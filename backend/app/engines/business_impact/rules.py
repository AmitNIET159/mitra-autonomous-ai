"""Deterministic Business Impact Engine Rules and ROI Calculations.

SAFETY & PROTOTYPE BOUNDARIES:
- 100% Deterministic and rule-based calculations.
- Zero live Paytm APIs, zero money movement, zero real customer or merchant data.
- Purely synthetic/digital-twin simulation environment.
- Strictly descriptive non-causal language and zero COGS fabrication.
- Consumes strictly the persisted Phase 9 Outcome.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional, Tuple

from app.models.enums import ImpactClassification, ImpactStatus, OutcomeStatus


class BusinessImpactError(Exception):
    """Base exception for business impact engine errors."""
    pass


class OutcomeNotFoundError(BusinessImpactError):
    """Raised when the specified outcome record does not exist (HTTP 404)."""
    pass


class OutcomeNotMeasuredError(BusinessImpactError):
    """Raised when attempting to analyze an outcome that has not been measured (HTTP 409)."""
    pass


class InsufficientImpactDataError(BusinessImpactError):
    """Raised when outcome data is insufficient to compute business impact."""
    pass


def verify_outcome_preconditions(outcome_row: Optional[Dict[str, Any]]) -> None:
    """Deterministically verifies that outcome is eligible for business impact analysis.
    
    PRECONDITIONS:
    1. Outcome must exist.
    2. Outcome status must be MEASURED or INSUFFICIENT_DATA.
       If PENDING, FAILED, or unmeasured, raises OutcomeNotMeasuredError (HTTP 409).
    """
    if not outcome_row:
        raise OutcomeNotFoundError("Outcome measurement record does not exist.")

    status = outcome_row.get("outcome_status") or outcome_row.get("status")
    if status == OutcomeStatus.INSUFFICIENT_DATA.value:
        # Permitted; will result in INSUFFICIENT_DATA business impact
        return

    if status != OutcomeStatus.MEASURED.value:
        raise OutcomeNotMeasuredError(
            f"Cannot calculate business impact: outcome measurement is required first. "
            f"Current outcome status is '{status}'."
        )


def calculate_campaign_cost(approved_action: Dict[str, Any]) -> float:
    """Deterministically extracts or calculates the campaign cost from approved/executed action.
    
    CRITICAL INVARIANT:
    - Strictly driven by approved_action (e.g. INR 100 clamped value), NEVER original proposal (INR 150).
    - Checks incentive_value * target_customer_count.
    - Zero division and negative cost safe.
    """
    if not approved_action:
        return 0.0

    params = approved_action.get("parameters") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}

    # Extract incentive (cashback / discount)
    incentive = 0.0
    for key in ("incentive_value", "cashback_inr", "discount_amount", "reward_amount"):
        val = approved_action.get(key) or params.get(key)
        if val is not None:
            try:
                incentive = float(val)
                break
            except (ValueError, TypeError):
                pass

    # Extract target customer count
    target_count = 0
    for key in ("target_customer_count", "target_count", "customer_count", "audience_size"):
        val = approved_action.get(key) or params.get(key)
        if val is not None:
            try:
                target_count = int(val)
                break
            except (ValueError, TypeError):
                pass

    # Fallback to estimated_cost_inr if explicit parameters are not separate
    if incentive <= 0.0 and target_count <= 0:
        est = approved_action.get("estimated_cost_inr") or params.get("estimated_cost_inr")
        if est is not None:
            try:
                return max(0.0, round(float(est), 2))
            except (ValueError, TypeError):
                return 0.0

    calculated_cost = round(max(0.0, incentive * target_count), 2)
    return calculated_cost


def calculate_business_impact_metrics(
    baseline_revenue: float,
    post_action_revenue: float,
    baseline_orders: float,
    post_action_orders: float,
    baseline_evening_orders: float,
    post_action_evening_orders: float,
    campaign_cost: float,
) -> Dict[str, Any]:
    """Deterministically calculates business impact metrics, ROI, and efficiency indicators.
    
    SAFETY:
    - Zero division safe (handles campaign_cost <= 0, incremental_orders <= 0).
    - No NaN, Infinity, or unhandled exceptions.
    - Zero COGS fabrication: gross_profit_impact remains None.
    """
    inc_revenue = round(post_action_revenue - baseline_revenue, 2)
    orders_diff = round(post_action_orders - baseline_orders, 2)
    inc_orders = max(0.0, orders_diff)
    evening_diff = round(post_action_evening_orders - baseline_evening_orders, 2)

    # Safe ROI calculation
    if campaign_cost <= 0.0:
        roi = None
        roi_pct = None
        cost_per_order = None
        rev_per_rupee = None
    else:
        roi = round((inc_revenue - campaign_cost) / campaign_cost, 4)
        roi_pct = round(roi * 100.0, 2)
        rev_per_rupee = round(inc_revenue / campaign_cost, 2)
        cost_per_order = (
            round(campaign_cost / inc_orders, 2) if inc_orders > 0.0 else None
        )

    # Gross profit impact: strictly None unless deterministic COGS is explicitly known
    gross_profit = None

    return {
        "incremental_revenue": inc_revenue,
        "orders_change": orders_diff,
        "incremental_orders": inc_orders,
        "evening_orders_change": evening_diff,
        "campaign_cost": campaign_cost,
        "gross_profit_impact": gross_profit,
        "roi": roi,
        "roi_percentage": roi_pct,
        "cost_per_incremental_order": cost_per_order,
        "revenue_per_campaign_rupee": rev_per_rupee,
    }


def classify_impact(
    roi: Optional[float],
    status: str,
) -> ImpactClassification:
    """Deterministically classifies simulated business impact.
    
    RULES:
    - If status == INSUFFICIENT_DATA or roi is None -> INSUFFICIENT_DATA
    - If roi > 0.0 -> POSITIVE
    - If roi == 0.0 -> NEUTRAL
    - If roi < 0.0 -> NEGATIVE
    """
    if status == ImpactStatus.INSUFFICIENT_DATA.value or roi is None:
        return ImpactClassification.INSUFFICIENT_DATA
    if roi > 0.0:
        return ImpactClassification.POSITIVE
    elif roi == 0.0:
        return ImpactClassification.NEUTRAL
    else:
        return ImpactClassification.NEGATIVE
