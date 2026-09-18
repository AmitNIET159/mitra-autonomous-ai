from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.database.repository import MerchantRepository, TransactionRepository
from app.database.seed import seed_digital_twin
from app.simulation.constants import SIMULATION_DISCLAIMER

router = APIRouter(prefix="/simulation", tags=["Digital Twin Simulation"])
settings = get_settings()


class SimulationResetResponse(BaseModel):
    status: str
    message: str
    simulated: bool = True
    seed_summary: Dict[str, Any]


class SimulationStatusResponse(BaseModel):
    simulation_mode: bool
    service: str
    environment: str
    simulation_disclaimer: str
    active_merchant_id: str
    database_seeded: bool
    total_orders: int
    total_revenue_inr: float


@router.post("/reset", response_model=SimulationResetResponse)
async def reset_simulation() -> SimulationResetResponse:
    """Resets the digital-twin simulation and reseeds deterministic demo data while preserving audit history."""
    from app.api.demo import reset_demo_endpoint
    res = reset_demo_endpoint()
    return SimulationResetResponse(
        status="ok",
        message="Digital twin simulation environment successfully reset and reseeded. Audit history preserved.",
        simulated=True,
        seed_summary=res.seed_summary,
    )


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status() -> SimulationStatusResponse:
    """Returns the current state and telemetry of the digital twin simulation."""
    merchant = MerchantRepository.get_merchant("MID-DEMO-98234")
    stats = TransactionRepository.get_stats("MID-DEMO-98234") if merchant else {"total_orders": 0, "total_revenue": 0.0}

    return SimulationStatusResponse(
        simulation_mode=settings.SIMULATION_MODE,
        service=settings.APP_NAME,
        environment=settings.APP_ENV,
        simulation_disclaimer=SIMULATION_DISCLAIMER,
        active_merchant_id="MID-DEMO-98234",
        database_seeded=bool(merchant),
        total_orders=stats.get("total_orders", 0),
        total_revenue_inr=stats.get("total_revenue", 0.0),
    )
