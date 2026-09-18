"""Schemas for MITRA Action Planning Engine."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.enums import ActionType


class MerchantRules(BaseModel):
    """Loaded deterministic merchant policy limits from SQLite digital-twin."""
    minimum_margin: float = 0.10
    daily_budget: float = 12000.0
    max_discount: float = 100.0
    max_campaign_frequency: int = 3
    autonomy_mode: str = "APPROVAL_REQUIRED"


class PlanningLimits(BaseModel):
    """Upper boundaries enforced during action candidate generation."""
    max_discount_inr: float = 100.0
    max_daily_budget_inr: float = 12000.0
    max_eligible_customers: int = 486
    min_margin: float = 0.10


class PlanningContext(BaseModel):
    """Structured deterministic planning context provided to Gemini or FallbackClient."""
    investigation_id: str
    signal_id: str
    merchant_id: str
    merchant_rules: MerchantRules
    eligible_customer_count: int
    eligible_segments: List[str] = Field(default_factory=lambda: ["repeat_customer", "regular"])
    investigation_findings: List[str] = Field(default_factory=list)
    investigation_summary: str = ""
    available_evidence_ids: List[str] = Field(default_factory=list)
    allowed_action_types: List[str] = Field(
        default_factory=lambda: [
            "EVENING_REENGAGEMENT_CAMPAIGN",
            "OFFER_CAMPAIGN",
            "CUSTOMER_LOYALTY",
        ]
    )
    planning_limits: PlanningLimits
    created_at: str


class ActionProposalOutput(BaseModel):
    """Structured schema expected from LLM JSON response."""
    action_type: str
    objective: str
    target_segment: str
    target_customer_count: int
    incentive_type: str
    incentive_value: float
    duration: str
    estimated_cost_inr: float
    reason: str
    supporting_evidence_ids: List[str]
    confidence: float = 0.85
