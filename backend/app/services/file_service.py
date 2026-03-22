import os
import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_file import ProjectFile

ALLOWED_EXTENSIONS = {"txt", "doc", "docx", "pdf", "xls", "xlsx"}

MIME_MAP = {
    "txt": "text/plain",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "project_resources")


def _get_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lstrip(".").lower()


class FileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upload_files(self, project_id: str, files: list[UploadFile]) -> list[ProjectFile]:
        project_dir = os.path.join(BASE_DIR, project_id)
        os.makedirs(project_dir, exist_ok=True)

        results = []
        for file in files:
            ext = _get_extension(file.filename)
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f"File type '.{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

            file_id = str(uuid.uuid4())
            stored_name = f"{file_id}.{ext}"
            file_path = os.path.join(project_dir, stored_name)

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            mime_type = MIME_MAP.get(ext, "application/octet-stream")

            record = ProjectFile(
                id=file_id,
                project_id=project_id,
                original_name=file.filename,
                stored_name=stored_name,
                file_type=ext,
                file_size=len(content),
                mime_type=mime_type,
            )
            self.session.add(record)
            results.append(record)

        await self.session.flush()
        return results

    async def list_by_project(self, project_id: str) -> list[ProjectFile]:
        result = await self.session.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .order_by(ProjectFile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, project_id: str, file_id: str) -> ProjectFile | None:
        result = await self.session.execute(
            select(ProjectFile)
            .where(ProjectFile.id == file_id, ProjectFile.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, project_id: str, file_id: str) -> bool:
        record = await self.get_by_id(project_id, file_id)
        if record is None:
            return False

        file_path = os.path.join(BASE_DIR, project_id, record.stored_name)
        if os.path.exists(file_path):
            os.remove(file_path)

        await self.session.delete(record)
        await self.session.flush()
        return True

    def get_file_path(self, project_id: str, stored_name: str) -> str:
        return os.path.join(BASE_DIR, project_id, stored_name)
