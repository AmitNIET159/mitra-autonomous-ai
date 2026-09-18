from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """MITRA Health Check endpoint.
    
    Expected response per Project Contract:
    {
      "status": "ok",
      "service": "MITRA"
    }
    """
    return HealthResponse(status="ok", service="MITRA")
