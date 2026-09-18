"""Deterministic Outcome Engine Rules and Digital-Twin Metric Generator.

SAFETY & PROTOTYPE BOUNDARIES:
- 100% Deterministic and rule-based calculations.
- Zero live Paytm APIs, zero money movement, zero real customer or merchant data.
- Purely synthetic/digital-twin simulation environment.
- Descriptive metric comparison only: strictly avoids any causal claims.
"""
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, Optional, Tuple

from app.models.enums import ExecutionMode, ExecutionState, OutcomeStatus


class OutcomeEngineError(Exception):
    """Base exception for outcome engine errors."""
    pass


class ExecutionNotFoundError(OutcomeEngineError):
    """Raised when the specified execution record does not exist."""
    pass


class ExecutionNotCompletedError(OutcomeEngineError):
    """Raised when attempting to measure an execution that is not COMPLETED."""
    pass


class NonSimulationExecutionError(OutcomeEngineError):
    """Raised when execution mode is not SIMULATION."""
    pass


class InsufficientMeasurementDataError(OutcomeEngineError):
    """Raised when baseline data is missing or statistically unusable."""
    pass


def verify_execution_preconditions(execution_row: Dict[str, Any]) -> None:
    """Deterministically verifies that execution is eligible for outcome measurement.
    
    PRECONDITIONS:
    1. execution_state must be strictly COMPLETED.
    2. execution_mode must be strictly SIMULATION.
    """
    if not execution_row:
        raise ExecutionNotFoundError("Execution record does not exist.")

    state = execution_row.get("execution_state") or execution_row.get("status")
    if state != ExecutionState.COMPLETED.value:
        raise ExecutionNotCompletedError(
            f"Cannot measure outcome: execution state is '{state}'. "
            f"Only COMPLETED executions can be measured."
        )

    mode = execution_row.get("execution_mode") or "SIMULATION"
    if mode != ExecutionMode.SIMULATION.value:
        raise NonSimulationExecutionError(
            f"Cannot measure outcome: execution mode is '{mode}'. "
            f"Only SIMULATION mode is permitted in prototype."
        )


def calculate_metric_change(
    baseline: Optional[float],
    post_action: Optional[float],
) -> Dict[str, Any]:
    """Calculates deterministic absolute and percentage change between baseline and post-action.
    
    Prevents division by zero.
    Returns status INSUFFICIENT_DATA if baseline is missing or 0.
    """
    if baseline is None or baseline == 0.0:
        abs_change = round((post_action or 0.0) - (baseline or 0.0), 2)
        return {
            "baseline": baseline,
            "post_action": post_action,
            "absolute_change": abs_change,
            "percentage_change": None,
            "status": OutcomeStatus.INSUFFICIENT_DATA.value,
            "is_positive": (post_action or 0.0) > 0.0 if baseline == 0.0 else None,
            "description": "Baseline is 0 or unavailable; percentage change undefined.",
        }

    p_val = post_action if post_action is not None else baseline
    abs_change = round(p_val - baseline, 2)
    pct_change = round(((p_val - baseline) / baseline) * 100.0, 2)

    return {
        "baseline": round(float(baseline), 2),
        "post_action": round(float(p_val), 2),
        "absolute_change": abs_change,
        "percentage_change": pct_change,
        "status": OutcomeStatus.MEASURED.value,
        "is_positive": pct_change > 0.0,
        "description": f"Observed simulated change: {'+' if pct_change >= 0 else ''}{pct_change}%",
    }


def generate_digital_twin_metrics(
    approved_action: Dict[str, Any],
    baseline_metrics: Dict[str, float],
) -> Dict[str, float]:
    """Deterministically transforms baseline metrics into post-action simulation metrics.
    
    CRITICAL:
    - Driven STRICTLY by approved_action (clamped parameters from Phase 6/7/8).
    - If parameters were clamped (e.g. INR 100 instead of INR 150), uses clamped value.
    - Purely mathematical model calibrated to the Sharma Kirana seed scenario.
    - Marked clearly as SIMULATED.
    """
    params = approved_action.get("parameters") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}

    # Extract deterministic parameters from approved_action
    incentive = float(
        approved_action.get("incentive_value")
        or params.get("cashback_inr")
        or params.get("discount_amount")
        or 50.0
    )
    target_count = int(
        approved_action.get("target_customer_count")
        or params.get("target_customer_count")
        or params.get("target_count")
        or 486
    )

    # Base values from baseline
    base_rev = float(baseline_metrics.get("revenue", 481850.0) or 481850.0)
    base_orders = float(baseline_metrics.get("orders", 1284.0) or 1284.0)
    base_evening = float(baseline_metrics.get("evening_orders", 291.0) or 291.0)
    base_conv = float(baseline_metrics.get("target_customer_conversion", 0.148) or 0.148)

    # Deterministic multiplier based on incentive scaling (baseline demo is INR 50)
    # Clamp scale between 0.5 and 2.5 to prevent extreme explosions
    scale = min(2.5, max(0.5, incentive / 50.0))

    # Incremental impacts (calibrated: INR 50 yields +40 evening orders, +172 total orders)
    inc_evening_orders = round(40.0 * scale * (target_count / 486.0))
    inc_total_orders = round(172.0 * scale * (target_count / 486.0))
    inc_revenue = round(18150.0 * scale * (target_count / 486.0), 2)

    post_evening_orders = base_evening + inc_evening_orders
    post_orders = base_orders + inc_total_orders
    post_revenue = round(base_rev + inc_revenue, 2)
    post_aov = round(post_revenue / max(1.0, post_orders), 2)
    post_conv = round(min(0.35, base_conv + (0.028 * scale)), 3)

    return {
        "revenue": post_revenue,
        "orders": post_orders,
        "gmv": post_revenue,
        "evening_orders": post_evening_orders,
        "average_order_value": post_aov,
        "target_customer_orders": round(382.0 + inc_evening_orders),
        "target_customer_conversion": post_conv,
        "target_segment_activity": round(min(95.0, 72.5 + (8.5 * scale)), 1),
    }


def get_default_windows() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Returns deterministic start and end timestamps for baseline and measurement windows."""
    ref_time = datetime(2026, 9, 17, 21, 0, 0, tzinfo=timezone.utc)
    baseline_window = {
        "start": (ref_time - timedelta(days=10)).isoformat(),
        "end": ref_time.isoformat(),
        "duration_days": 10,
        "label": "10-Day Pre-Action Baseline",
    }
    measurement_window = {
        "start": ref_time.isoformat(),
        "end": (ref_time + timedelta(days=7)).isoformat(),
        "duration_days": 7,
        "label": "7-Day Post-Action Simulated Observation Window",
    }
    return baseline_window, measurement_window
