from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.llm.client import get_llm_client
from app.simulation.constants import DEFAULT_MERCHANT_PROFILE, SIMULATION_DISCLAIMER

router = APIRouter(tags=["System"])
settings = get_settings()


class SystemStatusResponse(BaseModel):
    service: str
    version: str
    environment: str
    simulation_mode: bool
    simulation_disclaimer: str
    llm_provider: str
    llm_is_active: bool
    guardrails_enforced: bool
    merchant_profile: Dict[str, Any]


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """Returns MITRA system status, active LLM provider, and digital-twin merchant context."""
    llm = get_llm_client()
    return SystemStatusResponse(
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        simulation_mode=settings.SIMULATION_MODE,
        simulation_disclaimer=SIMULATION_DISCLAIMER,
        llm_provider=llm.provider_name,
        llm_is_active=settings.is_llm_active,
        guardrails_enforced=True,
        merchant_profile=DEFAULT_MERCHANT_PROFILE,
    )
