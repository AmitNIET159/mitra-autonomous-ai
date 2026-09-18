"""Deterministic context builder for MITRA action planning."""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

from app.database.repository import (
    CustomerRepository,
    InvestigationRepository,
    MerchantRepository,
)
from app.engines.planning_engine.schemas import (
    MerchantRules,
    PlanningContext,
    PlanningLimits,
)
from app.models.contracts import Investigation


class PlanningContextBuilder:
    """Builds structured deterministic planning context directly from digital-twin SQLite."""

    @staticmethod
    def build_context(
        investigation: Any,
        merchant_id: Optional[str] = None,
    ) -> PlanningContext:
        """Assembles deterministic merchant constraints, target audience, and findings."""
        if isinstance(investigation, Investigation):
            inv_id = investigation.investigation_id
            sig_id = investigation.signal_id
            mid = merchant_id or investigation.merchant_id
            findings = investigation.hypotheses or []
            summary = investigation.summary or ""
            evidence_ids = list(investigation.supporting_evidence.keys()) or ["E1", "E2", "E3", "E4", "E5"]
        elif hasattr(investigation, "investigation_id"):
            inv_id = str(investigation.investigation_id)
            sig_id = str(investigation.signal_id)
            mid = merchant_id or str(investigation.merchant_id)
            findings = getattr(investigation, "findings", []) or []
            summary = getattr(investigation, "summary", "") or ""
            evidence_ids = getattr(investigation, "evidence_ids", []) or ["E1", "E2", "E3", "E4", "E5"]
        else:
            inv_id = str(investigation)
            raw_inv = InvestigationRepository.get_investigation(inv_id)
            if not raw_inv:
                raise ValueError(f"Investigation with ID '{inv_id}' not found.")
            sig_id = raw_inv["signal_id"]
            mid = merchant_id or "MID-DEMO-98234"
            summary = raw_inv.get("summary") or ""
            try:
                findings_data = json.loads(raw_inv.get("hypotheses") or "[]")
                findings = [f.get("hypothesis", str(f)) if isinstance(f, dict) else str(f) for f in findings_data]
            except Exception:
                findings = [raw_inv.get("finding") or ""]
            try:
                evidence_ids = json.loads(raw_inv.get("evidence_ids") or "[]")
            except Exception:
                evidence_ids = ["E1", "E2", "E3", "E4", "E5"]

        # 1. Load merchant rules from SQLite
        raw_merchant = MerchantRepository.get_merchant(mid)
        if raw_merchant:
            min_margin = float(raw_merchant.get("minimum_margin", 0.10))
            daily_budget = float(raw_merchant.get("daily_budget", 12000.0))
            max_discount = float(raw_merchant.get("max_discount", 100.0))
            max_freq = int(raw_merchant.get("max_campaign_frequency", 3))
            autonomy = str(raw_merchant.get("autonomy_level", "APPROVAL_REQUIRED"))
        else:
            min_margin = 0.10
            daily_budget = 12000.0
            max_discount = 100.0
            max_freq = 3
            autonomy = "APPROVAL_REQUIRED"

        merchant_rules = MerchantRules(
            minimum_margin=min_margin,
            daily_budget=daily_budget,
            max_discount=max_discount,
            max_campaign_frequency=max_freq,
            autonomy_mode=autonomy,
        )

        # 2. Derive eligible customer count dynamically from CustomerRepository
        seg_summary = CustomerRepository.get_customers_summary(mid)
        eligible_count = int(seg_summary.get("target_campaign_customers", 486))

        # 3. Formulate planning limits
        planning_limits = PlanningLimits(
            max_discount_inr=max_discount,
            max_daily_budget_inr=daily_budget,
            max_eligible_customers=eligible_count,
            min_margin=min_margin,
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        return PlanningContext(
            investigation_id=inv_id,
            signal_id=sig_id,
            merchant_id=mid,
            merchant_rules=merchant_rules,
            eligible_customer_count=eligible_count,
            eligible_segments=["repeat_customer", "regular"],
            investigation_findings=findings,
            investigation_summary=summary,
            available_evidence_ids=evidence_ids or ["E1", "E2", "E3", "E4", "E5"],
            allowed_action_types=[
                "EVENING_REENGAGEMENT_CAMPAIGN",
                "OFFER_CAMPAIGN",
                "CUSTOMER_LOYALTY",
            ],
            planning_limits=planning_limits,
            created_at=now_iso,
        )
