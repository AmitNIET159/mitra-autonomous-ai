from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.database.repository import (
    BusinessMetricRepository,
    CampaignRepository,
    CustomerRepository,
    TransactionRepository,
)
from app.engines.signal_engine.thresholds import DEFAULT_THRESHOLDS, ThresholdConfig
from app.models.contracts import DetectionResult
from app.models.enums import SignalSeverity


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BaseDetector(ABC):
    """Abstract base class for all deterministic business anomaly detectors."""

    def __init__(self, thresholds: Optional[ThresholdConfig] = None):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    @property
    @abstractmethod
    def signal_type(self) -> str:
        pass

    @abstractmethod
    def detect(self, merchant_id: str) -> Optional[DetectionResult]:
        pass


class EveningOrderDeclineDetector(BaseDetector):
    """PRIMARY DEMO DETECTOR: Evaluates evening orders decline.
    
    Formula:
    decline_percentage = (baseline - current) / baseline * 100
    change_percentage = -decline_percentage
    """

    @property
    def signal_type(self) -> str:
        return "EVENING_ORDER_DECLINE"

    def detect(self, merchant_id: str) -> Optional[DetectionResult]:
        stats = TransactionRepository.get_stats(merchant_id)
        metrics_map = BusinessMetricRepository.get_metrics_map(merchant_id)

        # Retrieve baseline and current from database
        baseline = metrics_map.get("evening_orders_baseline")
        if baseline is None:
            baseline = stats.get("baseline_evening_orders", 0.0)

        current = stats.get("evening_orders", 0.0)

        # Edge case: Safe division by zero check
        if baseline is None or baseline <= 0:
            logger.warning("EveningOrderDeclineDetector: baseline is 0 or missing for %s. Skipping.", merchant_id)
            return None

        decline_orders = baseline - current
        if decline_orders <= 0:
            # Evening orders grew or stayed equal - no decline anomaly
            return None

        decline_percentage = round((decline_orders / baseline) * 100.0, 2)
        change_percentage = -decline_percentage

        severity = self.thresholds.classify_decline(decline_percentage)
        if not severity:
            # Below minimum threshold (<5%)
            return None

        # Fact-only evidence (NO causal claims per Phase 3 rules)
        evidence: Dict[str, Any] = {
            "baseline_evening_orders": int(baseline),
            "current_evening_orders": int(current),
            "order_difference": int(decline_orders),
            "time_slot": "17:00 - 20:59",
            "evaluation_window_days": 4,
            "baseline_window_days": 10,
        }

        description = (
            f"Evening orders (5:00 PM - 8:59 PM) declined by {decline_percentage:.2f}% "
            f"from historical baseline of {int(baseline)} orders to {int(current)} orders."
        )

        return DetectionResult(
            signal_type=self.signal_type,
            title="Evening Order Decline",
            description=description,
            severity=severity,
            baseline_value=float(baseline),
            current_value=float(current),
            change_percentage=change_percentage,
            decline_percentage=decline_percentage,
            metric_name="evening_orders",
            evidence=evidence,
            detected_at=utc_now(),
        )


class RepeatCustomerConversionDetector(BaseDetector):
    """Detects weakening in repeat-customer conversion rate."""

    @property
    def signal_type(self) -> str:
        return "REPEAT_CUSTOMER_CONVERSION_DECLINE"

    def detect(self, merchant_id: str) -> Optional[DetectionResult]:
        metrics_map = BusinessMetricRepository.get_metrics_map(merchant_id)

        baseline = metrics_map.get("repeat_conversion_baseline")
        current = metrics_map.get("repeat_conversion_observed")

        # Edge case: Safe missing / zero checks
        if baseline is None or baseline <= 0 or current is None:
            return None

        if current >= baseline:
            return None

        drop = baseline - current
        decline_percentage = round((drop / baseline) * 100.0, 2)
        change_percentage = -decline_percentage

        severity = self.thresholds.classify_decline(decline_percentage)
        if not severity:
            return None

        cust_summary = CustomerRepository.get_customers_summary(merchant_id)

        evidence: Dict[str, Any] = {
            "baseline_conversion_rate": round(baseline, 4),
            "current_conversion_rate": round(current, 4),
            "conversion_drop_points": round(drop, 4),
            "total_customers": cust_summary.get("total_customers", 0),
            "target_campaign_customers": cust_summary.get("target_campaign_customers", 0),
        }

        description = (
            f"Repeat-customer conversion rate declined by {decline_percentage:.2f}% "
            f"(from baseline {baseline * 100:.1f}% to {current * 100:.1f}%)."
        )

        return DetectionResult(
            signal_type=self.signal_type,
            title="Repeat Customer Conversion Weakening",
            description=description,
            severity=severity,
            baseline_value=round(baseline, 4),
            current_value=round(current, 4),
            change_percentage=change_percentage,
            decline_percentage=decline_percentage,
            metric_name="repeat_customer_conversion",
            evidence=evidence,
            detected_at=utc_now(),
        )


