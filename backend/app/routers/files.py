from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_file import ProjectFileResponse
from app.services.file_service import ALLOWED_EXTENSIONS, FileService
from app.services.project_service import ProjectService

formats_router = APIRouter(prefix="/api/files", tags=["files"])
router = APIRouter(prefix="/api/projects/{project_id}/files", tags=["files"])


@formats_router.get("/allowed-formats")
async def get_allowed_formats():
    extensions = sorted(ALLOWED_EXTENSIONS)
    return {
        "accept": ",".join(f".{ext}" for ext in extensions),
        "extensions": extensions,
        "label": ", ".join(ext.upper() for ext in extensions),
    }


async def _check_project(project_id: str, db: AsyncSession):
    project = await ProjectService(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=list[ProjectFileResponse], status_code=201)
async def upload_files(project_id: str, files: list[UploadFile], db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    try:
        records = await service.upload_files(project_id, files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return [ProjectFileResponse.from_model(r) for r in records]


@router.get("", response_model=list[ProjectFileResponse])
async def list_files(project_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    records = await service.list_by_project(project_id)
    return [ProjectFileResponse.from_model(r) for r in records]


@router.get("/{file_id}/download")
async def download_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    record = await service.get_by_id(project_id, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = await service.get_file_path(project_id, record.stored_name)
    return FileResponse(path=file_path, filename=record.original_name, media_type=record.mime_type)


@router.delete("/{file_id}", status_code=204)
async def delete_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    deleted = await service.delete(project_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()


@router.get("/{file_id}/preview")
async def preview_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    record = await service.get_by_id(project_id, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = await service.get_file_path(project_id, record.stored_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path=file_path, media_type=record.mime_type, filename=record.original_name)


@router.get("/{file_id}/content")
async def get_file_content(
    project_id: str,
    file_id: str,
    offset: int = 0,
    max_chars: int = 50000,
    db: AsyncSession = Depends(get_db),
):
    await _check_project(project_id, db)
    service = FileService(db)
    record = await service.get_by_id(project_id, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    text_full = record.extracted_text or ""
    total = len(text_full)
    offset = max(0, offset)
    max_chars = max(1, min(max_chars, 500_000))
    chunk = text_full[offset : offset + max_chars]
    return {
        "id": record.id,
        "name": record.original_name,
        "type": record.file_type,
        "status": record.extraction_status,
        "error": record.extraction_error,
        "offset": offset,
        "total_chars": total,
        "truncated": offset + max_chars < total,
        "content": chunk,
    }


@router.post("/{file_id}/reextract", response_model=ProjectFileResponse)
async def reextract_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    record = await service.reextract(project_id, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
    return ProjectFileResponse.from_model(record)


@router.get("/search")
async def search_files(project_id: str, q: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    hits = await service.search(project_id, q, limit=limit)
    return {
        "results": [
            {
                "file": ProjectFileResponse.from_model(h["file"]).model_dump(mode="json"),
                "snippet": h["snippet"],
                "rank": h["rank"],
            }
            for h in hits
        ]
    }
