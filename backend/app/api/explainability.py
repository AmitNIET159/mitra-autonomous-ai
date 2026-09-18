"""REST API Endpoints for MITRA Explainability Engine (Phase 11).

SAFETY & EXPLAINABILITY PRINCIPLES:
- Strictly read-only: Generates structured, verifiable explanations from authoritative digital twin data.
- Facts vs Hypotheses: Factual database evidence explicitly decoupled from AI hypotheses.
- Non-Causality: Descriptive language only; zero causal assertions.
- Zero Secret Leakage: Tokens, passwords, and sensitive keys stripped.
- Prototype Disclaimer: Explicitly labeled SIMULATED / PROTOTYPE / DIGITAL TWIN.
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.engines.explainability_engine.engine import ExplainabilityEngine
from app.models.contracts import ExplainabilitySummary

router = APIRouter(tags=["Audit & Explainability"])
engine = ExplainabilityEngine()


@router.get(
    "/explainability/workflow/{correlation_id}",
    response_model=ExplainabilitySummary,
    summary="Generate structured explainability summary for a workflow",
)
def get_workflow_explanation(correlation_id: str) -> ExplainabilitySummary:
    """Generates a comprehensive, human-readable, non-causal explanation of why MITRA acted.
    
    Covers:
    - WHY this signal was detected
    - WHAT evidence supported it (FACT vs AI HYPOTHESIS)
    - WHY this candidate action was proposed
    - HOW 10 guardrails evaluated the proposal (including clamped parameter modifications)
    - WHAT decision and sign-off occurred
    - WHAT was simulated in execution (proving unsafe values were excluded)
    - WHAT outcome was observed
    - WHAT simulated ROI and business impact was calculated
    - Cryptographic SHA-256 audit chain validation status
    """
    try:
        explanation = engine.generate_explanation(correlation_id)
        return explanation
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explainability summary for '{correlation_id}': {exc}",
        )


@router.get(
    "/explainability/entity/{entity_type}/{entity_id}",
    response_model=ExplainabilitySummary,
    summary="Generate explainability summary resolved from an entity ID",
)
def get_entity_explanation(entity_type: str, entity_id: str) -> ExplainabilitySummary:
    """Resolves the complete workflow graph starting from any entity (signal, action, decision, etc.)."""
    allowed_types = {"signal", "investigation", "action", "guardrail", "decision", "execution", "outcome", "impact"}
    if entity_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(sorted(allowed_types))}.",
        )

    try:
        explanation = engine.generate_explanation(entity_id)
        return explanation
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve explainability for entity '{entity_id}': {exc}",
        )
