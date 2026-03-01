"""Config controller — handles GET /config"""

from fastapi import APIRouter

import services.iqb_service as iqb_service

router = APIRouter(tags=["Config"])


@router.get("/config", summary="Get IQB configuration")
def get_config() -> dict:
    """
    Return the full IQB configuration — all use cases, their network
    requirements, threshold values, and dataset weights.
    """
    return iqb_service.get_config()