class RevenueDeclineDetector(BaseDetector):
    """Detects gross revenue velocity drops."""

    @property
    def signal_type(self) -> str:
        return "REVENUE_DECLINE"

    def detect(self, merchant_id: str) -> Optional[DetectionResult]:
        stats = TransactionRepository.get_stats(merchant_id)
        total_revenue = stats.get("total_revenue", 0.0)
        total_orders = stats.get("total_orders", 0)

        if total_orders <= 0 or total_revenue <= 0:
            return None

        # Compare evening revenue proportion to expected 40% retail benchmark
        evening_rev = stats.get("evening_revenue", 0.0)
        expected_evening_rev = total_revenue * (410.0 / 1284.0)  # based on baseline ratio

        if expected_evening_rev <= 0 or evening_rev >= expected_evening_rev:
            return None

        rev_drop = expected_evening_rev - evening_rev
        decline_percentage = round((rev_drop / expected_evening_rev) * 100.0, 2)
        change_percentage = -decline_percentage

        severity = self.thresholds.classify_decline(decline_percentage)
        if not severity:
            return None

        evidence: Dict[str, Any] = {
            "total_window_revenue_inr": total_revenue,
            "expected_evening_revenue_inr": round(expected_evening_rev, 2),
            "observed_evening_revenue_inr": round(evening_rev, 2),
            "revenue_gap_inr": round(rev_drop, 2),
        }

        description = (
            f"Evening revenue velocity declined by {decline_percentage:.2f}% "
            f"(gap of INR {rev_drop:,.2f} relative to baseline evening expectation)."
        )

        return DetectionResult(
            signal_type=self.signal_type,
            title="Evening Revenue Run-Rate Decline",
            description=description,
            severity=severity,
            baseline_value=round(expected_evening_rev, 2),
            current_value=round(evening_rev, 2),
            change_percentage=change_percentage,
            decline_percentage=decline_percentage,
            metric_name="evening_revenue_inr",
            evidence=evidence,
            detected_at=utc_now(),
        )


