"""REST API Endpoints for MITRA Outcome Monitoring and Measurement Engine (Phase 9)."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.database.repository import OutcomeRepository
from app.engines.outcome_engine.engine import OutcomeEngine
from app.engines.outcome_engine.rules import (
    ExecutionNotCompletedError,
    ExecutionNotFoundError,
    InsufficientMeasurementDataError,
    NonSimulationExecutionError,
)
from app.models.contracts import Outcome

router = APIRouter(tags=["Outcome Monitoring & Measurement"])


class MeasureOutcomeRequest(BaseModel):
    merchant_id: Optional[str] = "MID-DEMO-98234"
    measurement_window: Optional[Dict[str, Any]] = None


@router.post(
    "/outcomes/measure/{execution_id}",
    response_model=Outcome,
    summary="Deterministically measure post-execution simulated outcome",
)
def measure_execution_outcome(
    execution_id: str,
    response: Response,
    body: Optional[MeasureOutcomeRequest] = None,
):
    """Measures post-execution simulated business impact.
    
    PRECONDITIONS:
    1. Execution must exist.
    2. Execution must have completed (execution_state == COMPLETED).
    3. Execution mode must be SIMULATION.
    
    GUARANTEES:
    - Zero live Paytm APIs, zero money movement.
    - Zero arbitrary client metric injection: derived strictly from SQLite digital twin.
    - Idempotency: Returns existing outcome if already measured.
    - Descriptive comparison: strictly avoids any causal claims.
    """
    engine = OutcomeEngine()
    
    # Check if existing outcome already exists (for 200 vs 201 status code distinction)
    existing = OutcomeRepository.get_outcome_by_execution(execution_id)
    is_new = existing is None

    req_window = body.measurement_window if body else None

    try:
        outcome = engine.measure_outcome(
            execution_id=execution_id,
            measurement_window=req_window,
        )
        response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
        return outcome
    except ExecutionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ExecutionNotCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except NonSimulationExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Outcome measurement failed: {exc}",
        )


@router.get(
    "/outcomes/{outcome_id}",
    response_model=Outcome,
    summary="Retrieve outcome measurement by ID",
)
def get_outcome(outcome_id: str):
    """Retrieves an outcome measurement record by ID."""
    row = OutcomeRepository.get_outcome(outcome_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outcome measurement {outcome_id} not found.",
        )
    return Outcome.model_validate(row)


@router.get(
    "/executions/{execution_id}/outcome",
    response_model=Outcome,
    summary="Retrieve outcome measurement for an execution",
)
def get_outcome_for_execution(execution_id: str):
    """Retrieves the latest outcome measurement for a given simulated execution."""
    row = OutcomeRepository.get_outcome_by_execution(execution_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No outcome measurement found for execution {execution_id}.",
        )
    return Outcome.model_validate(row)


@router.get(
    "/outcomes",
    response_model=List[Outcome],
    summary="List outcome measurements for a merchant",
)
def list_merchant_outcomes(
    merchant_id: str = Query("MID-DEMO-98234", description="Merchant Identifier"),
    limit: int = Query(20, ge=1, le=100),
):
    """Retrieves chronological list of simulated outcome measurements for a merchant."""
    rows = OutcomeRepository.get_outcomes_by_merchant(merchant_id=merchant_id, limit=limit)
    return [Outcome.model_validate(r) for r in rows]
