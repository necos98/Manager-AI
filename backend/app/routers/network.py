import socket

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["network"])


def _get_local_ip() -> str:
    """Return the LAN IP of this machine using a UDP socket trick."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


@router.get("/network-info")
async def get_network_info():
    return {"local_ip": _get_local_ip()}
