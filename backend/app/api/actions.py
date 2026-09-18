"""API endpoints for MITRA Action Planning & Structured Proposals."""
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query

from app.database.repository import ActionRepository, InvestigationRepository
from app.engines.planning_engine.planning_engine import PlanningEngine
from app.models.contracts import ActionProposal
from app.models.enums import ActionType

router = APIRouter(tags=["Action Planning Engine"])


def _row_to_action_proposal(row: Dict[str, Any]) -> ActionProposal:
    """Helper to convert database row into an ActionProposal contract."""
    supporting_evidence_ids = []
    if row.get("supporting_evidence_ids"):
        if isinstance(row["supporting_evidence_ids"], str):
            try:
                supporting_evidence_ids = json.loads(row["supporting_evidence_ids"])
            except Exception:
                supporting_evidence_ids = []
        elif isinstance(row["supporting_evidence_ids"], list):
            supporting_evidence_ids = row["supporting_evidence_ids"]

    constraints = {}
    if row.get("constraints"):
        if isinstance(row["constraints"], str):
            try:
                constraints = json.loads(row["constraints"])
            except Exception:
                constraints = {}
        elif isinstance(row["constraints"], dict):
            constraints = row["constraints"]

    parameters = {}
    if row.get("parameters"):
        if isinstance(row["parameters"], str):
            try:
                parameters = json.loads(row["parameters"])
            except Exception:
                parameters = {}
        elif isinstance(row["parameters"], dict):
            parameters = row["parameters"]

    raw_action_type = row.get("action_type", "EVENING_REENGAGEMENT_CAMPAIGN")
    try:
        act_type = ActionType(raw_action_type)
    except Exception:
        act_type = ActionType.EVENING_REENGAGEMENT_CAMPAIGN

    return ActionProposal(
        action_id=row["id"],
        proposal_id=row["id"],
        signal_id=row.get("signal_id", ""),
        investigation_id=row.get("investigation_id"),
        merchant_id=row.get("merchant_id", "MID-DEMO-98234"),
        action_type=act_type,
        objective=row.get("objective", ""),
        target_segment=row.get("target_segment", "repeat_customer, regular"),
        target_customer_count=int(row.get("target_customer_count", 0) or 0),
        incentive_type=row.get("incentive_type", "CASHBACK"),
        incentive_value=float(row.get("incentive_value", 0.0) or 0.0),
        duration=row.get("duration", "7 days"),
        parameters=parameters,
        reason=row.get("reason", ""),
        confidence=0.85,
        estimated_cost_inr=float(row.get("estimated_cost_inr", 0.0) or 0.0),
        supporting_evidence_ids=supporting_evidence_ids,
        constraints=constraints,
        status=row.get("status", "PROPOSED"),
        is_fallback=bool(row.get("is_fallback", 0)),
        created_at=row.get("created_at"),
    )


@router.post("/actions/plan/{investigation_id}", response_model=ActionProposal)
async def plan_action(
    investigation_id: str,
    force_fallback: bool = Query(default=False),
) -> ActionProposal:
    """Synthesizes a structured candidate ActionProposal from an investigated signal.
    
    SAFETY PRINCIPLES:
    - Strictly PROPOSAL ONLY.
    - Zero execution, zero guardrail evaluation, zero Paytm API calls.
    - Status is fixed at PROPOSED.
    """
    # Verify investigation exists
    raw_inv = InvestigationRepository.get_investigation(investigation_id)
    if not raw_inv:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation with ID '{investigation_id}' was not found in digital twin database.",
        )

    engine = PlanningEngine()
    try:
        proposal = await engine.plan_action(
            investigation=investigation_id,
            merchant_id=raw_inv.get("merchant_id", "MID-DEMO-98234"),
            force_fallback=force_fallback,
        )
        return proposal
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Action planning failed: {exc}") from exc


@router.get("/actions/{action_id}", response_model=ActionProposal)
async def get_action(action_id: str) -> ActionProposal:
    """Retrieves an action proposal by unique action ID."""
    row = ActionRepository.get_action_proposal(action_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Action proposal with ID '{action_id}' was not found.",
        )
    return _row_to_action_proposal(row)


@router.get("/investigations/{investigation_id}/action", response_model=ActionProposal)
@router.get("/actions/by-investigation/{investigation_id}", response_model=ActionProposal)
async def get_action_by_investigation(investigation_id: str) -> ActionProposal:
    """Retrieves the candidate action proposal associated with an investigation."""
    row = ActionRepository.get_action_by_investigation(investigation_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No action proposal has been generated for investigation '{investigation_id}' yet.",
        )
    return _row_to_action_proposal(row)
