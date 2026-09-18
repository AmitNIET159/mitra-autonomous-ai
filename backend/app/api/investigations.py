import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.database.repository import InvestigationRepository, SignalRepository
from app.engines.investigation_engine.investigation_engine import InvestigationEngine
from app.engines.investigation_engine.schemas import (
    ConfidenceLevel,
    EvidenceBundle,
    Hypothesis,
    InvestigationResult,
)

router = APIRouter(tags=["Investigation Engine"])


def _row_to_investigation_result(row: Dict[str, Any]) -> InvestigationResult:
    """Helper to convert a database row into an InvestigationResult model."""
    hypotheses_raw = []
    if row.get("hypotheses"):
        try:
            hypotheses_raw = json.loads(row["hypotheses"])
        except Exception:
            hypotheses_raw = []

    hypotheses = [
        Hypothesis(
            hypothesis=h.get("hypothesis", ""),
            rationale=h.get("rationale", ""),
            supporting_evidence_ids=h.get("supporting_evidence_ids", []),
            confidence=ConfidenceLevel(h.get("confidence", "MEDIUM")),
        )
        for h in hypotheses_raw
        if isinstance(h, dict)
    ]

    bundle = None
    if row.get("evidence_bundle"):
        try:
            bundle_dict = json.loads(row["evidence_bundle"])
            if bundle_dict:
                bundle = EvidenceBundle(**bundle_dict)
        except Exception:
            bundle = None

    evidence_ids = []
    if row.get("evidence_ids"):
        try:
            evidence_ids = json.loads(row["evidence_ids"])
        except Exception:
            evidence_ids = []

    limitations = []
    if row.get("limitations"):
        try:
            limitations = json.loads(row["limitations"])
        except Exception:
            limitations = []

    # Get merchant_id from signal if possible
    mid = "MID-DEMO-98234"
    if bundle and bundle.merchant_id:
        mid = bundle.merchant_id

    conf_level = str(row.get("confidence_level") or "MEDIUM").upper()
    if conf_level not in ("LOW", "MEDIUM", "HIGH"):
        conf_level = "MEDIUM"

    findings = []
    if row.get("finding"):
        findings.append(row["finding"])

    return InvestigationResult(
        investigation_id=row["id"],
        signal_id=row["signal_id"],
        merchant_id=mid,
        status=row.get("status", "COMPLETED"),
        summary=row.get("summary") or row.get("finding") or "",
        findings=findings,
        hypotheses=hypotheses,
        confidence=ConfidenceLevel(conf_level),
        evidence_ids=evidence_ids,
        limitations=limitations,
        created_at=row.get("created_at", ""),
        is_fallback=bool(row.get("is_fallback", 0)),
        evidence_bundle=bundle,
    )


@router.post("/investigations/{signal_id}", response_model=InvestigationResult)
async def create_investigation(
    signal_id: str,
    force_fallback: bool = Query(default=False),
) -> InvestigationResult:
    """Triggers an evidence-backed investigation for a detected business signal."""
    # Verify signal exists
    raw_signal = SignalRepository.get_signal_by_id(signal_id)
    if not raw_signal:
        raise HTTPException(
            status_code=404,
            detail=f"Business signal with ID '{signal_id}' was not found in digital twin database.",
        )

    engine = InvestigationEngine()
    try:
        result = await engine.investigate(
            signal=signal_id,
            merchant_id=raw_signal.get("merchant_id"),
            force_fallback=force_fallback,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {exc}") from exc


@router.get("/investigations/{investigation_id}", response_model=InvestigationResult)
async def get_investigation(investigation_id: str) -> InvestigationResult:
    """Retrieves an investigation by unique investigation ID."""
    row = InvestigationRepository.get_investigation(investigation_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation with ID '{investigation_id}' was not found.",
        )
    return _row_to_investigation_result(row)


@router.get("/signals/{signal_id}/investigation", response_model=InvestigationResult)
async def get_investigation_by_signal(signal_id: str) -> InvestigationResult:
    """Retrieves the active/latest investigation linked to a signal."""
    row = InvestigationRepository.get_investigation_by_signal(signal_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No investigation has been conducted for signal '{signal_id}' yet.",
        )
    return _row_to_investigation_result(row)
