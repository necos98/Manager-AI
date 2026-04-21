import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.models.project import Project
from app.services import file_service


@pytest.mark.asyncio
async def test_upload_extract_read_search(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(file_service, "BASE_DIR", str(tmp_path))

    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("files", ("spec.md", b"# Spec\n\nKey phrase: UNIQUEKEYWORD appears here.", "text/markdown"))]
        r = await client.post("/api/projects/p1/files", files=files)
        assert r.status_code == 201, r.text
        body = r.json()
        assert len(body) == 1
        file_id = body[0]["id"]
        assert body[0]["extraction_status"] == "ok"

        r = await client.get(f"/api/projects/p1/files/{file_id}/content")
        assert r.status_code == 200
        data = r.json()
        assert "UNIQUEKEYWORD" in data["content"]
        assert data["status"] == "ok"
        assert data["truncated"] is False

        r = await client.get("/api/projects/p1/files/search", params={"q": "UNIQUEKEYWORD"})
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["file"]["id"] == file_id
        assert "UNIQUEKEYWORD" in results[0]["snippet"] or results[0]["snippet"] != ""

        r = await client.post(f"/api/projects/p1/files/{file_id}/reextract")
        assert r.status_code == 200
        assert r.json()["extraction_status"] == "ok"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_pagination(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(file_service, "BASE_DIR", str(tmp_path))

    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    big = "abcdefghij" * 100  # 1000 chars
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("files", ("big.txt", big.encode(), "text/plain"))]
        r = await client.post("/api/projects/p1/files", files=files)
        assert r.status_code == 201
        fid = r.json()[0]["id"]

        r = await client.get(f"/api/projects/p1/files/{fid}/content", params={"offset": 0, "max_chars": 100})
        data = r.json()
        assert len(data["content"]) == 100
        assert data["total_chars"] == 1000
        assert data["truncated"] is True

        r = await client.get(f"/api/projects/p1/files/{fid}/content", params={"offset": 950, "max_chars": 100})
        data = r.json()
        assert len(data["content"]) == 50
        assert data["truncated"] is False

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_image_skips_extraction(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(file_service, "BASE_DIR", str(tmp_path))

    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("files", ("photo.png", png_bytes, "image/png"))]
        r = await client.post("/api/projects/p1/files", files=files)
        assert r.status_code == 201, r.text
        body = r.json()
        assert len(body) == 1
        assert body[0]["file_type"] == "png"
        assert body[0]["mime_type"] == "image/png"
        assert body[0]["extraction_status"] == "skipped"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(file_service, "BASE_DIR", str(tmp_path))

    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    oversized = b"\x00" * (file_service.MAX_FILE_SIZE + 1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("files", ("big.png", oversized, "image/png"))]
        r = await client.post("/api/projects/p1/files", files=files)
        assert r.status_code == 400
        detail = r.json()["detail"].lower()
        assert "5" in detail or "size" in detail or "exceed" in detail or "mb" in detail

    app.dependency_overrides.clear()
