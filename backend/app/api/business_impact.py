"""REST API Endpoints for MITRA ROI and Business Impact Analysis Engine (Phase 10)."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.database.repository import BusinessImpactRepository
from app.engines.business_impact.engine import BusinessImpactEngine
from app.engines.business_impact.rules import (
    BusinessImpactError,
    InsufficientImpactDataError,
    OutcomeNotFoundError,
    OutcomeNotMeasuredError,
)
from app.models.contracts import BusinessImpact

router = APIRouter(tags=["ROI & Business Impact Analysis"])


class AnalyzeImpactRequest(BaseModel):
    merchant_id: Optional[str] = "MID-DEMO-98234"


@router.post(
    "/business-impact/analyze/{outcome_id}",
    response_model=BusinessImpact,
    summary="Deterministically analyze simulated business impact and ROI",
)
def analyze_business_impact(
    outcome_id: str,
    response: Response,
    body: Optional[AnalyzeImpactRequest] = None,
):
    """Calculates deterministic simulated business impact and ROI for a persisted outcome.
    
    PRECONDITIONS:
    1. Outcome must exist in SQLite (404 if not found).
    2. Outcome must be in MEASURED state (409 if not measured).
    
    GUARANTEES:
    - Zero live Paytm APIs, zero money movement, zero real customer data.
    - Zero client metric injection: metrics are calculated strictly from persisted server-side data.
    - Single authoritative row: returns 201 on creation, 200 on idempotent subsequent calls.
    - Non-causal, descriptive simulation framing.
    """
    engine = BusinessImpactEngine()

    # Check if existing impact already exists (for 200 vs 201 status code distinction)
    existing = BusinessImpactRepository.get_by_outcome(outcome_id)
    is_new = existing is None

    try:
        impact = engine.analyze_impact(outcome_id=outcome_id)
        response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
        return impact
    except OutcomeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OutcomeNotMeasuredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except BusinessImpactError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Business impact analysis failed: {exc}",
        )


@router.get(
    "/business-impact/{impact_id}",
    response_model=BusinessImpact,
    summary="Retrieve business impact analysis by ID",
)
def get_business_impact(impact_id: str):
    """Retrieves a business impact and ROI analysis record by ID."""
    row = BusinessImpactRepository.get_business_impact(impact_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business impact record {impact_id} not found.",
        )
    return BusinessImpact.model_validate(row)


@router.get(
    "/outcomes/{outcome_id}/business-impact",
    response_model=BusinessImpact,
    summary="Retrieve business impact analysis for an outcome",
)
def get_business_impact_for_outcome(outcome_id: str):
    """Retrieves the business impact analysis associated with a specific outcome ID."""
    row = BusinessImpactRepository.get_by_outcome(outcome_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No business impact analysis found for outcome {outcome_id}.",
        )
    return BusinessImpact.model_validate(row)


@router.get(
    "/business-impact",
    response_model=List[BusinessImpact],
    summary="List business impact records for a merchant",
)
def list_merchant_business_impacts(
    merchant_id: str = Query("MID-DEMO-98234", description="Merchant Identifier"),
    limit: int = Query(20, ge=1, le=100),
):
    """Retrieves chronological list of simulated business impact records for a merchant."""
    rows = BusinessImpactRepository.get_by_merchant(merchant_id=merchant_id, limit=limit)
    return [BusinessImpact.model_validate(r) for r in rows]
