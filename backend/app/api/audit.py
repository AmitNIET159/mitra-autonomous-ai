"""REST API Endpoints for MITRA Audit Trail Engine (Phase 11).

SAFETY & INTEGRITY PRINCIPLES:
- Strictly read-only: No external mutation or tampering allowed via API.
- Zero secret leakage: Credentials and tokens are automatically sanitized.
- Cryptographic verification: Validates SHA-256 hash chaining and detects tampering.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database.repository import AuditRepository
from app.engines.audit_engine.engine import AuditEngine
from app.models.contracts import AuditEvent, WorkflowAuditVerification

router = APIRouter(tags=["Audit Trail & Verification"])
audit_engine = AuditEngine()


@router.get(
    "/audit/events",
    response_model=List[AuditEvent],
    summary="Query tamper-evident audit events",
)
def list_audit_events(
    merchant_id: str = Query("MID-DEMO-98234", description="Merchant Identifier"),
    correlation_id: Optional[str] = Query(None, description="Optional Workflow Correlation ID filter"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
) -> List[AuditEvent]:
    """Retrieves chronological audit events for a merchant or specific workflow correlation ID."""
    return audit_engine.get_events(limit=limit, merchant_id=merchant_id, correlation_id=correlation_id)


@router.get(
    "/audit/events/{event_id}",
    response_model=AuditEvent,
    summary="Retrieve single audit event by ID",
)
def get_audit_event(event_id: str) -> AuditEvent:
    """Retrieves an authoritative audit event by event ID."""
    row = AuditRepository.get_event(event_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit event '{event_id}' not found in audit ledger.",
        )
    return AuditEvent.model_validate(row)


@router.get(
    "/audit/workflow/{correlation_id}",
    response_model=List[AuditEvent],
    summary="Retrieve audit chain for a workflow",
)
def get_workflow_audit_chain(correlation_id: str) -> List[AuditEvent]:
    """Retrieves the complete, ordered audit chain for a workflow correlation ID."""
    events = audit_engine.get_events(correlation_id=correlation_id, limit=500)
    return events


@router.get(
    "/audit/workflow/{correlation_id}/verify",
    response_model=WorkflowAuditVerification,
    summary="Cryptographically verify SHA-256 audit chain integrity",
)
def verify_workflow_audit(correlation_id: str) -> WorkflowAuditVerification:
    """Validates the cryptographic SHA-256 hash chaining of a workflow audit trail.
    
    Verifies that:
    1. Genesis previous_hash matches expected anchor.
    2. Every subsequent event's previous_hash equals the preceding event's integrity_hash.
    3. Recomputing sha256(prev_hash | stage | actor | action | input | output) matches the stored hash.
    4. Detects any manual database modification or tamper attempt without silently repairing it.
    """
    verification = audit_engine.verify_audit_chain(correlation_id=correlation_id)
    return verification
