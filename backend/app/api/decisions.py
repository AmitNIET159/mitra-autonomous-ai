"""API endpoints for MITRA Deterministic Decision Engine & Merchant Sign-off."""
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.database.repository import ActionRepository, DecisionRepository
from app.engines.decision_engine.engine import DecisionEngine
from app.engines.decision_engine.rules import (
    BlockedDecisionApprovalError,
    EscalatedDecisionApprovalError,
    GuardrailActionMismatchError,
    GuardrailMerchantMismatchError,
    MerchantAuthorizationError,
    MissingGuardrailEvaluationError,
    StaleDecisionError,
)
from app.models.contracts import Decision

router = APIRouter(tags=["Decision Engine & Sign-off"])


class ApprovalRequest(BaseModel):
    merchant_id: str = "MID-DEMO-98234"
    approver: str = "Merchant Admin"


class RejectionRequest(BaseModel):
    merchant_id: str = "MID-DEMO-98234"
    reason: str = "Rejected by merchant"
    approver: str = "Merchant Admin"


@router.post(
    "/decisions/create/{action_id}",
    response_model=Decision,
    status_code=status.HTTP_201_CREATED,
    summary="Create authoritative decision from existing GuardrailEvaluation",
)
def create_decision(
    action_id: str,
    merchant_id: str = Query("MID-DEMO-98234", description="Merchant Identifier"),
):
    """Creates authoritative decision strictly from existing persisted GuardrailEvaluation.
    
    MANDATORY PRECONDITION:
    A valid GuardrailEvaluation must already exist for this action.
    This endpoint does NOT invoke Phase 6 guardrails. If missing, returns 409 Conflict.
    """
    engine = DecisionEngine()
    try:
        decision = engine.create_decision_from_persisted_evaluation(
            action_id=action_id,
            merchant_id=merchant_id,
        )
        return decision
    except MissingGuardrailEvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Guardrail evaluation required before decision creation.",
        ) from exc
    except (GuardrailActionMismatchError, GuardrailMerchantMismatchError) as exc:
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
    "/decisions/{decision_id}",
    response_model=Decision,
    summary="Get authoritative decision by ID",
)
def get_decision(decision_id: str):
    """Retrieves authoritative decision by ID."""
    row = DecisionRepository.get_decision(decision_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found.",
        )
    return DecisionEngine._row_to_decision(row)


@router.get(
    "/actions/{action_id}/decision",
    response_model=Decision,
    summary="Get latest authoritative decision for an action",
)
def get_decision_by_action(action_id: str):
    """Retrieves latest decision associated with a specific action."""
    row = DecisionRepository.get_decision_by_action(action_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No decision found for action {action_id}.",
        )
    return DecisionEngine._row_to_decision(row)


@router.post(
    "/decisions/{decision_id}/approve",
    response_model=Decision,
    summary="Merchant signs off (APPROVE) on authoritative decision",
)
def approve_decision(
    decision_id: str,
    body: Optional[ApprovalRequest] = None,
):
    """Records merchant sign-off (APPROVE) on an authoritative Decision.
    
    SAFETY CONSTRAINTS:
    - BLOCK decisions cannot be approved (400 Bad Request).
    - ESCALATE decisions require human review resolution (400 Bad Request).
    - Stale decisions with changed hashes are rejected (409 Conflict).
    - Approver merchant ID must match decision merchant ID (403 Forbidden).
    """
    req = body or ApprovalRequest()
    engine = DecisionEngine()
    try:
        approved = engine.approve_decision(
            decision_id=decision_id,
            approver_merchant_id=req.merchant_id,
            approver_name=req.approver,
        )
        return approved
    except BlockedDecisionApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Blocked decisions cannot be approved.",
        ) from exc
    except EscalatedDecisionApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Escalated decisions require human review and cannot bypass the review barrier.",
        ) from exc
    except StaleDecisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Decision is stale. Fresh guardrail evaluation required.",
        ) from exc
    except MerchantAuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant not authorized to approve this decision.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/decisions/{decision_id}/reject",
    response_model=Decision,
    summary="Merchant signs off (REJECT) on authoritative decision",
)
def reject_decision(
    decision_id: str,
    body: Optional[RejectionRequest] = None,
):
    """Records merchant rejection on an authoritative Decision."""
    req = body or RejectionRequest()
    engine = DecisionEngine()
    try:
        rejected = engine.reject_decision(
            decision_id=decision_id,
            reason=req.reason,
            approver_merchant_id=req.merchant_id,
            approver_name=req.approver,
        )
        return rejected
    except MerchantAuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant not authorized to reject this decision.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
