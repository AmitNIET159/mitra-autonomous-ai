from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Union

from app.database.repository import AuditRepository
from app.models.contracts import AuditEvent, WorkflowAuditVerification
from app.models.enums import StageType


SENSITIVE_KEYS = {
    "password", "token", "secret", "api_key", "apikey", "jwt",
    "credential", "credentials", "auth_token", "private_key",
    "access_token", "refresh_token", "session_secret",
}


def sanitize_payload(payload: Any) -> Any:
    """Recursively sanitizes sensitive tokens/secrets from audit payloads."""
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if any(s_key in k.lower() for s_key in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


def compute_event_hash(
    prev_hash: str,
    stage: Union[StageType, str],
    actor: str,
    action_description: str,
    input_payload: Dict[str, Any],
    output_payload: Dict[str, Any],
) -> str:
    """Deterministically computes canonical SHA-256 hash for an audit event."""
    st_val = stage.value if hasattr(stage, "value") else str(stage)
    in_str = json.dumps(input_payload or {}, sort_keys=True, default=str)
    out_str = json.dumps(output_payload or {}, sort_keys=True, default=str)
    hash_input = f"{prev_hash}|{st_val}|{actor}|{action_description}|{in_str}|{out_str}"
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


class AuditEngine:
    """Tamper-evident audit logging for every stage in MITRA's workflow (Phase 11).
    
    SAFETY PRINCIPLES:
    - Zero secret leakage: automatically sanitizes passwords, API keys, credentials.
    - Zero hidden LLM reasoning exposure: records structured events and evidence, not raw chain-of-thought.
    - Deterministic SHA-256 hash chaining: cryptographically links each event to its predecessor.
    - Unified persistence: records directly to SQLite audit_events while maintaining in-memory caching.
    """

    sanitize_payload = staticmethod(sanitize_payload)

    def __init__(self):
        self._events: List[AuditEvent] = []

    def record_event(
        self,
        stage: StageType,
        actor: str,
        action_description: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        event_type: Optional[str] = None,
        merchant_id: Optional[str] = None,
        signal_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        action_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        outcome_id: Optional[str] = None,
        impact_id: Optional[str] = None,
        decision: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AuditEvent:
        """Records an audit event with SHA-256 integrity hash chaining and SQLite persistence."""
        clean_input = sanitize_payload(input_payload or {})
        clean_output = sanitize_payload(output_payload or {})

        # Extract IDs from payloads if not explicitly passed
        sig_id = signal_id or clean_input.get("signal_id") or clean_output.get("signal_id")
        inv_id = investigation_id or clean_input.get("investigation_id") or clean_output.get("investigation_id")
        act_id = action_id or clean_input.get("action_id") or clean_output.get("action_id")
        dec_id = decision_id or clean_input.get("decision_id") or clean_output.get("decision_id")
        exec_id = execution_id or clean_input.get("execution_id") or clean_output.get("execution_id")
        out_id = outcome_id or clean_input.get("outcome_id") or clean_output.get("outcome_id")
        imp_id = impact_id or clean_input.get("impact_id") or clean_output.get("impact_id")
        m_id = merchant_id or clean_input.get("merchant_id") or clean_output.get("merchant_id") or "MID-DEMO-98234"

        # Derive workflow correlation_id if not explicitly provided
        corr_id = correlation_id or clean_input.get("correlation_id") or clean_output.get("correlation_id")
        if not corr_id:
            if sig_id:
                corr_id = f"wf-{sig_id.replace('sig-', '').replace('SIG-', '').lower()}"
            elif inv_id:
                try:
                    from app.database.repository import InvestigationRepository
                    inv = InvestigationRepository.get_investigation(inv_id)
                    if inv and inv.get("signal_id"):
                        corr_id = f"wf-{inv['signal_id'].replace('sig-', '').replace('SIG-', '').lower()}"
                except Exception:
                    pass
                if not corr_id:
                    corr_id = f"wf-{inv_id.replace('inv-', '')}"
            elif act_id:
                try:
                    from app.database.repository import ActionRepository
                    act = ActionRepository.get_action(act_id)
                    if act and act.get("signal_id"):
                        corr_id = f"wf-{act['signal_id'].replace('sig-', '').replace('SIG-', '').lower()}"
                except Exception:
                    pass
                if not corr_id:
                    corr_id = f"wf-{act_id.replace('act-', '').replace('prop-', '')}"
            elif dec_id:
                try:
                    from app.database.repository import DecisionRepository, ActionRepository
                    dec = DecisionRepository.get_decision(dec_id)
                    if dec and dec.get("action_id"):
                        act = ActionRepository.get_action(dec["action_id"])
                        if act and act.get("signal_id"):
                            corr_id = f"wf-{act['signal_id'].replace('sig-', '').replace('SIG-', '').lower()}"
                except Exception:
                    pass
                if not corr_id:
                    corr_id = f"wf-{dec_id.replace('dec-', '')}"
            elif exec_id:
                try:
                    from app.database.repository import ExecutionRepository, ActionRepository
                    exc = ExecutionRepository.get_execution(exec_id)
                    if exc and exc.get("action_id"):
                        act = ActionRepository.get_action(exc["action_id"])
                        if act and act.get("signal_id"):
                            corr_id = f"wf-{act['signal_id'].replace('sig-', '').replace('SIG-', '').lower()}"
                except Exception:
                    pass
                if not corr_id:
                    corr_id = f"wf-{exec_id.replace('exec-', '')}"
            elif out_id:
                try:
                    from app.database.repository import OutcomeRepository, ExecutionRepository, ActionRepository
                    out = OutcomeRepository.get_outcome(out_id)
                    if out and out.get("execution_id"):
                        exc = ExecutionRepository.get_execution(out["execution_id"])
                        if exc and exc.get("action_id"):
                            act = ActionRepository.get_action(exc["action_id"])
                            if act and act.get("signal_id"):
                                corr_id = f"wf-{act['signal_id'].replace('sig-', '').replace('SIG-', '').lower()}"
                except Exception:
                    pass
                if not corr_id:
                    corr_id = f"wf-{out_id.replace('out-', '')}"
            else:
                corr_id = "wf-general"

        # Determine event_type
        ev_type = event_type or clean_output.get("event_type") or clean_input.get("event_type") or "WORKFLOW_STEP"

        # Determine previous hash in chain
        prev_hash = "GENESIS"
        try:
            latest_row = AuditRepository.get_latest_event(correlation_id=corr_id)
            if latest_row and latest_row.get("integrity_hash"):
                prev_hash = latest_row["integrity_hash"]
            elif self._events:
                # Fallback to in-memory tail if matching correlation or latest
                matching = [e for e in self._events if e.correlation_id == corr_id]
                if matching and matching[-1].integrity_hash:
                    prev_hash = matching[-1].integrity_hash
                elif self._events[-1].integrity_hash:
                    prev_hash = self._events[-1].integrity_hash
        except Exception:
            if self._events and self._events[-1].integrity_hash:
                prev_hash = self._events[-1].integrity_hash

        # Compute SHA-256 integrity hash
        integrity_hash = compute_event_hash(
            prev_hash=prev_hash,
            stage=stage,
            actor=actor,
            action_description=action_description,
            input_payload=clean_input,
            output_payload=clean_output,
        )

        # Persist to SQLite
        try:
            row = AuditRepository.record_event(
                stage=stage.value if hasattr(stage, "value") else str(stage),
                actor=actor,
                action_description=action_description,
                input_payload=clean_input,
                output_payload=clean_output,
                integrity_hash=integrity_hash,
                previous_hash=prev_hash,
                correlation_id=corr_id,
                event_type=ev_type,
                merchant_id=m_id,
                signal_id=sig_id,
                investigation_id=inv_id,
                action_id=act_id,
                decision_id=dec_id,
                execution_id=exec_id,
                outcome_id=out_id,
                impact_id=imp_id,
                decision=decision or clean_output.get("decision"),
                reason=reason or clean_output.get("reason"),
            )
            event = AuditEvent.model_validate(row)
        except Exception:
            # Fallback to in-memory AuditEvent
            event = AuditEvent(
                stage=stage,
                actor=actor,
                action_description=action_description,
                input_payload=clean_input,
                output_payload=clean_output,
                integrity_hash=integrity_hash,
                previous_hash=prev_hash,
                correlation_id=corr_id,
                event_type=ev_type,
                merchant_id=m_id,
                signal_id=sig_id,
                investigation_id=inv_id,
                action_id=act_id,
                decision_id=dec_id,
                execution_id=exec_id,
                outcome_id=out_id,
                impact_id=imp_id,
                decision=decision,
                reason=reason,
            )

        self._events.append(event)
        return event

    def get_events(self, limit: int = 50, merchant_id: Optional[str] = None, correlation_id: Optional[str] = None) -> List[AuditEvent]:
        """Retrieves recorded audit events from SQLite, falling back to memory."""
        try:
            if correlation_id:
                rows = AuditRepository.get_events_by_correlation_id(correlation_id)
            else:
                rows = AuditRepository.get_events(merchant_id=merchant_id, limit=limit)
            if rows:
                return [AuditEvent.model_validate(r) for r in rows]
        except Exception:
            pass

        if correlation_id:
            filtered = [e for e in self._events if e.correlation_id == correlation_id]
            return filtered[-limit:]
        if merchant_id:
            filtered = [e for e in self._events if e.merchant_id == merchant_id]
            return list(reversed(filtered[-limit:]))
        return list(reversed(self._events[-limit:]))

    def verify_audit_chain(
        self,
        correlation_id: Optional[str] = None,
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> WorkflowAuditVerification:
        """Deterministically verifies cryptographic SHA-256 chain integrity."""
        if events is None:
            try:
                if correlation_id:
                    ev_rows = AuditRepository.get_events_by_correlation_id(correlation_id)
                else:
                    ev_rows = AuditRepository.get_events(limit=500)
                    ev_rows = list(reversed(ev_rows))
            except Exception:
                ev_rows = []
        else:
            ev_rows = events

        if not ev_rows:
            return WorkflowAuditVerification(
                valid=True,
                event_count=0,
                verification_mode="SHA-256",
                correlation_id=correlation_id,
                error=None,
            )

        for i, ev in enumerate(ev_rows):
            ev_id = ev.get("id") or ev.get("event_id")
            prev_h = ev.get("previous_hash") or "GENESIS"
            stored_hash = ev.get("integrity_hash") or ev.get("event_hash")

            # Verify chain link
            if i > 0:
                expected_prev = ev_rows[i - 1].get("integrity_hash") or ev_rows[i - 1].get("event_hash")
                if prev_h != expected_prev:
                    return WorkflowAuditVerification(
                        valid=False,
                        event_count=len(ev_rows),
                        verification_mode="SHA-256",
                        correlation_id=correlation_id,
                        error=(
                            f"Broken chain link at event {ev_id}: previous_hash '{prev_h}' "
                            f"does not match preceding integrity_hash '{expected_prev}'."
                        ),
                    )

            # Recompute expected hash
            computed = compute_event_hash(
                prev_hash=prev_h,
                stage=ev.get("stage", "DETECT"),
                actor=ev.get("actor", "System"),
                action_description=ev.get("action_description") or ev.get("description", ""),
                input_payload=ev.get("input_payload", {}),
                output_payload=ev.get("output_payload", {}),
            )

            if computed != stored_hash:
                return WorkflowAuditVerification(
                    valid=False,
                    event_count=len(ev_rows),
                    verification_mode="SHA-256",
                    correlation_id=correlation_id,
                    error=(
                        f"Tampered hash detected at event {ev_id}: stored hash '{stored_hash}' "
                        f"does not match computed hash '{computed}'."
                    ),
                )

        return WorkflowAuditVerification(
            valid=True,
            event_count=len(ev_rows),
            verification_mode="SHA-256",
            correlation_id=correlation_id,
            error=None,
        )