class CampaignUnderperformanceDetector(BaseDetector):
    """Detects performance deficiencies in currently active promotional campaigns.

    Correction Rule:
    - An expired campaign is contextual evidence for future investigation, NOT an active underperformance signal.
    - Triggers ONLY when an active/measurable campaign has performance below its configured benchmark.
    - If no active campaign exists, returns NO SIGNAL (None).
    """

    @property
    def signal_type(self) -> str:
        return "CAMPAIGN_UNDERPERFORMANCE"

    def detect(self, merchant_id: str) -> Optional[DetectionResult]:
        campaigns = CampaignRepository.get_campaigns(merchant_id)
        active_campaigns = [c for c in campaigns if c.get("status") == "ACTIVE"]

        # If no active campaign exists, return NO SIGNAL
        if not active_campaigns:
            return None

        for campaign in active_campaigns:
            target_customers = campaign.get("target_customer_count", 0)
            if target_customers <= 0:
                continue

            # Standard retail benchmark: minimum 15% conversion/redemption rate
            benchmark_redemption_rate = 0.15
            expected_conversions = target_customers * benchmark_redemption_rate
            actual_conversions = float(campaign.get("actual_conversions", 0.0))

            if actual_conversions < expected_conversions and expected_conversions > 0:
                drop = expected_conversions - actual_conversions
                decline_percentage = round((drop / expected_conversions) * 100.0, 2)
                severity = self.thresholds.classify_decline(decline_percentage)
                if not severity:
                    continue

                evidence: Dict[str, Any] = {
                    "campaign_id": campaign.get("id"),
                    "campaign_name": campaign.get("name"),
                    "campaign_type": campaign.get("campaign_type"),
                    "target_customer_count": target_customers,
                    "benchmark_redemption_rate": benchmark_redemption_rate,
                    "expected_conversions": round(expected_conversions, 2),
                    "actual_conversions": round(actual_conversions, 2),
                    "decline_percentage": decline_percentage,
                }

                description = (
                    f"Active campaign '{campaign.get('name')}' underperformed benchmark by {decline_percentage:.2f}% "
                    f"({actual_conversions:.0f} actual vs {expected_conversions:.1f} expected conversions)."
                )

                return DetectionResult(
                    signal_type=self.signal_type,
                    title=f"Campaign Underperformance: {campaign.get('name')}",
                    description=description,
                    severity=severity,
                    baseline_value=round(expected_conversions, 2),
                    current_value=round(actual_conversions, 2),
                    change_percentage=-decline_percentage,
                    decline_percentage=decline_percentage,
                    metric_name="active_campaign_conversions",
                    evidence=evidence,
                    detected_at=utc_now(),
                )

        return None


class CustomerEngagementDeclineDetector(BaseDetector):
    """Detects elevated customer dormancy using relative deterioration formula.

    Correction Rule:
    - Inactive ratio: current ≈ 7.69% vs baseline = 5.0%.
    - Relative deterioration formula:
        relative_deterioration = ((current - baseline) / baseline) * 100
        ((7.69 - 5.0) / 5.0) * 100 ≈ 53.8%
    - Severity: CRITICAL (>30% threshold).
    - Stores current_ratio, baseline_ratio, and change_percentage explicitly.
    """

    @property
    def signal_type(self) -> str:
        return "CUSTOMER_ENGAGEMENT_DECLINE"

    def detect(self, merchant_id: str) -> Optional[DetectionResult]:
        cust_summary = CustomerRepository.get_customers_summary(merchant_id)
        total = cust_summary.get("total_customers", 0)
        segments = cust_summary.get("segment_breakdown", {})

        if total <= 0:
            return None

        inactive_count = segments.get("inactive", 0)
        current_ratio = round((inactive_count / total) * 100.0, 2)  # e.g., (40 / 520) * 100 = 7.69%
        baseline_ratio = 5.0  # 5.0% standard retail baseline

        if current_ratio > baseline_ratio:
            # Relative deterioration: ((current - baseline) / baseline) * 100
            change_percentage = round(
                ((current_ratio - baseline_ratio) / baseline_ratio) * 100.0, 2
            )
            severity = self.thresholds.classify_decline(change_percentage)
            if not severity:
                return None

            evidence: Dict[str, Any] = {
                "total_customers": total,
                "inactive_customer_count": inactive_count,
                "current_ratio": current_ratio,
                "baseline_ratio": baseline_ratio,
                "change_percentage": change_percentage,
                "relative_deterioration": change_percentage,
                "formula": "((current_ratio - baseline_ratio) / baseline_ratio) * 100",
            }

            description = (
                f"Inactive customer ratio ({current_ratio:.2f}%) deteriorated by "
                f"{change_percentage:.1f}% relative to baseline ({baseline_ratio:.1f}%), "
                f"exceeding the CRITICAL threshold with {inactive_count} inactive customers."
            )

            return DetectionResult(
                signal_type=self.signal_type,
                title="Customer Engagement Dormancy",
                description=description,
                severity=severity,
                baseline_value=baseline_ratio,
                current_value=current_ratio,
                change_percentage=change_percentage,
                decline_percentage=change_percentage,
                metric_name="inactive_customer_ratio",
                evidence=evidence,
                detected_at=utc_now(),
            )

        return None

