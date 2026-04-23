from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    platform: str
    wsl_available: bool
    distros: list[str]
    default_distro: str | None
    host_ip_for_wsl: str | None
