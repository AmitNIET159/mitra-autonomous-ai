"""API endpoints for MITRA Human-in-the-Loop & Controlled Autonomy Engine (Phase 12)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database.repository import (
    ActionRepository,
    AutonomyRepository,
    DecisionRepository,
    MerchantRepository,
)
from app.engines.autonomy_engine.engine import AutonomyPolicyEngine
from app.engines.autonomy_engine.rules import (
    BlockedAutonomyOverrideError,
    EscalatedAutonomyOverrideError,
    StaleAutonomyEvaluationError,
)
from app.engines.decision_engine.engine import DecisionEngine
from app.engines.decision_engine.rules import (
    BlockedDecisionApprovalError,
    EscalatedDecisionApprovalError,
    MerchantAuthorizationError,
    StaleDecisionError,
)
from app.models.contracts import AutonomyEvaluation, MerchantAutonomyPolicy
from app.models.enums import ActorType, ApprovalSource, AutonomyMode, AutonomyStatus

router = APIRouter(prefix="/autonomy", tags=["Controlled Autonomy & HITL"])


class MerchantAutonomyUpdateRequest(BaseModel):
    """Payload for updating merchant autonomy mode and policy thresholds."""
    autonomy_mode: AutonomyMode
    auto_approval_risk_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    full_autonomy_risk_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    auto_approval_max_budget: Optional[float] = Field(default=None, ge=0.0)
    auto_approval_max_discount: Optional[float] = Field(default=None, ge=0.0)
    require_human_for_modify: Optional[bool] = None
    require_human_for_escalation: Optional[bool] = None


class AutonomySignOffRequest(BaseModel):
    merchant_id: str = "MID-DEMO-98234"
    approver: str = "Merchant Admin"
    reason: str = "Approved by merchant"


class AutonomyRejectionRequest(BaseModel):
    merchant_id: str = "MID-DEMO-98234"
    reason: str = "Rejected by merchant"
    approver: str = "Merchant Admin"


@router.post(
    "/evaluate/{action_id}",
    response_model=AutonomyEvaluation,
    status_code=status.HTTP_200_OK,
    summary="Evaluate deterministic autonomy policy for an action",
)
def evaluate_autonomy(
    action_id: str,
    merchant_id: str = Query("MID-DEMO-98234", description="Merchant Identifier"),
    override_mode: Optional[AutonomyMode] = Query(None, description="Temporary override mode for simulation"),
):
    """Evaluates the deterministic autonomy policy for an action proposal.
    
    CRITICAL INVARIANTS:
    - Hard guardrail BLOCK can NEVER be bypassed by any autonomy mode.
    - Clamped parameters (e.g. ₹100 instead of ₹150) are strictly evaluated and approved.
    - Zero LLM authority over approvals.
    """
    engine = AutonomyPolicyEngine()
    try:
        evaluation = engine.evaluate(
            action_id=action_id,
            merchant_id=merchant_id,
            override_mode=override_mode,
        )
        return evaluation
    except StaleAutonomyEvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{action_id}",
    response_model=AutonomyEvaluation,
    summary="Get autonomy evaluation by action ID",
)
def get_autonomy_by_action(action_id: str):
    """Fetches the latest autonomy evaluation for an action proposal."""
    row = AutonomyRepository.get_by_action(action_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No autonomy evaluation found for action {action_id}.",
        )
    return AutonomyEvaluation.model_validate(row)


@router.get(
    "/workflow/{correlation_id}",
    response_model=AutonomyEvaluation,
    summary="Get autonomy evaluation by workflow correlation ID",
)
def get_autonomy_by_workflow(correlation_id: str):
    """Fetches the autonomy evaluation associated with a workflow correlation ID."""
    row = AutonomyRepository.get_by_correlation_id(correlation_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No autonomy evaluation found for correlation_id {correlation_id}.",
        )
    return AutonomyEvaluation.model_validate(row)


@router.post(
    "/{action_id}/approve",
    response_model=AutonomyEvaluation,
    summary="Merchant signs off (APPROVE) on action under APPROVAL_REQUIRED mode",
)
def approve_action_autonomy(
    action_id: str,
    body: Optional[AutonomySignOffRequest] = None,
):
    """Processes human merchant sign-off for an action pending approval."""
    req = body or AutonomySignOffRequest()
    dec_row = DecisionRepository.get_decision_by_action(action_id)
    if not dec_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No decision found for action {action_id}.",
        )

    dec_engine = DecisionEngine()
    try:
        dec_engine.approve_decision(
            decision_id=dec_row["id"],
            approver_merchant_id=req.merchant_id,
            approver_name=req.approver,
        )
    except BlockedDecisionApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Blocked actions cannot be approved.",
        ) from exc
    except EscalatedDecisionApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Escalated actions require manual human review.",
        ) from exc
    except StaleDecisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except MerchantAuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    # Refresh or create autonomy evaluation record
    eval_row = AutonomyRepository.get_by_action(action_id)
    if not eval_row:
        engine = AutonomyPolicyEngine()
        engine.evaluate(action_id=action_id, merchant_id=req.merchant_id)
        eval_row = AutonomyRepository.get_by_action(action_id)

    updated = AutonomyRepository.record_evaluation(
        evaluation_id=eval_row["id"],
        correlation_id=eval_row.get("correlation_id", ""),
        merchant_id=req.merchant_id,
        action_id=action_id,
        guardrail_evaluation_id=eval_row.get("guardrail_evaluation_id", ""),
        decision_id=dec_row["id"],
        autonomy_mode=eval_row.get("autonomy_mode", "APPROVAL_REQUIRED"),
        guardrail_status=eval_row.get("guardrail_status", "PASS"),
        approval_required=False,
        auto_approval_allowed=False,
        auto_approval_reason=f"Signed off by merchant ({req.approver}).",
        approval_source=ApprovalSource.HUMAN_APPROVED.value,
        actor_type=ActorType.MERCHANT.value,
        blocked=False,
        escalated=False,
        approved_action=eval_row.get("approved_action", {}),
        evaluated_risk=eval_row.get("evaluated_risk", 0.0),
        policy_threshold=eval_row.get("policy_threshold", 0.30),
        policy_version="1.0.0",
        passed_checks=eval_row.get("passed_checks", []),
        failed_checks=[],
        simulation_mode=True,
    )
    return AutonomyEvaluation.model_validate(updated)


@router.post(
    "/{action_id}/reject",
    response_model=AutonomyEvaluation,
    summary="Merchant signs off (REJECT) on action",
)
def reject_action_autonomy(
    action_id: str,
    body: Optional[AutonomyRejectionRequest] = None,
):
    """Processes human merchant rejection of an action."""
    req = body or AutonomyRejectionRequest()
    dec_row = DecisionRepository.get_decision_by_action(action_id)
    if not dec_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No decision found for action {action_id}.",
        )

    dec_engine = DecisionEngine()
    try:
        dec_engine.reject_decision(
            decision_id=dec_row["id"],
            reason=req.reason,
            approver_merchant_id=req.merchant_id,
            approver_name=req.approver,
        )
    except MerchantAuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    eval_row = AutonomyRepository.get_by_action(action_id)
    if not eval_row:
        engine = AutonomyPolicyEngine()
        engine.evaluate(action_id=action_id, merchant_id=req.merchant_id)
        eval_row = AutonomyRepository.get_by_action(action_id)

    updated = AutonomyRepository.record_evaluation(
        evaluation_id=eval_row["id"],
        correlation_id=eval_row.get("correlation_id", ""),
        merchant_id=req.merchant_id,
        action_id=action_id,
        guardrail_evaluation_id=eval_row.get("guardrail_evaluation_id", ""),
        decision_id=dec_row["id"],
        autonomy_mode=eval_row.get("autonomy_mode", "APPROVAL_REQUIRED"),
        guardrail_status=eval_row.get("guardrail_status", "PASS"),
        approval_required=True,
        auto_approval_allowed=False,
        auto_approval_reason=f"Rejected by merchant: {req.reason}",
        approval_source=ApprovalSource.REJECTED.value,
        actor_type=ActorType.MERCHANT.value,
        blocked=False,
        escalated=False,
        approved_action=eval_row.get("approved_action", {}),
        evaluated_risk=eval_row.get("evaluated_risk", 0.0),
        policy_threshold=eval_row.get("policy_threshold", 0.30),
        policy_version="1.0.0",
        passed_checks=eval_row.get("passed_checks", []),
        failed_checks=["Action explicitly rejected by merchant admin."],
        simulation_mode=True,
    )
    return AutonomyEvaluation.model_validate(updated)


# Merchant Autonomy Policy Routes
merchants_autonomy_router = APIRouter(prefix="/merchants", tags=["Merchant Autonomy Policy"])


@merchants_autonomy_router.get(
    "/{merchant_id}/autonomy",
    response_model=MerchantAutonomyPolicy,
    summary="Get merchant autonomy configuration",
)
def get_merchant_autonomy(merchant_id: str = "MID-DEMO-98234"):
    """Fetches the current autonomy policy configuration for a merchant."""
    policy = MerchantRepository.get_autonomy_policy(merchant_id)
    return MerchantAutonomyPolicy.model_validate(policy)


@merchants_autonomy_router.put(
    "/{merchant_id}/autonomy",
    response_model=MerchantAutonomyPolicy,
    summary="Update merchant autonomy mode and policy thresholds",
)
def update_merchant_autonomy(
    merchant_id: str,
    payload: MerchantAutonomyUpdateRequest,
):
    """Updates the merchant autonomy mode and policy thresholds."""
    try:
        updated = MerchantRepository.update_autonomy_policy(
            merchant_id=merchant_id,
            autonomy_mode=payload.autonomy_mode.value,
            auto_approval_risk_threshold=payload.auto_approval_risk_threshold,
            full_autonomy_risk_threshold=payload.full_autonomy_risk_threshold,
            auto_approval_max_budget=payload.auto_approval_max_budget,
            auto_approval_max_discount=payload.auto_approval_max_discount,
            require_human_for_modify=payload.require_human_for_modify,
            require_human_for_escalation=payload.require_human_for_escalation,
        )
        return MerchantAutonomyPolicy.model_validate(updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
