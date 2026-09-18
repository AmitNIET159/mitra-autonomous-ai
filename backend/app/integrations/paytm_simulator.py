"""Simulated Paytm Adapter for MITRA Hackathon Prototype.

ABSOLUTE SAFETY BOUNDARY:
- Strictly executes in digital-twin simulation mode.
- NEVER calls real Paytm APIs or external endpoints.
- NEVER requires or accepts live Paytm credentials.
- NEVER charges customers, transfers money, or alters production campaigns.
- All actions and results are synthetic simulations for demonstration.
"""
from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional
import uuid

from app.core.logging import logger


class RealExecutionNotAllowedError(Exception):
    """Raised when any live, non-simulation execution is requested."""
    pass


class SimulatedPaytmAdapter:
    """Deterministic simulated execution adapter for Paytm merchant actions."""

    def __init__(self, simulation_mode: bool = True):
        if not simulation_mode:
            raise RealExecutionNotAllowedError(
                "CRITICAL SAFETY BARRIER: Real Paytm execution is strictly disallowed in MITRA prototype. "
                "simulation_mode must be True."
            )
        self.simulation_mode = simulation_mode

    def simulate_campaign_execution(
        self,
        approved_action: Dict[str, Any],
        merchant_id: str = "MID-DEMO-98234",
    ) -> Dict[str, Any]:
        """Simulates campaign dispatch deterministically in digital twin sandbox.
        
        Args:
            approved_action: Immutable dictionary of approved action parameters.
            merchant_id: Unique merchant identifier.
            
        Returns:
            Deterministic dictionary confirming simulated execution receipt.
        """
        if not self.simulation_mode:
            raise RealExecutionNotAllowedError("Real Paytm API dispatch is strictly prohibited.")

        action_type = approved_action.get("action_type", "OFFER_CAMPAIGN")
        parameters = approved_action.get("parameters", {})
        
        # Extract target customer count
        target_customer_count = approved_action.get("target_customer_count")
        if target_customer_count is None:
            target_customer_count = parameters.get("target_customer_count", 486)
        try:
            target_customer_count = int(target_customer_count)
        except (ValueError, TypeError):
            target_customer_count = 486

        # Extract incentive value (must be the guardrail-approved clamped value)
        incentive_value = approved_action.get("incentive_value")
        if incentive_value is None:
            incentive_value = parameters.get("cashback_inr", parameters.get("discount_percentage", 50.0))
        try:
            incentive_value = float(incentive_value)
        except (ValueError, TypeError):
            incentive_value = 50.0

        # Extract duration
        duration_str = str(approved_action.get("duration", parameters.get("duration", "7 days")))
        match = re.search(r"(\d+)", duration_str)
        duration_days = int(match.group(1)) if match else 7

        # Extract estimated cost
        estimated_cost_inr = approved_action.get("estimated_cost_inr")
        if estimated_cost_inr is None:
            estimated_cost_inr = parameters.get("budget_inr", incentive_value * target_customer_count)
        try:
            estimated_cost_inr = float(estimated_cost_inr)
        except (ValueError, TypeError):
            estimated_cost_inr = 0.0

        simulation_id = f"sim-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        logger.info(
            "SimulatedPaytmAdapter dispatching: %s for %s (Audience: %d, Incentive: %.2f, Mode: SIMULATION)",
            action_type,
            merchant_id,
            target_customer_count,
            incentive_value,
        )

        return {
            "simulation_id": simulation_id,
            "status": "COMPLETED",
            "execution_mode": "SIMULATION",
            "mode": "SIMULATION",
            "merchant_id": merchant_id,
            "executed_action_type": action_type,
            "target_customer_count": target_customer_count,
            "incentive_value": incentive_value,
            "duration_days": duration_days,
            "estimated_cost_inr": estimated_cost_inr,
            "applied_parameters": parameters,
            "dispatched_at": now_iso,
            "message": "Campaign simulated successfully in digital twin sandbox. No real Paytm transaction.",
            "disclaimer": "SIMULATED - PROTOTYPE - NO REAL PAYTM TRANSACTION",
            "simulated": True,
        }
