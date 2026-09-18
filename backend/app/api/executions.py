"""API endpoints for MITRA Safe Execution Simulator."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.database.repository import ExecutionRepository
from app.engines.execution_engine.engine import (
    BlockedActionExecutionError,
    DecisionNotFoundError,
    EscalatedActionExecutionError,
    ExecutionEngine,
    ExecutionNotEligibleError,
    ExecutionSafetyError,
    MerchantMismatchError,
    RealExecutionNotAllowedError,
    StaleDecisionExecutionError,
    UnapprovedActionExecutionError,
    UncheckedExecutionAttemptError,
)
from app.models.contracts import ExecutionResult
from app.models.enums import ActionType, ExecutionMode, ExecutionState

router = APIRouter(tags=["Safe Execution Simulator"])


class ExecuteRequest(BaseModel):
    merchant_id: Optional[str] = "MID-DEMO-98234"


def _row_to_execution_result(row: Dict[str, Any]) -> ExecutionResult:
    """Helper to convert an execution database row into an ExecutionResult contract."""
    action_type_str = row.get("action_type", "OFFER_CAMPAIGN")
    try:
        action_type = ActionType(action_type_str)
    except ValueError:
        action_type = ActionType.OFFER_CAMPAIGN

    exec_state_str = row.get("execution_state", "COMPLETED")
    try:
        exec_state = ExecutionState(exec_state_str)
    except ValueError:
        exec_state = ExecutionState.COMPLETED

    exec_mode_str = row.get("execution_mode", "SIMULATION")
    try:
        exec_mode = ExecutionMode(exec_mode_str)
    except ValueError:
        exec_mode = ExecutionMode.SIMULATION

    return ExecutionResult(
        execution_id=row["id"],
        decision_id=row["decision_id"],
        action_id=row.get("action_id", ""),
        merchant_id=row.get("merchant_id", "MID-DEMO-98234"),
        action_type=action_type,
        execution_state=exec_state,
        status=exec_state.value,
        success=(exec_state == ExecutionState.COMPLETED),
        execution_mode=exec_mode,
        simulated=bool(row.get("simulated", 1)),
        approved_action=row.get("approved_action", {}),
        result=row.get("result", {}),
        output_details=row.get("result", {}),
        error=row.get("error"),
        executed_at=row.get("executed_at"),
    )


@router.post(
    "/executions/execute/{decision_id}",
    response_model=ExecutionResult,
    status_code=status.HTTP_201_CREATED,
)
def execute_decision(
    decision_id: str,
    payload: Optional[ExecuteRequest] = None,
) -> ExecutionResult:
    """Simulates the execution of a merchant-approved decision.
    
    SAFETY PRINCIPLES:
    - Strictly runs in SIMULATION mode.
    - Zero real Paytm API calls, zero financial side effects.
    - Strictly gated by 10 deterministic preconditions.
    - Automatically handles idempotency: duplicate executions safely return the existing record.
    """
    merchant_id = payload.merchant_id if payload else "MID-DEMO-98234"
    engine = ExecutionEngine(simulation_mode=True)

    try:
        result = engine.execute(decision_or_id=decision_id, merchant_id=merchant_id)
        return result
    except DecisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MerchantMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (
        BlockedActionExecutionError,
        EscalatedActionExecutionError,
        UnapprovedActionExecutionError,
        ExecutionNotEligibleError,
        UncheckedExecutionAttemptError,
        RealExecutionNotAllowedError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except StaleDecisionExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ExecutionSafetyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed unexpectedly: {exc}",
        ) from exc


@router.get("/executions/{execution_id}", response_model=ExecutionResult)
def get_execution(execution_id: str) -> ExecutionResult:
    """Retrieves an execution record by unique execution ID."""
    row = ExecutionRepository.get_execution(execution_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID '{execution_id}' was not found.",
        )
    return _row_to_execution_result(row)


@router.get("/decisions/{decision_id}/execution", response_model=ExecutionResult)
def get_execution_by_decision(decision_id: str) -> ExecutionResult:
    """Retrieves the latest execution record for a specific decision."""
    row = ExecutionRepository.get_execution_by_decision(decision_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No execution has been performed for decision '{decision_id}' yet.",
        )
    return _row_to_execution_result(row)


@router.get("/executions", response_model=List[ExecutionResult])
def list_executions(
    merchant_id: str = Query(default="MID-DEMO-98234"),
    limit: int = Query(default=20, le=100),
) -> List[ExecutionResult]:
    """Retrieves the history of simulated executions for a merchant."""
    rows = ExecutionRepository.get_executions_by_merchant(merchant_id=merchant_id, limit=limit)
    return [_row_to_execution_result(r) for r in rows]
