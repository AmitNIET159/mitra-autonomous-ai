"""Business Impact Engine for MITRA (Autonomous AI Teammate for Paytm Merchants).

Phase 10: ROI / Business Impact Analysis.
Deterministically calculates business impact and ROI from persisted Phase 9 outcomes
strictly within the digital-twin sandbox environment.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from app.core.logging import logger
from app.database.repository import (
    BusinessImpactRepository,
    ExecutionRepository,
    OutcomeRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.business_impact.rules import (
    calculate_business_impact_metrics,
    calculate_campaign_cost,
    classify_impact,
    verify_outcome_preconditions,
    BusinessImpactError,
    InsufficientImpactDataError,
    OutcomeNotFoundError,
    OutcomeNotMeasuredError,
)
from app.models.contracts import BusinessImpact
from app.models.enums import ImpactClassification, ImpactStatus, MeasurementMode, OutcomeStatus, StageType


class BusinessImpactEngine:
    """Deterministic Business Impact and ROI Analysis Engine."""

    def __init__(self, audit_engine: Optional[AuditEngine] = None, simulation_mode: bool = True):
        self.audit_engine = audit_engine or AuditEngine()
        self.simulation_mode = simulation_mode

    def analyze_impact(
        self,
        outcome_id: str,
    ) -> BusinessImpact:
        """Deterministically analyzes simulated business impact and ROI for a persisted outcome.
        
        ENFORCES:
        - Outcome must exist (HTTP 404 if missing).
        - Outcome must be MEASURED (HTTP 409 if unmeasured/pending/failed).
        - Single authoritative impact per outcome (Idempotent).
        - Campaign cost strictly derived from approved/executed action (MODIFY clamped invariant).
        - Zero division safety and zero COGS fabrication.
        - Audit trail logging with SHA-256 integrity hash chaining.
        """
        # 1. Audit request
        self.audit_engine.record_event(
            stage=StageType.LEARN,
            actor="BusinessImpactEngine",
            action_description="Business impact analysis requested for outcome",
            input_payload={"outcome_id": outcome_id},
            output_payload={"event_type": "BUSINESS_IMPACT_ANALYSIS_REQUESTED"},
        )

        # 2. Load outcome
        outcome_row = OutcomeRepository.get_outcome(outcome_id)
        if not outcome_row:
            self.audit_engine.record_event(
                stage=StageType.LEARN,
                actor="BusinessImpactEngine",
                action_description="Business impact analysis failed: outcome not found",
                input_payload={"outcome_id": outcome_id},
                output_payload={"event_type": "BUSINESS_IMPACT_FAILED", "error": "OutcomeNotFoundError"},
            )
            raise OutcomeNotFoundError(f"Outcome {outcome_id} not found in database.")

        # 3. Verify preconditions
        try:
            verify_outcome_preconditions(outcome_row)
        except Exception as exc:
            self.audit_engine.record_event(
                stage=StageType.LEARN,
                actor="BusinessImpactEngine",
                action_description=f"Business impact analysis failed precondition: {exc}",
                input_payload={"outcome_id": outcome_id, "status": outcome_row.get("outcome_status")},
                output_payload={"event_type": "BUSINESS_IMPACT_FAILED", "error": str(exc)},
            )
            raise

        # 4. Check Idempotency: single authoritative business impact per outcome
        existing = BusinessImpactRepository.get_by_outcome(outcome_id)
        if existing:
            logger.info("Idempotent business impact return for outcome %s", outcome_id)
            return BusinessImpact.model_validate(existing)

        execution_id = outcome_row.get("execution_id") or ""
        decision_id = outcome_row.get("decision_id")
        action_id = outcome_row.get("action_id")
        merchant_id = outcome_row.get("merchant_id") or "MID-DEMO-98234"
        out_status = outcome_row.get("outcome_status") or outcome_row.get("status")

        # 5. Handle INSUFFICIENT_DATA outcome
        if out_status == OutcomeStatus.INSUFFICIENT_DATA.value:
            logger.warning("Outcome %s has INSUFFICIENT_DATA, returning insufficient business impact", outcome_id)
            persisted_dict = BusinessImpactRepository.create_business_impact(
                outcome_id=outcome_id,
                execution_id=execution_id,
                decision_id=decision_id,
                action_id=action_id,
                merchant_id=merchant_id,
                impact_status=ImpactStatus.INSUFFICIENT_DATA.value,
                baseline_revenue=0.0,
                post_action_revenue=0.0,
                incremental_revenue=0.0,
                baseline_orders=0.0,
                post_action_orders=0.0,
                incremental_orders=0.0,
                orders_change=0.0,
                baseline_evening_orders=0.0,
                post_action_evening_orders=0.0,
                evening_orders_change=0.0,
                campaign_cost=0.0,
                gross_profit_impact=None,
                roi=None,
                roi_percentage=None,
                cost_per_incremental_order=None,
                revenue_per_campaign_rupee=None,
                impact_classification=ImpactClassification.INSUFFICIENT_DATA.value,
                measurement_mode=MeasurementMode.SIMULATION.value,
                simulated=True,
            )
            self.audit_engine.record_event(
                stage=StageType.LEARN,
                actor="BusinessImpactEngine",
                action_description="Business impact inconclusive: insufficient outcome data",
                input_payload={"outcome_id": outcome_id},
                output_payload={
                    "event_type": "BUSINESS_IMPACT_INCONCLUSIVE",
                    "impact_id": persisted_dict.get("id"),
                    "status": "INSUFFICIENT_DATA",
                },
            )
            return BusinessImpact.model_validate(persisted_dict)

        # 6. Resolve execution and extract approved action parameters
        exec_row = ExecutionRepository.get_execution(execution_id) if execution_id else None
        approved_action = {}
        if exec_row:
            raw_act = exec_row.get("approved_action") or {}
            if isinstance(raw_act, str):
                try:
                    approved_action = json.loads(raw_act)
                except Exception:
                    approved_action = {}
            elif isinstance(raw_act, dict):
                approved_action = raw_act

        # 7. Compute campaign cost from approved_action (Strictly clamped value in MODIFY flow)
        campaign_cost = calculate_campaign_cost(approved_action)

        # 8. Extract metrics from outcome
        base_metrics = outcome_row.get("baseline_metrics") or {}
        post_metrics = outcome_row.get("post_action_metrics") or {}

        base_rev = float(base_metrics.get("revenue") or base_metrics.get("gmv") or 0.0)
        post_rev = float(post_metrics.get("revenue") or post_metrics.get("gmv") or 0.0)
        base_orders = float(base_metrics.get("orders") or 0.0)
        post_orders = float(post_metrics.get("orders") or 0.0)
        base_evening = float(base_metrics.get("evening_orders") or 0.0)
        post_evening = float(post_metrics.get("evening_orders") or 0.0)

        # 9. Deterministic calculation
        impact_metrics = calculate_business_impact_metrics(
            baseline_revenue=base_rev,
            post_action_revenue=post_rev,
            baseline_orders=base_orders,
            post_action_orders=post_orders,
            baseline_evening_orders=base_evening,
            post_action_evening_orders=post_evening,
            campaign_cost=campaign_cost,
        )

        classification = classify_impact(
            roi=impact_metrics["roi"],
            status=ImpactStatus.CALCULATED.value,
        )

        # 10. Persist single authoritative business impact row
        persisted_dict = BusinessImpactRepository.create_business_impact(
            outcome_id=outcome_id,
            execution_id=execution_id,
            decision_id=decision_id,
            action_id=action_id,
            merchant_id=merchant_id,
            impact_status=ImpactStatus.CALCULATED.value,
            baseline_revenue=base_rev,
            post_action_revenue=post_rev,
            incremental_revenue=impact_metrics["incremental_revenue"],
            baseline_orders=base_orders,
            post_action_orders=post_orders,
            incremental_orders=impact_metrics["incremental_orders"],
            orders_change=impact_metrics["orders_change"],
            baseline_evening_orders=base_evening,
            post_action_evening_orders=post_evening,
            evening_orders_change=impact_metrics["evening_orders_change"],
            campaign_cost=impact_metrics["campaign_cost"],
            gross_profit_impact=impact_metrics["gross_profit_impact"],
            roi=impact_metrics["roi"],
            roi_percentage=impact_metrics["roi_percentage"],
            cost_per_incremental_order=impact_metrics["cost_per_incremental_order"],
            revenue_per_campaign_rupee=impact_metrics["revenue_per_campaign_rupee"],
            impact_classification=classification.value,
            measurement_mode=MeasurementMode.SIMULATION.value,
            simulated=True,
        )

        impact = BusinessImpact.model_validate(persisted_dict)

        # 11. Audit completion
        self.audit_engine.record_event(
            stage=StageType.LEARN,
            actor="BusinessImpactEngine",
            action_description="Calculated deterministic business impact and simulated ROI",
            input_payload={
                "outcome_id": outcome_id,
                "execution_id": execution_id,
                "campaign_cost": campaign_cost,
            },
            output_payload={
                "event_type": "BUSINESS_IMPACT_CALCULATED",
                "impact_id": impact.impact_id,
                "roi_percentage": impact.roi_percentage,
                "incremental_revenue": impact.incremental_revenue,
                "classification": impact.impact_classification.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return impact
