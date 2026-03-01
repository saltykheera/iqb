"""Health controller — handles GET /"""

from fastapi import APIRouter

from models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/", response_model=HealthResponse, summary="Health check")
def health() -> HealthResponse:
    """Returns a simple status message to confirm the API is running."""
    return HealthResponse(status="ok", service="M-Lab IQB API")
