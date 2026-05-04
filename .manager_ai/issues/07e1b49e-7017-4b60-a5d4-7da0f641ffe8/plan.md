# Implementation Plan: Integrate Playwright for End-to-End Testing

## Architecture Overview

Eight implementation tasks, ordered by dependency. Each follows existing codebase patterns: SQLAlchemy async models → services → schemas → routers → MCP tools → frontend → migrations.

**Files map:**

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/models/project_credential.py` | Create | SQLAlchemy model for `project_credentials` table |
| `backend/app/models/project.py` | Modify | Add `url` column to Project |
| `backend/app/models/__init__.py` | Modify | Export `ProjectCredential` |
| `backend/app/services/credential_service.py` | Create | Fernet-encrypted CRUD for credentials |
| `backend/app/schemas/credential.py` | Create | Pydantic request/response schemas |
| `backend/app/routers/credentials.py` | Create | REST endpoints for credential management |
| `backend/app/mcp/server.py` | Modify | Add 5 new MCP tools |
| `backend/app/mcp/default_settings.json` | Modify | Add tool descriptions |
| `backend/app/main.py` | Modify | Register new router |
| `backend/app/schemas/project.py` | Modify | Add `url` field to ProjectResponse/ProjectUpdate/ProjectCreate |
| `backend/app/routers/projects.py` | Modify | Project update includes `url` |
| `frontend/src/shared/types/index.ts` | Modify | Add `url`, credential types |
| `frontend/src/features/projects/api.ts` | Modify | Add credential API functions |
| `frontend/src/features/projects/hooks.ts` | Modify | Add credential React Query hooks |
| `frontend/src/features/projects/components/project-settings-dialog.tsx` | Modify | Add URL field, Test Credentials section |
| `backend/alembic/versions/xxxx_playwright_credentials.py` | Create | Migration for `project_credentials` + `projects.url` |

---

### Task 1: Database Model — `ProjectCredential`

**Files:**
- Create: `backend/app/models/project_credential.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/project.py` (add `url` column)

**Steps:**

- [ ] **Step 1: Create `ProjectCredential` model**
```python
# backend/app/models/project_credential.py
import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ProjectCredential(Base):
    __tablename__ = "project_credentials"
    __table_args__ = (
        UniqueConstraint("project_id", "role", name="uq_project_credential_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    encrypted_fields: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: Add `url` column to `Project` model**
```python
# In backend/app/models/project.py, add after wsl_distro:
url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
```

- [ ] **Step 3: Export model in `__init__.py`**
```python
# In backend/app/models/__init__.py, add:
from app.models.project_credential import ProjectCredential
# Add to __all__ list
```

- [ ] **Step 4: Commit**
```
git commit -m "feat: add ProjectCredential model and Project.url column"
```

---

### Task 2: Credential Service with Fernet Encryption

**Files:**
- Create: `backend/app/services/credential_service.py`

**Steps:**

- [ ] **Step 1: Create `CredentialService`**
```python
# backend/app/services/credential_service.py
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.exceptions import NotFoundError
from app.models.project_credential import ProjectCredential
from app.config import settings
import json
import os

class CredentialService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _get_fernet() -> Fernet:
        key = os.environ.get("MANAGER_AI_SECRET_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            os.environ["MANAGER_AI_SECRET_KEY"] = key
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
```

- [ ] **Step 2: Add `cryptography` dependency**
```
pip install cryptography
# Update requirements.txt / pyproject.toml
```

- [ ] **Step 3: Verify import works**
```bash
cd backend && python -c "from app.services.credential_service import CredentialService; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**
```
git commit -m "feat: add CredentialService with Fernet encryption"
```

---

### Task 3: Credential Schemas and Router

**Files:**
- Create: `backend/app/schemas/credential.py`
- Create: `backend/app/routers/credentials.py`
- Modify: `backend/app/schemas/project.py` (add `url` field)
- Modify: `backend/app/main.py` (register router)

**Steps:**

- [ ] **Step 1: Create credential schemas**
```python
# backend/app/schemas/credential.py
from pydantic import BaseModel, Field

class CredentialUpsert(BaseModel):
    role: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=2000)
    fields: dict = Field(default_factory=dict)

class CredentialRole(BaseModel):
    role: str

class CredentialResponse(BaseModel):
    id: str
    project_id: str
    role: str
    url: str
    fields: dict
    created_at: str | None = None
    updated_at: str | None = None
```

- [ ] **Step 2: Add `url` to project schemas**
```python
# In ProjectCreate, ProjectUpdate, ProjectResponse: add url field
# ProjectCreate: url: str | None = None
# ProjectUpdate: url: str | None = None  
# ProjectResponse: url: str | None = None
```

- [ ] **Step 3: Create credentials router**
```python
# backend/app/routers/credentials.py
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
        id=cred.id, project_id=cred.project_id, role=cred.role,
        url=cred.url, fields=decoded,
        created_at=str(cred.created_at) if cred.created_at else None,
        updated_at=str(cred.updated_at) if cred.updated_at else None,
    )

