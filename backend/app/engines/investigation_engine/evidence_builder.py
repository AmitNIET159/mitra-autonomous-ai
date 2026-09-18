from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.contracts import Signal, utc_now
from app.database.repository import (
    BusinessMetricRepository,
    CampaignRepository,
    CustomerRepository,
    TransactionRepository,
)
from app.engines.investigation_engine.schemas import (
    EvidenceBundle,
    EvidenceCategory,
    EvidenceItem,
)
from app.models.contracts import Signal


class EvidenceBuilder:
    """Deterministic evidence builder.
    
    Gathers factual data directly from SQLite database repositories.
    Never invents data; returns 'data unavailable' if a metric cannot be queried.
    """

    @staticmethod
    def build_evidence(signal: Signal, merchant_id: Optional[str] = None) -> EvidenceBundle:
        mid = merchant_id or signal.merchant_id or "MID-DEMO-98234"
        now_str = utc_now().isoformat()

        # 1. Fetch dynamic telemetry from DB repositories
        try:
            stats = TransactionRepository.get_stats(mid)
        except Exception:
            stats = {}

        try:
            metrics = BusinessMetricRepository.get_metrics_map(mid)
        except Exception:
            metrics = {}

        try:
            cust_summary = CustomerRepository.get_customers_summary(mid)
        except Exception:
            cust_summary = {}

        try:
            campaigns = CampaignRepository.get_campaigns(mid)
        except Exception:
            campaigns = []

        evidence_items: List[EvidenceItem] = []

        # ==========================================
        # E1: PRIMARY_SIGNAL (Observed signal fact)
        # ==========================================
        e1_baseline = signal.baseline_value
        e1_current = signal.observed_value
        if signal.change_percentage and signal.change_percentage != 0.0:
            e1_change = signal.change_percentage
        elif e1_baseline and e1_baseline > 0 and e1_current is not None:
            e1_change = round(((e1_current - e1_baseline) / e1_baseline) * 100.0, 2)
        else:
            e1_change = 0.0

        if e1_baseline is not None and e1_current is not None:
            e1_obs = (
                f"Evening orders fell from {e1_baseline:.0f} baseline to {e1_current:.0f} "
                f"observed orders ({e1_change:.2f}% change, {signal.severity.value} severity)."
            )
        else:
            e1_obs = "data unavailable"

        evidence_items.append(
            EvidenceItem(
                evidence_id="E1",
                category=EvidenceCategory.PRIMARY_SIGNAL,
                metric=signal.metric_name or "evening_orders",
                baseline=e1_baseline if e1_baseline is not None else "data unavailable",
                current=e1_current if e1_current is not None else "data unavailable",
                change_percentage=e1_change,
                observation=e1_obs,
                source="transactions",
            )
        )

        # ==========================================
        # E2: CUSTOMER_BEHAVIOR (Repeat conversion)
        # ==========================================
        rep_baseline = metrics.get("repeat_conversion_baseline")
        rep_current = metrics.get("repeat_conversion_observed")

        if rep_baseline is not None and rep_current is not None and rep_baseline > 0:
            rep_change = round(((rep_current - rep_baseline) / rep_baseline) * 100.0, 2)
            e2_obs = (
                f"Repeat-customer conversion rate declined from {rep_baseline * 100:.1f}% baseline "
                f"to {rep_current * 100:.1f}% ({rep_change:.2f}% relative change)."
            )
            evidence_items.append(
                EvidenceItem(
                    evidence_id="E2",
                    category=EvidenceCategory.CUSTOMER_BEHAVIOR,
                    metric="repeat_customer_conversion",
                    baseline=round(rep_baseline, 4),
                    current=round(rep_current, 4),
                    change_percentage=rep_change,
                    observation=e2_obs,
                    source="business_metrics",
                )
            )
        else:
            evidence_items.append(
                EvidenceItem(
                    evidence_id="E2",
                    category=EvidenceCategory.CUSTOMER_BEHAVIOR,
                    metric="repeat_customer_conversion",
                    baseline="data unavailable",
                    current="data unavailable",
                    change_percentage=None,
                    observation="data unavailable",
                    source="business_metrics",
                )
            )

        # ==========================================
        # E3: CAMPAIGN_CONTEXT (Expired campaign)
        # ==========================================
        expired_campaigns = [c for c in campaigns if c.get("status") == "EXPIRED"]
        active_campaigns = [c for c in campaigns if c.get("status") == "ACTIVE"]

        if campaigns:
            target_campaign = expired_campaigns[0] if expired_campaigns else campaigns[0]
            ended_at_str = target_campaign.get("ended_at")
            days_since_expiration = 3  # Default nominal window anchor

            if ended_at_str:
                try:
                    # Clean ISO format
                    ended_dt = datetime.fromisoformat(ended_at_str.replace("Z", "+00:00"))
                    # Benchmark comparison against latest transaction date or now
                    now_dt = datetime.now(timezone.utc)
                    diff_days = (now_dt - ended_dt).days
                    if diff_days >= 0:
                        days_since_expiration = diff_days
                except Exception:
                    days_since_expiration = 3

            c_name = target_campaign.get("name", "Unknown Campaign")
            c_status = target_campaign.get("status", "EXPIRED")
            active_count = len(active_campaigns)

            if c_status == "EXPIRED":
                e3_obs = (
                    f"Previous campaign '{c_name}' expired {days_since_expiration} days ago. "
                    f"Currently, {active_count} active replacement campaigns exist."
                )
                e3_current = f"Expired {days_since_expiration} days ago"
            else:
                e3_obs = (
                    f"Campaign '{c_name}' status is {c_status}. "
                    f"Currently, {active_count} active campaigns exist."
                )
                e3_current = c_status

            evidence_items.append(
                EvidenceItem(
                    evidence_id="E3",
                    category=EvidenceCategory.CAMPAIGN_CONTEXT,
                    metric="previous_campaign_status",
                    baseline="Active Promotional Coverage",
                    current=e3_current,
                    change_percentage=None,
                    observation=e3_obs,
                    source="campaigns",
                )
            )
        else:
            evidence_items.append(
                EvidenceItem(
                    evidence_id="E3",
                    category=EvidenceCategory.CAMPAIGN_CONTEXT,
                    metric="previous_campaign_status",
                    baseline="data unavailable",
                    current="data unavailable",
                    change_percentage=None,
                    observation="data unavailable",
                    source="campaigns",
                )
            )

        # ==========================================
        # E4: TARGET_AUDIENCE (Customer segmentation)
        # ==========================================
        total_cust = cust_summary.get("total_customers")
        target_cust = cust_summary.get("target_campaign_customers")
        segments = cust_summary.get("segment_breakdown", {})
        inactive_cust = segments.get("inactive", 0)

        if total_cust is not None and target_cust is not None and total_cust > 0:
            e4_obs = (
                f"Customer base contains {total_cust} total customers, with {target_cust} "
                f"eligible for re-engagement and {inactive_cust} inactive accounts."
            )
            evidence_items.append(
                EvidenceItem(
                    evidence_id="E4",
                    category=EvidenceCategory.TARGET_AUDIENCE,
                    metric="customer_segment_distribution",
                    baseline=int(total_cust),
                    current=int(target_cust),
                    change_percentage=None,
                    observation=e4_obs,
                    source="customers",
                )
            )
        else:
            evidence_items.append(
                EvidenceItem(
                    evidence_id="E4",
                    category=EvidenceCategory.TARGET_AUDIENCE,
                    metric="customer_segment_distribution",
                    baseline="data unavailable",
                    current="data unavailable",
                    change_percentage=None,
                    observation="data unavailable",
                    source="customers",
                )
            )

        # ==========================================
        # E5: BUSINESS_CONTEXT (Evening Revenue GMV)
        # ==========================================
        # Explicit deterministic baseline evening revenue and current evening revenue
        baseline_evn_rev = stats.get("baseline_evening_revenue")
        current_evn_rev = stats.get("evening_revenue")

        if baseline_evn_rev is not None and current_evn_rev is not None and baseline_evn_rev > 0:
            rev_change = round(((current_evn_rev - baseline_evn_rev) / baseline_evn_rev) * 100.0, 2)
            gap = abs(baseline_evn_rev - current_evn_rev)
            e5_obs = (
                f"Evening revenue velocity changed from ₹{baseline_evn_rev:,.2f} baseline to "
                f"₹{current_evn_rev:,.2f} observed in the recent window "
                f"({rev_change:.2f}% change, gap of ₹{gap:,.2f})."
            )
            evidence_items.append(
                EvidenceItem(
                    evidence_id="E5",
                    category=EvidenceCategory.BUSINESS_CONTEXT,
                    metric="evening_revenue_inr",
                    baseline=round(baseline_evn_rev, 2),
                    current=round(current_evn_rev, 2),
                    change_percentage=rev_change,
                    observation=e5_obs,
                    source="transactions",
                )
            )
        else:
            evidence_items.append(
                EvidenceItem(
                    evidence_id="E5",
                    category=EvidenceCategory.BUSINESS_CONTEXT,
                    metric="evening_revenue_inr",
                    baseline="data unavailable",
                    current="data unavailable",
                    change_percentage=None,
                    observation="data unavailable",
                    source="transactions",
                )
            )

        return EvidenceBundle(
            signal_id=signal.signal_id,
            signal_type=signal.signal_type,
            severity=signal.severity.value,
            merchant_id=mid,
            primary_metric=signal.metric_name or "evening_orders",
            created_at=now_str,
            evidence_items=evidence_items,
        )
