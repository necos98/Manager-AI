from __future__ import annotations

import platform

from fastapi import APIRouter

from app.schemas.system import SystemInfoResponse
from app.services.wsl_support import (
    get_default_distro,
    get_host_ip_for_wsl,
    list_wsl_distros,
    wsl_available,
)

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
async def system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        platform=platform.system(),
        wsl_available=wsl_available(),
        distros=list_wsl_distros(),
        default_distro=get_default_distro(),
        host_ip_for_wsl=get_host_ip_for_wsl(),
    )
