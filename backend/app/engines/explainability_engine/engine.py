"""Deterministic Explainability Engine for MITRA (Phase 11).

SAFETY PRINCIPLES:
- Facts vs Hypotheses: Factual observations strictly decoupled from AI interpretations.
- Zero Numerical Hallucination: 100% of numbers extracted from authoritative SQLite digital twin.
- Zero Secret Leakage: Sensitive merchant tokens and system credentials excluded.
- Zero Hidden Reasoning Exposure: Displays structured evidence and deterministic rules, never raw chain-of-thought tokens.
- Non-Causal Framing: Strictly frames changes as descriptive observations within simulation.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.engines.audit_engine.engine import AuditEngine
from app.engines.explainability_engine.rules import (
    build_action_explanation,
    build_autonomy_explanation,
    build_business_impact_explanation,
    build_decision_explanation,
    build_execution_explanation,
    build_guardrail_explanation,
    build_outcome_explanation,
    build_signal_explanation,
    extract_facts_and_hypotheses,
    resolve_workflow_entities,
)
from app.models.contracts import ExplainabilitySummary, WorkflowAuditVerification


class ExplainabilityEngine:
    """Deterministic, structured explainability engine for MITRA workflows."""

    def __init__(self, audit_engine: Optional[AuditEngine] = None):
        self.audit_engine = audit_engine or AuditEngine()

    def generate_explanation(self, identifier: str) -> ExplainabilitySummary:
        """Generates comprehensive explainability summary for a workflow by correlation ID or entity ID."""
        entities = resolve_workflow_entities(identifier)
        corr_id = entities["correlation_id"]
        sig_row = entities["signal"]
        inv_row = entities["investigation"]
        act_row = entities["action"]
        grd_row = entities["guardrail"]
        dec_row = entities["decision"]
        aut_row = entities.get("autonomy")
        exec_row = entities["execution"]
        out_row = entities["outcome"]
        imp_row = entities["business_impact"]
        aud_events = entities["audit_events"]

        # Extract verified facts, hypotheses, and provenance
        facts, hypotheses, provenance = extract_facts_and_hypotheses(inv_row, sig_row, aut_row)

        # Build component explanations
        signal_summary = build_signal_explanation(sig_row)
        action_summary = build_action_explanation(act_row)
        guardrail_summary = build_guardrail_explanation(grd_row)
        decision_summary = build_decision_explanation(dec_row)
        autonomy_summary = build_autonomy_explanation(aut_row)
        execution_summary = build_execution_explanation(exec_row, act_row, grd_row)
        outcome_summary = build_outcome_explanation(out_row)
        business_impact_summary = build_business_impact_explanation(imp_row)

        # Cryptographically verify the SHA-256 audit chain
        audit_verification = self.audit_engine.verify_audit_chain(
            correlation_id=corr_id,
            events=aud_events,
        )

        # Standardized limitations
        limitations = [
            "All metrics and evaluations are computed inside a synthetic digital-twin sandbox environment.",
            "Zero real Paytm APIs were invoked; zero live money movement or real banking operations occurred.",
            "Merchant COGS and product margins are not modeled in simulation; gross profit impact is unavailable.",
            "All observed changes are descriptive associations within the observation window; causality is not asserted.",
        ]

        return ExplainabilitySummary(
            correlation_id=corr_id,
            merchant_id="MID-DEMO-98234",
            signal_summary=signal_summary,
            facts=facts,
            hypotheses=hypotheses,
            evidence_provenance=provenance,
            action_summary=action_summary,
            guardrail_summary=guardrail_summary,
            decision_summary=decision_summary,
            autonomy_summary=autonomy_summary,
            execution_summary=execution_summary,
            outcome_summary=outcome_summary,
            business_impact_summary=business_impact_summary,
            audit_timeline=aud_events,
            audit_verification=audit_verification,
            limitations=limitations,
            disclaimer=(
                "SIMULATED • PROTOTYPE • DIGITAL TWIN. This explanation describes deterministic prototype behavior "
                "in a digital twin sandbox. It is not evidence of real Paytm performance."
            ),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
