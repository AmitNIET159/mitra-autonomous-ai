from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database.repository import (
    BusinessMetricRepository,
    CampaignRepository,
    CustomerRepository,
    MerchantRepository,
    TransactionRepository,
)
from app.simulation.constants import SIMULATION_DISCLAIMER

router = APIRouter(prefix="/merchant", tags=["Merchant Digital Twin"])


class MerchantResponse(BaseModel):
    id: str
    name: str
    category: str
    location: str
    minimum_margin: float
    daily_budget: float
    max_discount: float
    max_campaign_frequency: int
    autonomy_level: str
    simulated: bool = True
    simulation_disclaimer: str = SIMULATION_DISCLAIMER


class MetricItem(BaseModel):
    name: str
    value: float
    unit: str
    description: str


class MerchantMetricsResponse(BaseModel):
    merchant_id: str
    total_revenue_inr: float
    total_orders: int
    avg_basket_size_inr: float
    evening_orders_current: int
    evening_orders_baseline: int
    evening_orders_variance_pct: float
    repeat_conversion_current: float
    repeat_conversion_baseline: float
    target_campaign_customers: int
    simulated: bool = True
    metrics_breakdown: List[MetricItem] = Field(default_factory=list)


class CustomerSegmentSummary(BaseModel):
    merchant_id: str
    total_customers: int
    segment_breakdown: Dict[str, int]
    target_campaign_customers: int
    simulated: bool = True


class CampaignItem(BaseModel):
    id: str
    name: str
    campaign_type: str
    discount_amount: float
    discount_percent: float
    budget: float
    target_customer_count: int
    started_at: str
    ended_at: Optional[str] = None
    status: str
    simulated: bool = True


@router.get("", response_model=MerchantResponse)
async def get_merchant(merchant_id: str = "MID-DEMO-98234") -> MerchantResponse:
    """Returns the primary demo merchant digital-twin profile and guardrail limits."""
    merchant = MerchantRepository.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail=f"Merchant {merchant_id} not found in digital twin.")
    return MerchantResponse(
        id=merchant["id"],
        name=merchant["name"],
        category=merchant["category"],
        location=merchant["location"],
        minimum_margin=merchant["minimum_margin"],
        daily_budget=merchant["daily_budget"],
        max_discount=merchant["max_discount"],
        max_campaign_frequency=merchant["max_campaign_frequency"],
        autonomy_level=merchant["autonomy_level"],
        simulated=True,
    )


@router.get("/metrics", response_model=MerchantMetricsResponse)
async def get_merchant_metrics(merchant_id: str = "MID-DEMO-98234") -> MerchantMetricsResponse:
    """Returns derived business health and anomaly metrics for the merchant."""
    stats = TransactionRepository.get_stats(merchant_id)
    metrics_map = BusinessMetricRepository.get_metrics_map(merchant_id)
    cust_summary = CustomerRepository.get_customers_summary(merchant_id)

    evn_baseline = int(metrics_map.get("evening_orders_baseline", 410))
    evn_current = int(stats.get("evening_orders", 291))
    variance_pct = round(((evn_current - evn_baseline) / evn_baseline) * 100.0, 2)

    breakdown = [
        MetricItem(name="Total Revenue (Window)", value=stats["total_revenue"], unit="INR", description="Aggregated digital twin revenue"),
        MetricItem(name="Total Orders (Window)", value=stats["total_orders"], unit="Orders", description="Total orders placed in evaluation window"),
        MetricItem(name="Evening Orders Current", value=evn_current, unit="Orders", description="Orders placed 5:00 PM - 8:59 PM in recent window"),
        MetricItem(name="Evening Orders Baseline", value=evn_baseline, unit="Orders", description="Historical average evening orders"),
        MetricItem(name="Repeat Customer Conversion", value=round(metrics_map.get("repeat_conversion_observed", 0.148) * 100, 1), unit="Percent", description="Current repeat-customer conversion rate"),
        MetricItem(name="Historical Repeat Conversion", value=round(metrics_map.get("repeat_conversion_baseline", 0.182) * 100, 1), unit="Percent", description="Historical repeat-customer conversion rate"),
    ]

    return MerchantMetricsResponse(
        merchant_id=merchant_id,
        total_revenue_inr=stats["total_revenue"],
        total_orders=stats["total_orders"],
        avg_basket_size_inr=stats["avg_basket_size"],
        evening_orders_current=evn_current,
        evening_orders_baseline=evn_baseline,
        evening_orders_variance_pct=variance_pct,
        repeat_conversion_current=metrics_map.get("repeat_conversion_observed", 0.148),
        repeat_conversion_baseline=metrics_map.get("repeat_conversion_baseline", 0.182),
        target_campaign_customers=cust_summary["target_campaign_customers"],
        simulated=True,
        metrics_breakdown=breakdown,
    )


@router.get("/customers/summary", response_model=CustomerSegmentSummary)
async def get_customers_summary(merchant_id: str = "MID-DEMO-98234") -> CustomerSegmentSummary:
    """Returns customer segmentation counts and derived campaign re-engagement target."""
    summary = CustomerRepository.get_customers_summary(merchant_id)
    return CustomerSegmentSummary(
        merchant_id=summary["merchant_id"],
        total_customers=summary["total_customers"],
        segment_breakdown=summary["segment_breakdown"],
        target_campaign_customers=summary["target_campaign_customers"],
        simulated=True,
    )


@router.get("/campaigns", response_model=List[CampaignItem])
async def get_campaigns(merchant_id: str = "MID-DEMO-98234") -> List[CampaignItem]:
    """Returns marketing campaign history including expired baseline campaigns."""
    campaigns = CampaignRepository.get_campaigns(merchant_id)
    return [
        CampaignItem(
            id=c["id"],
            name=c["name"],
            campaign_type=c["campaign_type"],
            discount_amount=c["discount_amount"],
            discount_percent=c["discount_percent"],
            budget=c["budget"],
            target_customer_count=c["target_customer_count"],
            started_at=c["started_at"],
            ended_at=c.get("ended_at"),
            status=c["status"],
            simulated=True,
        )
        for c in campaigns
    ]
