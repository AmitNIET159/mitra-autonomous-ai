"""API endpoints for MITRA Deterministic Guardrail Engine."""
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query

from app.database.repository import ActionRepository, GuardrailRepository
from app.engines.guardrail_engine.engine import GuardrailEngine
from app.models.contracts import GuardrailCheck, GuardrailEvaluation
from app.models.enums import DecisionState

router = APIRouter(tags=["Guardrail Engine"])


def _row_to_guardrail_evaluation(row: Dict[str, Any]) -> GuardrailEvaluation:
    """Helper to convert database row into a structured GuardrailEvaluation contract."""
    checks_raw = row.get("checks", "[]")
    if isinstance(checks_raw, str):
        try:
            checks_list = json.loads(checks_raw)
        except Exception:
            checks_list = []
    elif isinstance(checks_raw, list):
        checks_list = checks_raw
    else:
        checks_list = []

    parsed_checks = []
    for c in checks_list:
        if isinstance(c, dict):
            parsed_checks.append(GuardrailCheck(**c))
        elif isinstance(c, GuardrailCheck):
            parsed_checks.append(c)

    def _parse_list(val: Any) -> list:
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return []
        elif isinstance(val, list):
            return val
        return []

    def _parse_dict(val: Any) -> dict:
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        elif isinstance(val, dict):
            return val
        return {}

    overall_status_str = row.get("overall_status", "PASS")
    try:
        overall_status = DecisionState(overall_status_str)
    except Exception:
        overall_status = DecisionState.PASS

    return GuardrailEvaluation(
        evaluation_id=row["id"],
        action_id=row["action_id"],
        merchant_id=row.get("merchant_id", "MID-DEMO-98234"),
        overall_status=overall_status,
        passed=bool(row.get("passed", 1)),
        checks=parsed_checks,
        passed_checks=_parse_list(row.get("passed_checks")),
        failed_checks=_parse_list(row.get("failed_checks")),
        warnings=_parse_list(row.get("warnings")),
        modifications=_parse_dict(row.get("modifications")),
        original_values=_parse_dict(row.get("original_values")),
        modified_values=_parse_dict(row.get("modified_values")),
        notes=row.get("notes", ""),
        evaluated_at=row.get("evaluated_at"),
        is_deterministic=bool(row.get("is_deterministic", 1)),
    )


@router.post("/guardrails/evaluate/{action_id}", response_model=GuardrailEvaluation)
async def evaluate_action_proposal(
    action_id: str,
    merchant_id: Optional[str] = Query(None, description="Optional merchant ID override"),
) -> GuardrailEvaluation:
    """Deterministically evaluates a stored action proposal against hard merchant guardrails.
    
    100% Deterministic — Zero LLM authority over safety.
    Guarantees that no unsafe, unbudgeted, or unverified action can proceed.
    """
    # Verify action proposal exists
    raw_action = ActionRepository.get_action(action_id)
    if not raw_action:
        raise HTTPException(
            status_code=404,
            detail=f"Action proposal with ID '{action_id}' not found.",
        )

    engine = GuardrailEngine()
    try:
        evaluation = engine.evaluate(action_id, merchant_id=merchant_id)
        return evaluation
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate guardrails for action '{action_id}': {str(exc)}",
        )


@router.get("/guardrails/{evaluation_id}", response_model=GuardrailEvaluation)
async def get_guardrail_evaluation(evaluation_id: str) -> GuardrailEvaluation:
    """Retrieves a previously computed guardrail evaluation by its evaluation ID."""
    row = GuardrailRepository.get_evaluation(evaluation_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Guardrail evaluation with ID '{evaluation_id}' not found.",
        )
    return _row_to_guardrail_evaluation(row)


@router.get("/actions/{action_id}/guardrails", response_model=GuardrailEvaluation)
async def get_guardrail_by_action(action_id: str) -> GuardrailEvaluation:
    """Retrieves the latest guardrail evaluation for a given action proposal ID."""
    row = GuardrailRepository.get_evaluation_by_action(action_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No guardrail evaluation found for action ID '{action_id}'.",
        )
    return _row_to_guardrail_evaluation(row)
