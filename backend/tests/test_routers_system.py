import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_system_info_shape(monkeypatch):
    from app.routers import system as sysrouter

    monkeypatch.setattr(sysrouter, "wsl_available", lambda: True)
    monkeypatch.setattr(sysrouter, "list_wsl_distros", lambda: ["Ubuntu-22.04"])
    monkeypatch.setattr(sysrouter, "get_default_distro", lambda: "Ubuntu-22.04")
    monkeypatch.setattr(sysrouter, "get_host_ip_for_wsl", lambda: None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/system/info")
    assert r.status_code == 200
    body = r.json()
    assert body["wsl_available"] is True
    assert body["distros"] == ["Ubuntu-22.04"]
    assert body["default_distro"] == "Ubuntu-22.04"
    assert body["host_ip_for_wsl"] is None
    assert "platform" in body