@router.delete("/{role}", status_code=204)
async def delete_credential(project_id: str, role: str, db: AsyncSession = Depends(get_db)):
    svc = CredentialService(db)
    await svc.delete(project_id, role)
    await db.commit()
```

- [ ] **Step 4: Register router in `main.py`**
```python
# In backend/app/main.py:
from app.routers import credentials
# ...
app.include_router(credentials.router)
```

- [ ] **Step 5: Commit**
```
git commit -m "feat: add credential REST endpoints and schemas"
```

---

### Task 4: MCP Tools for Playwright Integration

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`

**Steps:**

- [ ] **Step 1: Add 5 MCP tool descriptions to `default_settings.json`**
```json
{
  "tool.get_project_url.description": "Get the web application URL for a project (for Playwright browser testing). Returns null if project has no URL configured.",
  "tool.list_credentials.description": "List available credential roles for a project (e.g. 'admin', 'user'). Only returns role names, never the actual credential values.",
  "tool.get_credential.description": "Get decrypted credentials for a specific role. Returns url, username, password, and any extra fields. Credentials are decrypted in-memory and never logged.",
  "tool.set_credential.description": "Save or update credentials for a project role. Fields should be a JSON object like {\"username\": \"...\", \"password\": \"...\"}. Encrypted at rest with Fernet.",
  "tool.delete_credential.description": "Delete credentials for a specific role from a project."
}
```

- [ ] **Step 2: Add MCP tools to `server.py`**
```python
# In backend/app/mcp/server.py, after existing tools:

from app.services.credential_service import CredentialService

@mcp.tool(description=_desc["tool.get_project_url.description"])
async def get_project_url(project_id: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
            return {"url": project.url}
        except AppError as e:
            return {"error": e.message}

@mcp.tool(description=_desc["tool.list_credentials.description"])
async def list_credentials(project_id: str) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        roles = await svc.list_roles(project_id)
        return {"roles": roles}

@mcp.tool(description=_desc["tool.get_credential.description"])
async def get_credential(project_id: str, role: str) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        try:
            return await svc.get(project_id, role)
        except AppError as e:
            return {"error": e.message}

@mcp.tool(description=_desc["tool.set_credential.description"])
async def set_credential(project_id: str, role: str, url: str, fields: dict) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        cred = await svc.upsert(project_id, role, url, fields)
        await session.commit()
        return {"id": cred.id, "role": cred.role, "url": cred.url}

@mcp.tool(description=_desc["tool.delete_credential.description"])
async def delete_credential(project_id: str, role: str) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        try:
            await svc.delete(project_id, role)
            await session.commit()
            return {"deleted": True}
        except AppError as e:
            return {"error": e.message}
```

- [ ] **Step 3: Commit**
```
git commit -m "feat: add MCP tools for Playwright credential management"
```

---

### Task 5: Frontend — Types and API Layer

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/features/projects/api.ts`

**Steps:**

- [ ] **Step 1: Add types to shared types**
```typescript
// In frontend/src/shared/types/index.ts:

