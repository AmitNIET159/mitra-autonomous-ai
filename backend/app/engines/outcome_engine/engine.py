"""Outcome Engine for MITRA (Autonomous AI Teammate for Paytm Merchants).

Phase 9: Outcome Monitoring & Measurement.
Monitors and measures post-execution simulated business impact strictly within
the digital twin sandbox environment.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from app.core.logging import logger
from app.database.connection import get_connection
from app.database.repository import ExecutionRepository, OutcomeRepository
from app.engines.audit_engine.engine import AuditEngine
from app.engines.outcome_engine.rules import (
    calculate_metric_change,
    generate_digital_twin_metrics,
    get_default_windows,
    verify_execution_preconditions,
    ExecutionNotFoundError,
    ExecutionNotCompletedError,
    InsufficientMeasurementDataError,
    NonSimulationExecutionError,
)
from app.models.contracts import Outcome
from app.models.enums import MeasurementMode, OutcomeStatus, StageType


class OutcomeEngine:
    """Deterministic Outcome Monitoring and Measurement Engine."""

    def __init__(self, audit_engine: Optional[AuditEngine] = None, simulation_mode: bool = True):
        self.audit_engine = audit_engine or AuditEngine()
        self.simulation_mode = simulation_mode

    def load_baseline_metrics(self, merchant_id: str) -> Dict[str, float]:
        """Loads baseline metrics from SQLite digital twin business_metrics table.
        
        Returns empty dictionary if metrics are missing or unavailable.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT metric_name, metric_value
                FROM business_metrics
                WHERE merchant_id = ?
                ORDER BY timestamp DESC
                """,
                (merchant_id,),
            )
            rows = cursor.fetchall()
            raw_metrics = {r["metric_name"]: float(r["metric_value"]) for r in rows}

            if not raw_metrics:
                return {}

            # Map raw business metrics to standardized outcome metrics
            return {
                "revenue": raw_metrics.get("total_window_revenue_inr", 481850.0),
                "orders": raw_metrics.get("total_window_orders", 1284.0),
                "gmv": raw_metrics.get("total_window_revenue_inr", 481850.0),
                "evening_orders": raw_metrics.get("evening_orders_observed", 291.0),
                "average_order_value": raw_metrics.get("avg_basket_size_inr", 375.27),
                "target_customer_orders": 382.0,
                "target_customer_conversion": raw_metrics.get("repeat_conversion_observed", 0.148),
                "target_segment_activity": 72.5,
            }
        except Exception as exc:
            logger.error("Error loading baseline metrics for %s: %s", merchant_id, exc)
            return {}
        finally:
            conn.close()

    def measure_outcome(
        self,
        execution_id: str,
        measurement_window: Optional[Dict[str, Any]] = None,
    ) -> Outcome:
        """Deterministically measures post-execution simulated outcomes.
        
        ENFORCES:
        - Execution must exist.
        - Execution must be COMPLETED.
        - Execution must be in SIMULATION mode.
        - Idempotency: Duplicate calls for same execution return existing outcome.
        - Strictly descriptive comparison: zero causal claims.
        """
        # 1. Audit request
        self.audit_engine.record_event(
            stage=StageType.LEARN,
            actor="OutcomeEngine",
            action_description="Outcome measurement requested for execution",
            input_payload={"execution_id": execution_id, "window": measurement_window},
            output_payload={"event_type": "OUTCOME_MEASUREMENT_REQUESTED"},
        )

        # 2. Load execution
        exec_row = ExecutionRepository.get_execution(execution_id)
        if not exec_row:
            self.audit_engine.record_event(
                stage=StageType.LEARN,
                actor="OutcomeEngine",
                action_description="Outcome measurement failed: execution not found",
                input_payload={"execution_id": execution_id},
                output_payload={"event_type": "OUTCOME_MEASUREMENT_FAILED", "error": "ExecutionNotFoundError"},
            )
            raise ExecutionNotFoundError(f"Execution {execution_id} not found in database.")

        # 3. Verify preconditions
        try:
            verify_execution_preconditions(exec_row)
        except Exception as exc:
            self.audit_engine.record_event(
                stage=StageType.LEARN,
                actor="OutcomeEngine",
                action_description=f"Outcome measurement failed precondition: {exc}",
                input_payload={"execution_id": execution_id, "state": exec_row.get("execution_state")},
                output_payload={"event_type": "OUTCOME_MEASUREMENT_FAILED", "error": str(exc)},
            )
            raise

        # 4. Check Idempotency
        existing_outcome = OutcomeRepository.get_outcome_by_execution(execution_id)
        if existing_outcome:
            logger.info("Idempotent outcome return for execution %s", execution_id)
            return Outcome.model_validate(existing_outcome)

        # 5. Determine measurement & baseline windows
        def_base_win, def_meas_win = get_default_windows()
        b_win = def_base_win
        m_win = measurement_window or def_meas_win

        merchant_id = exec_row.get("merchant_id") or "MID-DEMO-98234"
        decision_id = exec_row.get("decision_id")
        action_id = exec_row.get("action_id")

        # 6. Load baseline metrics
        base_metrics = self.load_baseline_metrics(merchant_id)
        if not base_metrics or "orders" not in base_metrics or base_metrics.get("orders", 0) == 0:
            logger.warning("Insufficient baseline data for merchant %s, execution %s", merchant_id, execution_id)
            insufficient_outcome_dict = OutcomeRepository.create_outcome(
                execution_id=execution_id,
                decision_id=decision_id,
                action_id=action_id,
                merchant_id=merchant_id,
                baseline_window=b_win,
                measurement_window=m_win,
                baseline_metrics={},
                post_action_metrics={},
                metric_changes={},
                outcome_status=OutcomeStatus.INSUFFICIENT_DATA.value,
                measurement_mode=MeasurementMode.SIMULATION.value,
                simulated=True,
            )
            self.audit_engine.record_event(
                stage=StageType.LEARN,
                actor="OutcomeEngine",
                action_description="Outcome measurement inconclusive: insufficient baseline data",
                input_payload={"execution_id": execution_id, "merchant_id": merchant_id},
                output_payload={
                    "event_type": "OUTCOME_INSUFFICIENT_DATA",
                    "outcome_id": insufficient_outcome_dict["id"],
                    "status": "INSUFFICIENT_DATA",
                },
            )
            return Outcome.model_validate(insufficient_outcome_dict)

        # 7. Generate deterministic post-action metrics
        approved_action = exec_row.get("approved_action") or {}
        if isinstance(approved_action, str):
            try:
                approved_action = json.loads(approved_action)
            except Exception:
                approved_action = {}

        post_metrics = generate_digital_twin_metrics(approved_action, base_metrics)

        # 8. Calculate deterministic metric changes
        metric_changes: Dict[str, Any] = {}
        for m_key, b_val in base_metrics.items():
            p_val = post_metrics.get(m_key)
            metric_changes[m_key] = calculate_metric_change(b_val, p_val)

        # 9. Persist outcome
        persisted_dict = OutcomeRepository.create_outcome(
            execution_id=execution_id,
            decision_id=decision_id,
            action_id=action_id,
            merchant_id=merchant_id,
            baseline_window=b_win,
            measurement_window=m_win,
            baseline_metrics=base_metrics,
            post_action_metrics=post_metrics,
            metric_changes=metric_changes,
            outcome_status=OutcomeStatus.MEASURED.value,
            measurement_mode=MeasurementMode.SIMULATION.value,
            simulated=True,
        )

        outcome = Outcome.model_validate(persisted_dict)

        # 10. Audit completion
        self.audit_engine.record_event(
            stage=StageType.LEARN,
            actor="OutcomeEngine",
            action_description="Measured simulated post-action outcome",
            input_payload={
                "merchant_id": merchant_id,
                "execution_id": execution_id,
                "decision_id": decision_id,
                "action_id": action_id,
                "measurement_window": m_win,
            },
            output_payload={
                "event_type": "OUTCOME_MEASURED",
                "outcome_id": outcome.outcome_id,
                "status": outcome.outcome_status.value,
                "evening_orders_delta_pct": outcome.delta_percentage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return outcome
