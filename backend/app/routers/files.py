import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.rag import get_rag_service
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
    # Trigger async embedding for each uploaded file
    rag = get_rag_service()
    for record in records:
        file_path = service.get_file_path(project_id, record.stored_name)
        asyncio.create_task(rag.embed_file(
            project_id=project_id,
            source_id=record.id,
            file_path=file_path,
            mime_type=record.mime_type,
            original_name=record.original_name,
        ))
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

    file_path = service.get_file_path(project_id, record.stored_name)
    return FileResponse(
        path=file_path,
        filename=record.original_name,
        media_type=record.mime_type,
    )


@router.delete("/{file_id}", status_code=204)
async def delete_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    deleted = await service.delete(project_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
    # Remove embeddings for the deleted file
    rag = get_rag_service()
    asyncio.create_task(rag.delete_source(file_id))
