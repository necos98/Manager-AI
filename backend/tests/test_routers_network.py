import re

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_network_info_returns_local_ip(client):
    response = await client.get("/api/network-info")
    assert response.status_code == 200
    data = response.json()
    assert "local_ip" in data
    assert IP_RE.match(data["local_ip"]), f"Expected IP, got: {data['local_ip']!r}"
