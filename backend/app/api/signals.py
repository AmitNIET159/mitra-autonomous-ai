from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.database.repository import SignalRepository
from app.engines.signal_engine.engine import SignalDetectionEngine
from app.models.contracts import Signal
from app.models.enums import SignalSeverity, SignalStatus

router = APIRouter(prefix="/signals", tags=["Signal Detection"])


class DetectSignalsRequest(BaseModel):
    merchant_id: str = Field(default="MID-DEMO-98234")


class DetectSignalsResponse(BaseModel):
    merchant_id: str
    signals_detected: List[Signal]
    count: int
    simulated: bool = True


@router.post("/detect", response_model=DetectSignalsResponse)
async def detect_signals(
    req: Optional[DetectSignalsRequest] = None,
    merchant_id: Optional[str] = Query(default=None),
) -> DetectSignalsResponse:
    """Triggers deterministic detection over the merchant digital-twin telemetry."""
    mid = (req.merchant_id if req else None) or merchant_id or "MID-DEMO-98234"
    engine = SignalDetectionEngine()
    signals = engine.detect_signals(mid)
    return DetectSignalsResponse(
        merchant_id=mid,
        signals_detected=signals,
        count=len(signals),
        simulated=True,
    )


@router.get("", response_model=List[Signal])
async def get_signals(
    merchant_id: str = Query(default="MID-DEMO-98234"),
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    signal_type: Optional[str] = Query(default=None),
) -> List[Signal]:
    """Retrieves business signals from the digital-twin database with optional filtering."""
    raw_signals = SignalRepository.get_signals(
        merchant_id=merchant_id,
        status=status,
        severity=severity,
        signal_type=signal_type,
    )
    import json
    result: List[Signal] = []
    for r in raw_signals:
        context_data = {}
        if r.get("context_data"):
            try:
                context_data = json.loads(r["context_data"])
            except Exception:
                context_data = {}

        raw_status = (r.get("status") or "ACTIVE").upper()
        if raw_status == "NEW":
            status_val = SignalStatus.ACTIVE
        else:
            try:
                status_val = SignalStatus(raw_status)
            except Exception:
                status_val = SignalStatus.ACTIVE

        raw_severity = (r.get("severity") or "MEDIUM").upper()
        try:
            severity_val = SignalSeverity(raw_severity)
        except Exception:
            severity_val = SignalSeverity.MEDIUM

        change_val = float(r.get("change_percentage") or 0.0)
        decline_val = float(r.get("decline_percentage") or abs(change_val))

        result.append(
            Signal(
                signal_id=r["id"],
                merchant_id=r["merchant_id"],
                signal_type=r["signal_type"],
                severity=severity_val,
                metric_name=r["metric_name"],
                baseline_value=float(r["baseline_value"]),
                observed_value=float(r["observed_value"]),
                change_percentage=change_val,
                decline_percentage=decline_val,
                variance_percentage=change_val,
                description=r["description"],
                status=status_val,
                context_data=context_data,
            )
        )
    return result


@router.get("/{signal_id}", response_model=Signal)
async def get_signal_by_id(signal_id: str) -> Signal:
    """Fetches a specific signal by ID."""
    r = SignalRepository.get_signal_by_id(signal_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found.")

    import json
    context_data = {}
    if r.get("context_data"):
        try:
            context_data = json.loads(r["context_data"])
        except Exception:
            context_data = {}

    raw_status = (r.get("status") or "ACTIVE").upper()
    if raw_status == "NEW":
        status_val = SignalStatus.ACTIVE
    else:
        try:
            status_val = SignalStatus(raw_status)
        except Exception:
            status_val = SignalStatus.ACTIVE

    raw_severity = (r.get("severity") or "MEDIUM").upper()
    try:
        severity_val = SignalSeverity(raw_severity)
    except Exception:
        severity_val = SignalSeverity.MEDIUM

    change_val = float(r.get("change_percentage") or 0.0)
    decline_val = float(r.get("decline_percentage") or abs(change_val))

    return Signal(
        signal_id=r["id"],
        merchant_id=r["merchant_id"],
        signal_type=r["signal_type"],
        severity=severity_val,
        metric_name=r["metric_name"],
        baseline_value=float(r["baseline_value"]),
        observed_value=float(r["observed_value"]),
        change_percentage=change_val,
        decline_percentage=decline_val,
        variance_percentage=change_val,
        description=r["description"],
        status=status_val,
        context_data=context_data,
    )