export interface ProjectCredential {
  id: string;
  project_id: string;
  role: string;
  url: string;
  fields: Record<string, string>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CredentialUpsert {
  role: string;
  url: string;
  fields: Record<string, string>;
}

// Add 'url' to Project, ProjectCreate, ProjectUpdate interfaces:
// url?: string | null;
```

- [ ] **Step 2: Add API functions**
```typescript
// In frontend/src/features/projects/api.ts:

export async function fetchCredentials(projectId: string): Promise<string[]> {
  const res = await fetch(`/api/projects/${projectId}/credentials`);
  if (!res.ok) throw new Error("Failed to fetch credentials");
  return res.json();
}

export async function fetchCredential(projectId: string, role: string): Promise<ProjectCredential> {
  const res = await fetch(`/api/projects/${projectId}/credentials/${encodeURIComponent(role)}`);
  if (!res.ok) throw new Error("Failed to fetch credential");
  return res.json();
}

export async function upsertCredential(projectId: string, data: CredentialUpsert): Promise<ProjectCredential> {
  const res = await fetch(`/api/projects/${projectId}/credentials`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to save credential");
  return res.json();
}

export async function deleteCredential(projectId: string, role: string): Promise<void> {
  const res = await fetch(`/api/projects/${projectId}/credentials/${encodeURIComponent(role)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete credential");
}
```

- [ ] **Step 3: Commit**
```
git commit -m "feat: add frontend types and API layer for credentials"
```

---

### Task 6: Frontend — React Query Hooks

**Files:**
- Modify: `frontend/src/features/projects/hooks.ts`
- Create or modify: `frontend/src/features/projects/hooks-credentials.ts`

**Steps:**

- [ ] **Step 1: Add credential hooks**
```typescript
// New file: frontend/src/features/projects/hooks-credentials.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { CredentialUpsert } from "@/shared/types";
import { projectKeys } from "./hooks";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const credentialKeys = {
  list: (projectId: string) => ["projects", projectId, "credentials"] as const,
  detail: (projectId: string, role: string) => ["projects", projectId, "credentials", role] as const,
};

export function useCredentials(projectId: string) {
  return useQuery({
    queryKey: credentialKeys.list(projectId),
    queryFn: () => api.fetchCredentials(projectId),
    enabled: !!projectId,
  });
}

export function useCredential(projectId: string, role: string) {
  return useQuery({
    queryKey: credentialKeys.detail(projectId, role),
    queryFn: () => api.fetchCredential(projectId, role),
    enabled: !!projectId && !!role,
  });
}

export function useUpsertCredential(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CredentialUpsert) => api.upsertCredential(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: credentialKeys.list(projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteCredential(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (role: string) => api.deleteCredential(projectId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: credentialKeys.list(projectId) });
    },
    onError: onMutationError,
  });
}
```

- [ ] **Step 2: Commit**
```
git commit -m "feat: add React Query hooks for credential management"
```

---

### Task 7: Frontend — Project Settings UI

**Files:**
- Modify: `frontend/src/features/projects/components/project-settings-dialog.tsx`

**Steps:**

- [ ] **Step 1: Add URL field and Test Credentials section to settings dialog**

Add after the Tech Stack field:
```tsx
{/* URL field */}
<div>
  <label className="text-sm font-medium">Web App URL</label>
  <Input
    value={form.url || ""}
    onChange={(e) => setForm({ ...form, url: e.target.value })}
    placeholder="https://example.com"
  />
  <p className="text-xs text-muted-foreground mt-1">
    Base URL for Playwright browser testing.
  </p>
</div>
```

Add after WSL section, before Archive section:
```tsx
{/* Test Credentials section */}
<div className="pt-2 border-t">
  <label className="text-sm font-medium">Test Credentials</label>
  <p className="text-xs text-muted-foreground mt-1 mb-3">
    Credentials used by Claude Code + Playwright for browser testing. Stored encrypted.
  </p>
  {/* List existing credentials */}
  {/* Add credential form (role, login URL, key-value fields) */}
  {/* Delete button per credential */}
</div>
```

Full implementation includes:
- List existing credentials with role, URL, and delete button
- Add form with role input, URL input, dynamic key-value pairs (username/password)
- Edit capability (click existing credential pre-fills form)
- Delete confirmation

- [ ] **Step 2: Update `form` state type to include `url` and wire credential state**
```tsx
const [form, setForm] = useState({
  name: project.name,
  path: project.path,
  description: project.description || "",
  tech_stack: project.tech_stack || "",
  shell: project.shell || "__default__",
  wsl_distro: project.wsl_distro || "",
  url: project.url || "",
});
```

- [ ] **Step 3: Commit**
```
git commit -m "feat: add URL field and Test Credentials UI to project settings"
```

---

### Task 8: Database Migration

**Files:**
- Create: `backend/alembic/versions/xxxx_add_playwright_credentials.py`

**Steps:**

- [ ] **Step 1: Generate Alembic migration**
```bash
cd backend && python -m alembic revision --autogenerate -m "add playwright credentials and project url"
```

- [ ] **Step 2: Verify migration SQL**
```bash
cd backend && python -m alembic upgrade head
```
Expected: Migration applies without errors.

- [ ] **Step 3: Run backend tests to verify no regressions**
```bash
cd backend && python -m pytest
```

- [ ] **Step 4: Commit**
```
git commit -m "feat: add migration for project_credentials table and project.url"
```

## Dependencies

```
Task 1 (Models) ──► Task 2 (Service) ──► Task 3 (Router/Schemas) ──► Task 4 (MCP Tools)
                                                                        │
                                                    Task 5 (Types/API) ─┼─► Task 6 (Hooks) ──► Task 7 (UI)
                                                                        │
                                                    Task 8 (Migration) ─┘ (can run after Task 1)
```

Tasks 5-6-7 (frontend) can run in parallel with Tasks 2-4 (backend) once Task 1 is done.
Task 8 can run anytime after Task 1.