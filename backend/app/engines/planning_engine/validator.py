"""Strict validator for LLM-generated ActionProposal."""
import json
import re
from typing import Any, Dict, Optional, Tuple

from app.engines.planning_engine.schemas import PlanningContext
from app.models.contracts import ActionProposal
from app.models.enums import ActionType


class ActionValidator:
    """Enforces strict code-level verification on candidate action proposals.
    
    Rejects:
    - Invalid JSON syntax
    - Unknown evidence IDs (e.g. E99)
    - Unallowed action types
    - Target count exceeding eligible customers
    - Incentive value exceeding merchant max discount
    - Estimated cost exceeding daily budget
    - Missing required fields
    - Fabricated or unapproved status claims
    """

    @classmethod
    def validate_and_parse(
        cls,
        raw_llm_response: str,
        context: PlanningContext,
        action_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[ActionProposal], Optional[str]]:
        """Validates raw LLM response against deterministic planning boundaries."""
        cleaned = raw_llm_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except Exception as exc:
            return False, None, f"Failed to parse LLM JSON response: {exc}"

        if not isinstance(data, dict):
            return False, None, "LLM response is not a valid JSON object."

        # 1. Required fields check
        required_fields = [
            "action_type",
            "target_customer_count",
            "incentive_type",
            "incentive_value",
            "reason",
            "supporting_evidence_ids",
        ]
        for f in required_fields:
            if f not in data or data[f] is None:
                return False, None, f"Missing required field in ActionProposal: '{f}'"

        # 2. Action Type verification
        raw_action_type = str(data["action_type"]).strip().upper()
        if raw_action_type not in context.allowed_action_types:
            return False, None, f"Unallowed action type '{raw_action_type}'. Allowed: {context.allowed_action_types}"

        try:
            action_type_enum = ActionType(raw_action_type)
        except Exception:
            # Fallback to general offer campaign enum if matched
            if "CAMPAIGN" in raw_action_type:
                action_type_enum = ActionType.OFFER_CAMPAIGN
            else:
                return False, None, f"Unknown action type enum: {raw_action_type}"

        # 3. Supporting evidence IDs verification (zero tolerance for hallucinated IDs)
        evidence_ids = data.get("supporting_evidence_ids")
        if not isinstance(evidence_ids, list) or len(evidence_ids) == 0:
            return False, None, "ActionProposal must cite at least one supporting evidence ID."

        allowed_ids = set(context.available_evidence_ids)
        for eid in evidence_ids:
            if str(eid) not in allowed_ids:
                return False, None, f"Unknown evidence ID '{eid}' not present in verified context {list(allowed_ids)}"

        # 4. Target customer count boundary
        try:
            target_count = int(data["target_customer_count"])
        except (ValueError, TypeError):
            return False, None, "target_customer_count must be an integer."

        if target_count <= 0:
            return False, None, "target_customer_count must be greater than 0."

        if target_count > context.planning_limits.max_eligible_customers:
            return (
                False,
                None,
                f"Target customer count {target_count} exceeds eligible customers {context.planning_limits.max_eligible_customers}.",
            )

        # 5. Incentive value boundary (cannot exceed max_discount_inr)
        try:
            incentive_val = float(data["incentive_value"])
        except (ValueError, TypeError):
            return False, None, "incentive_value must be a numeric value."

        if incentive_val <= 0:
            return False, None, "incentive_value must be greater than 0."

        if incentive_val > context.planning_limits.max_discount_inr:
            return (
                False,
                None,
                f"Incentive value INR {incentive_val:.2f} exceeds merchant maximum discount INR {context.planning_limits.max_discount_inr:.2f}.",
            )

        # 6. Budget / Estimated cost boundary (cannot exceed max_daily_budget_inr)
        estimated_cost = float(data.get("estimated_cost_inr") or (incentive_val * min(target_count, 100)))
        if estimated_cost > context.planning_limits.max_daily_budget_inr:
            return (
                False,
                None,
                f"Estimated cost INR {estimated_cost:.2f} exceeds merchant daily budget INR {context.planning_limits.max_daily_budget_inr:.2f}.",
            )

        # 7. Disallow claiming approval or execution
        reason_text = str(data["reason"])
        prohibited_claims = ["already approved", "is approved", "executed", "campaign is live", "guaranteed roi", "guaranteed profit"]
        for p in prohibited_claims:
            if p in reason_text.lower():
                return False, None, f"Proposal claims premature approval/execution: '{p}'"

        # 8. Assemble validated ActionProposal
        import uuid
        proposal_id = action_id or f"prop-{uuid.uuid4().hex[:10]}"
        parameters = {
            "incentive_type": str(data.get("incentive_type", "CASHBACK")),
            "incentive_value": incentive_val,
            "discount_amount": incentive_val,
            "target_segment": str(data.get("target_segment", "repeat_customer, regular")),
            "target_customer_count": target_count,
            "target_count": target_count,
            "duration": str(data.get("duration", "7 days")),
            "budget_inr": estimated_cost,
        }

        constraints_snapshot = {
            "max_discount_inr": context.planning_limits.max_discount_inr,
            "max_daily_budget_inr": context.planning_limits.max_daily_budget_inr,
            "eligible_customers": context.planning_limits.max_eligible_customers,
            "minimum_margin": context.planning_limits.min_margin,
            "autonomy_mode": context.merchant_rules.autonomy_mode,
        }

        proposal = ActionProposal(
            proposal_id=proposal_id,
            action_id=proposal_id,
            signal_id=context.signal_id,
            investigation_id=context.investigation_id,
            merchant_id=context.merchant_id,
            action_type=action_type_enum,
            objective=str(data.get("objective", "Re-engage evening drop-off cohort with targeted incentive")),
            target_segment=str(data.get("target_segment", "repeat_customer, regular")),
            target_customer_count=target_count,
            incentive_type=str(data.get("incentive_type", "CASHBACK")),
            incentive_value=incentive_val,
            duration=str(data.get("duration", "7 days")),
            parameters=parameters,
            reason=reason_text,
            confidence=float(data.get("confidence", 0.85)),
            estimated_cost_inr=estimated_cost,
            supporting_evidence_ids=[str(e) for e in evidence_ids],
            constraints=constraints_snapshot,
            projected_impact={
                "target_reach": target_count,
                "reengagement_window": str(data.get("duration", "7 days")),
            },
            status="PROPOSED",
            is_fallback=False,
        )

        return True, proposal, None
