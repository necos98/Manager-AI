import json
import os

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.project_credential import ProjectCredential


class CredentialService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _get_fernet() -> Fernet:
        key = os.environ.get("MANAGER_AI_SECRET_KEY")
        if not key:
            raise ValueError(
                "MANAGER_AI_SECRET_KEY is not set. "
                "The server must set this env var at startup "
                "(it is persisted to data/secret.key on first run)."
            )
        return Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt_fields(self, fields: dict) -> str:
        f = self._get_fernet()
        return f.encrypt(json.dumps(fields).encode()).decode()

    def decrypt_fields(self, encrypted: str) -> dict:
        f = self._get_fernet()
        return json.loads(f.decrypt(encrypted.encode()).decode())

    async def list_roles(self, project_id: str) -> list[str]:
        result = await self.session.execute(
            select(ProjectCredential.role)
            .where(ProjectCredential.project_id == project_id)
            .order_by(ProjectCredential.role)
        )
        return list(result.scalars().all())

    async def get(self, project_id: str, role: str) -> dict:
        result = await self.session.execute(
            select(ProjectCredential)
            .where(ProjectCredential.project_id == project_id)
            .where(ProjectCredential.role == role)
        )
        cred = result.scalar_one_or_none()
        if cred is None:
            raise NotFoundError(f"Credential not found for role '{role}'")
        return {
            "id": cred.id,
            "project_id": cred.project_id,
            "role": cred.role,
            "url": cred.url,
            "fields": self.decrypt_fields(cred.encrypted_fields),
        }

    async def upsert(self, project_id: str, role: str, url: str, fields: dict) -> ProjectCredential:
        result = await self.session.execute(
            select(ProjectCredential)
            .where(ProjectCredential.project_id == project_id)
            .where(ProjectCredential.role == role)
        )
        cred = result.scalar_one_or_none()
        encrypted = self.encrypt_fields(fields)
        if cred:
            cred.url = url
            cred.encrypted_fields = encrypted
        else:
            cred = ProjectCredential(
                project_id=project_id, role=role, url=url, encrypted_fields=encrypted
            )
            self.session.add(cred)
        await self.session.flush()
        return cred

    async def delete(self, project_id: str, role: str) -> None:
        result = await self.session.execute(
            select(ProjectCredential)
            .where(ProjectCredential.project_id == project_id)
            .where(ProjectCredential.role == role)
        )
        cred = result.scalar_one_or_none()
        if cred is None:
            raise NotFoundError(f"Credential not found for role '{role}'")
        await self.session.delete(cred)
        await self.session.flush()
