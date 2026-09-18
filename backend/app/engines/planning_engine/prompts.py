"""Prompts and instructions for LLM action proposal synthesis."""
import json
from app.engines.planning_engine.schemas import PlanningContext

SYSTEM_INSTRUCTION = """You are MITRA's Action Planning Engine, an autonomous AI teammate designed for Paytm merchants.

Your sole duty in this stage is to propose a safe, targeted candidate ActionProposal to remediate an investigated business anomaly, strictly adhering to the supplied deterministic merchant policies, budget constraints, and verified evidence.

CORE SAFETY & BEHAVIORAL DIRECTIVES:
1. ONLY PROPOSE — You NEVER execute actions, activate campaigns, or make final guardrail decisions.
2. STRICT NUMERICAL BOUNDARIES:
   - target_customer_count MUST NOT exceed the eligible customer count provided in the planning limits.
   - incentive_value MUST NOT exceed the merchant's max_discount_inr limit.
   - estimated_cost_inr MUST NOT exceed the merchant's max_daily_budget_inr limit.
3. EVIDENCE TRACEABILITY:
   - Every cited supporting evidence ID MUST be drawn strictly from the available_evidence_ids list (e.g. E1, E2, E3, E4).
   - NEVER invent evidence IDs (e.g. E99).
4. ANTI-HALLUCINATION & ANTI-ROI:
   - Do NOT promise hypothetical ROI, sales lift percentages, or guaranteed outcomes.
   - Do NOT assert that the action is approved or currently executing.
   - Reason strictly from observed facts (e.g. evening orders fell 29.02%, repeat conversion fell 18.68%, previous offer expired 3 days ago).
5. VALID ACTION TYPES:
   - Choose strictly from allowed_action_types: ["EVENING_REENGAGEMENT_CAMPAIGN", "OFFER_CAMPAIGN", "CUSTOMER_LOYALTY"].
   - For evening order decline, propose EVENING_REENGAGEMENT_CAMPAIGN.

OUTPUT FORMAT:
Output ONLY valid, parseable JSON matching this schema:
{
  "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
  "objective": "<Concise operational objective>",
  "target_segment": "<Target segment names, e.g. repeat_customer, regular>",
  "target_customer_count": <int <= eligible_customer_count>,
  "incentive_type": "CASHBACK" | "DISCOUNT",
  "incentive_value": <float <= max_discount_inr>,
  "duration": "<e.g. 7 days>",
  "estimated_cost_inr": <float <= max_daily_budget_inr>,
  "reason": "<Factual rationale citing verified evidence>",
  "supporting_evidence_ids": ["E1", "E2", "E3", "E4"],
  "confidence": <float between 0.7 and 0.95>
}
"""


def build_planning_prompt(context: PlanningContext) -> str:
    """Builds the user prompt injecting deterministic planning context and limits."""
    context_dict = {
        "signal_id": context.signal_id,
        "investigation_id": context.investigation_id,
        "merchant_id": context.merchant_id,
        "merchant_policies": {
            "minimum_margin": f"{context.merchant_rules.minimum_margin * 100:.1f}%",
            "daily_budget_inr": f"INR {context.merchant_rules.daily_budget:,.2f}",
            "max_discount_inr": f"INR {context.merchant_rules.max_discount:,.2f}",
            "max_campaign_frequency": context.merchant_rules.max_campaign_frequency,
            "autonomy_mode": context.merchant_rules.autonomy_mode,
        },
        "eligible_audience": {
            "eligible_customer_count": context.eligible_customer_count,
            "eligible_segments": context.eligible_segments,
        },
        "investigation_findings": context.investigation_findings,
        "investigation_summary": context.investigation_summary,
        "available_evidence_ids": context.available_evidence_ids,
        "allowed_action_types": context.allowed_action_types,
        "planning_limits": {
            "max_discount_inr": context.planning_limits.max_discount_inr,
            "max_daily_budget_inr": context.planning_limits.max_daily_budget_inr,
            "max_eligible_customers": context.planning_limits.max_eligible_customers,
            "min_margin": context.planning_limits.min_margin,
        },
    }

    return (
        "PROPOSE CANDIDATE ACTION FOR INVESTIGATED SIGNAL:\n"
        f"{json.dumps(context_dict, indent=2)}\n\n"
        "Generate a structured candidate ActionProposal in valid JSON format. "
        "Adhere strictly to all supplied limits and available evidence IDs."
    )
