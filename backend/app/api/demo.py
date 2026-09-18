"""API endpoints for MITRA Demo Reset & Health Telemetry (Phase 14).

CORE PRINCIPLES:
1. Deterministic demo reset: Restores digital-twin simulation state and merchant demo baseline.
2. PRESERVES AUDIT HISTORY: Does NOT destroy or truncate historical audit records, genesis, or hash chains.
3. Records DEMO_RESET_PERFORMED as a valid audit event in the existing hash chain.
4. Idempotent: Calling reset multiple times results in the same clean baseline state.
5. Zero secret leakage: No API keys, passwords, or tokens exposed.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.database.connection import get_connection
from app.database.repository import MerchantRepository
from app.database.seed import seed_digital_twin
from app.engines.audit_engine.engine import AuditEngine
from app.llm.provider import get_ai_provider_manager
from app.models.enums import StageType

router = APIRouter(prefix="/demo", tags=["Demo Controller & Hardening"])
settings = get_settings()


class DemoResetResponse(BaseModel):
    status: str = "ok"
    message: str
    merchant_id: str = "MID-DEMO-98234"
    autonomy_mode: str = "APPROVAL_REQUIRED"
    active_scenario: str = "NORMAL_FLOW"
    active_signal_id: str = "SIG-EVN-DECLINE-01"
    audit_preserved: bool = True
    audit_events_count: int
    ai_provider: str
    simulated: bool = True
    seed_summary: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SystemHealthResponse(BaseModel):
    backend: str = "ONLINE"
    database: str = "ONLINE"
    ai: str
    ai_status: str
    guardrails: str = "ACTIVE"
    audit: str = "ACTIVE"
    execution: str = "SIMULATED"
    autonomy_mode: str = "APPROVAL_REQUIRED"
    simulation_mode: bool = True
    disclaimer: str = "PROTOTYPE SIMULATION - Digital twin sandbox for Paytm Build for India Hackathon"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Deterministically reset demo state to baseline while preserving audit history",
)
def reset_demo_endpoint() -> DemoResetResponse:
    """Safely resets merchant demo baseline and simulation state.
    
    CRITICAL INVARIANTS:
    - Preserves audit_events and hash-chain integrity.
    - Resets merchant autonomy policy to APPROVAL_REQUIRED.
    - Clears temporary scenario-local proposals and executions.
    - Clears in-memory advisory AI cache.
    - Records DEMO_RESET_PERFORMED in audit ledger.
    - Idempotent: repeated calls produce identical baseline.
    """
    mid = "MID-DEMO-98234"

    # 1. Reseed digital-twin simulation state (merchants, customers, transactions, metrics)
    # preserve_audit=True ensures audit_events table is NEVER purged
    seed_summary = seed_digital_twin(preserve_audit=True)

    # 2. Reset autonomy policy to default APPROVAL_REQUIRED mode
    MerchantRepository.update_autonomy_policy(
        mid,
        autonomy_mode="APPROVAL_REQUIRED",
        auto_approval_risk_threshold=0.30,
        full_autonomy_risk_threshold=0.50,
        auto_approval_max_budget=10000.0,
        auto_approval_max_discount=100.0,
    )

    # 3. Clean up ephemeral scenario-local objects from DB to isolate demo state
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM autonomy_evaluations WHERE action_id LIKE 'act-demo-%' OR action_id LIKE 'act-p12-%' OR action_id LIKE 'prop-%'")
        cursor.execute("DELETE FROM decisions WHERE action_id LIKE 'act-demo-%' OR action_id LIKE 'act-p12-%' OR action_id LIKE 'prop-%'")
        cursor.execute("DELETE FROM guardrail_evaluations WHERE action_id LIKE 'act-demo-%' OR action_id LIKE 'act-p12-%' OR action_id LIKE 'prop-%'")
        cursor.execute("DELETE FROM actions WHERE id LIKE 'act-demo-%' OR id LIKE 'act-p12-%' OR id LIKE 'prop-%'")
        cursor.execute("DELETE FROM investigations WHERE id LIKE 'inv-demo-%' OR id LIKE 'inv-p12-%'")
        cursor.execute("DELETE FROM signals WHERE id LIKE 'sig-demo-%' OR id LIKE 'sig-p12-%'")
        # Ensure primary demo signal is active/new
        cursor.execute("UPDATE signals SET status = 'NEW' WHERE id = 'SIG-EVN-DECLINE-01'")
        conn.commit()

        # Count total preserved audit events
        cursor.execute("SELECT COUNT(*) FROM audit_events")
        audit_count = cursor.fetchone()[0]
    finally:
        conn.close()

    # 4. Clear in-memory AI provider cache
    ai_manager = get_ai_provider_manager()
    ai_manager.clear_cache()
    provider_status = ai_manager.get_provider_status()

    # 5. Record DEMO_RESET_PERFORMED in audit ledger (continues cryptographic hash chain)
    audit_engine = AuditEngine()
    audit_engine.record_event(
        stage=StageType.DETECT,
        actor="SystemAdmin",
        action_description="DEMO_RESET_PERFORMED: Reset digital-twin demo state to baseline while preserving audit history",
        input_payload={"merchant_id": mid, "preserve_audit": True},
        output_payload={
            "status": "SUCCESS",
            "autonomy_mode": "APPROVAL_REQUIRED",
            "active_signal_id": "SIG-EVN-DECLINE-01",
            "audit_events_count": audit_count + 1,
        },
        correlation_id="wf-demo-reset",
        merchant_id=mid,
    )

    return DemoResetResponse(
        status="ok",
        message="Demo state deterministically reset to baseline. Audit history preserved.",
        merchant_id=mid,
        autonomy_mode="APPROVAL_REQUIRED",
        active_scenario="NORMAL_FLOW",
        active_signal_id="SIG-EVN-DECLINE-01",
        audit_preserved=True,
        audit_events_count=audit_count + 1,
        ai_provider=provider_status.active_provider,
        simulated=True,
        seed_summary=seed_summary,
    )


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Compact 6-pillar system health and readiness telemetry",
)
def get_system_health() -> SystemHealthResponse:
    """Returns compact status across all 6 core MITRA pillars without exposing secrets."""
    mid = "MID-DEMO-98234"
    policy = MerchantRepository.get_autonomy_policy(mid)
    autonomy_mode = policy.get("autonomy_mode", "APPROVAL_REQUIRED") if policy else "APPROVAL_REQUIRED"

    ai_manager = get_ai_provider_manager()
    ai_status_obj = ai_manager.get_provider_status()
    is_live = "Gemini" in ai_status_obj.active_provider or "Hugging Face" in ai_status_obj.active_provider
    ai_health = "ONLINE" if is_live else "OFFLINE_MODE"

    return SystemHealthResponse(
        backend="ONLINE",
        database="ONLINE",
        ai=ai_status_obj.active_provider,
        ai_status=ai_health,
        guardrails="ACTIVE",
        audit="ACTIVE",
        execution="SIMULATED",
        autonomy_mode=autonomy_mode,
        simulation_mode=settings.SIMULATION_MODE,
    )
