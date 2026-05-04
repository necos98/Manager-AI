from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.credential import CredentialResponse, CredentialUpsert
from app.services.credential_service import CredentialService

router = APIRouter(prefix="/api/projects/{project_id}/credentials", tags=["credentials"])


@router.get("", response_model=list[str])
async def list_credentials(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = CredentialService(db)
    return await svc.list_roles(project_id)


@router.get("/{role}", response_model=CredentialResponse)
async def get_credential(project_id: str, role: str, db: AsyncSession = Depends(get_db)):
    svc = CredentialService(db)
    return await svc.get(project_id, role)


@router.post("", response_model=CredentialResponse, status_code=201)
async def upsert_credential(project_id: str, data: CredentialUpsert, db: AsyncSession = Depends(get_db)):
    svc = CredentialService(db)
    cred = await svc.upsert(project_id, data.role, data.url, data.fields)
    await db.commit()
    decoded = svc.decrypt_fields(cred.encrypted_fields)
    return CredentialResponse(
        id=cred.id,
        project_id=cred.project_id,
        role=cred.role,
        url=cred.url,
        fields=decoded,
        created_at=str(cred.created_at) if cred.created_at else None,
        updated_at=str(cred.updated_at) if cred.updated_at else None,
    )


@router.delete("/{role}", status_code=204)
async def delete_credential(project_id: str, role: str, db: AsyncSession = Depends(get_db)):
    svc = CredentialService(db)
    await svc.delete(project_id, role)
    await db.commit()
