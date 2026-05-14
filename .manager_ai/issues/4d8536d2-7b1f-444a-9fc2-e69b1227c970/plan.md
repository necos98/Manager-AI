# Implementation Plan: Project Linking with Relationship Types

## Architecture

New `project_links` SQL table with FK references to `projects`. Directional: `source_project_id → target_project_id` with free-text `description`. REST API under `/api/projects/{project_id}/links`. Frontend section in ProjectSettingsDialog.

DB-backed (not file-backed) because cross-project queries need referential integrity.

## Files to create/modify

| File | Action |
|------|--------|
| `backend/app/models/project_link.py` | Create - SQLAlchemy model |
| `backend/app/models/__init__.py` | Modify - register ProjectLink |
| `backend/app/schemas/project_link.py` | Create - Pydantic schemas |
| `backend/app/services/project_link_service.py` | Create - business logic |
| `backend/app/routers/project_links.py` | Create - REST endpoints |
| `backend/app/main.py` | Modify - register router |
| `frontend/src/shared/types/index.ts` | Modify - add ProjectLink types |
| `frontend/src/features/projects/api.ts` | Modify - add API functions |
| `frontend/src/features/projects/hooks.ts` | Modify - add hooks |
| `frontend/src/features/projects/components/project-settings-dialog.tsx` | Modify - add section |

---

### Task 1: Create ProjectLink model and migration

**Files:**
- Create: `backend/app/models/project_link.py`

Model:
```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectLink(Base):
    __tablename__ = "project_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    target_project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    source_project = relationship("Project", foreign_keys=[source_project_id])
    target_project = relationship("Project", foreign_keys=[target_project_id])

    __table_args__ = (
        UniqueConstraint("source_project_id", "target_project_id", name="uq_project_link_pair"),
    )
```

- [ ] **Step 1: Create model file**
- [ ] **Step 2: Register in models/__init__.py** - add `from app.models.project_link import ProjectLink` and `"ProjectLink"` to `__all__`
- [ ] **Step 3: Generate migration** with `cd backend && python -m alembic revision --autogenerate -m "add project_links table"`
- [ ] **Step 4: Apply migration** with `cd backend && python -m alembic upgrade head`
- [ ] **Step 5: Verify table exists** - check that the migration created the `project_links` table with correct columns and unique constraint

---

### Task 2: Create Pydantic schemas

**Files:**
- Create: `backend/app/schemas/project_link.py`

```python
from datetime import datetime
from pydantic import BaseModel


class ProjectLinkCreate(BaseModel):
    target_project_id: str
    description: str


class ProjectLinkUpdate(BaseModel):
    description: str


class ProjectLinkResponse(BaseModel):
    id: str
    source_project_id: str
    source_project_name: str
    target_project_id: str
    target_project_name: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 1: Create schema file**

---

### Task 3: Create ProjectLinkService

**Files:**
- Create: `backend/app/services/project_link_service.py`

```python
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.project_link import ProjectLink


class ProjectLinkService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_project(self, project_id: str) -> list[ProjectLink]:
        result = await self.session.execute(
            select(ProjectLink)
            .options(selectinload(ProjectLink.source_project), selectinload(ProjectLink.target_project))
            .where(
                or_(
                    ProjectLink.source_project_id == project_id,
                    ProjectLink.target_project_id == project_id,
                )
            )
            .order_by(ProjectLink.created_at)
        )
        return list(result.scalars().all())

    async def create(self, source_project_id: str, target_project_id: str, description: str) -> ProjectLink:
        if source_project_id == target_project_id:
            raise ValidationError("A project cannot be linked to itself")
        if not description.strip():
            raise ValidationError("Description is required")

        link = ProjectLink(
            source_project_id=source_project_id,
            target_project_id=target_project_id,
            description=description.strip(),
        )
        self.session.add(link)
        await self.session.flush()
        # Reload with relationships
        return await self._get_by_id(link.id)

    async def update(self, link_id: str, project_id: str, description: str) -> ProjectLink:
        link = await self._get_by_id(link_id)
        if link.source_project_id != project_id and link.target_project_id != project_id:
            raise NotFoundError("Project link not found")
        if not description.strip():
            raise ValidationError("Description is required")
        link.description = description.strip()
        await self.session.flush()
        return await self._get_by_id(link_id)

    async def delete(self, link_id: str, project_id: str) -> None:
        link = await self._get_by_id(link_id)
        if link.source_project_id != project_id and link.target_project_id != project_id:
            raise NotFoundError("Project link not found")
        await self.session.delete(link)
        await self.session.flush()

    async def _get_by_id(self, link_id: str) -> ProjectLink:
        result = await self.session.execute(
            select(ProjectLink)
            .options(selectinload(ProjectLink.source_project), selectinload(ProjectLink.target_project))
            .where(ProjectLink.id == link_id)
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise NotFoundError("Project link not found")
        return link
```

- [ ] **Step 1: Create service file**

---

### Task 4: Create router + response builder

**Files:**
- Create: `backend/app/routers/project_links.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_link import ProjectLinkCreate, ProjectLinkResponse, ProjectLinkUpdate
from app.services.project_link_service import ProjectLinkService

router = APIRouter(prefix="/api/projects/{project_id}/links", tags=["project-links"])


def _to_response(link) -> ProjectLinkResponse:
    return ProjectLinkResponse(
        id=link.id,
        source_project_id=link.source_project_id,
        source_project_name=link.source_project.name,
        target_project_id=link.target_project_id,
        target_project_name=link.target_project.name,
        description=link.description,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.get("", response_model=list[ProjectLinkResponse])
async def list_links(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    links = await svc.list_for_project(project_id)
    return [_to_response(l) for l in links]


@router.post("", response_model=ProjectLinkResponse, status_code=201)
async def create_link(project_id: str, data: ProjectLinkCreate, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    link = await svc.create(project_id, data.target_project_id, data.description)
    await db.commit()
    return _to_response(link)


@router.put("/{link_id}", response_model=ProjectLinkResponse)
async def update_link(project_id: str, link_id: str, data: ProjectLinkUpdate, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    link = await svc.update(link_id, project_id, data.description)
    await db.commit()
    return _to_response(link)


@router.delete("/{link_id}", status_code=204)
async def delete_link(project_id: str, link_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    await svc.delete(link_id, project_id)
    await db.commit()
```

- [ ] **Step 1: Create router file**
- [ ] **Step 2: Register router in main.py** - add `from app.routers import ..., project_links` and `app.include_router(project_links.router)`

---

### Task 5: Add frontend types

**Files:**
- Modify: `frontend/src/shared/types/index.ts`

Add after Project types:
```ts
// ── Project Links ──

export interface ProjectLink {
  id: string;
  source_project_id: string;
  source_project_name: string;
  target_project_id: string;
  target_project_name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectLinkCreate {
  target_project_id: string;
  description: string;
}

export interface ProjectLinkUpdate {
  description: string;
}
```

- [ ] **Step 1: Add types to types/index.ts**

---

### Task 6: Add frontend API functions

**Files:**
- Modify: `frontend/src/features/projects/api.ts`

Add after existing functions:
```ts
import type { ProjectLink, ProjectLinkCreate, ProjectLinkUpdate } from "@/shared/types";

export function fetchProjectLinks(projectId: string): Promise<ProjectLink[]> {
  return apiGet<ProjectLink[]>(`/projects/${projectId}/links`);
}

export function createProjectLink(projectId: string, data: ProjectLinkCreate): Promise<ProjectLink> {
  return apiPost<ProjectLink>(`/projects/${projectId}/links`, data);
}

export function updateProjectLink(projectId: string, linkId: string, data: ProjectLinkUpdate): Promise<ProjectLink> {
  return apiPut<ProjectLink>(`/projects/${projectId}/links/${linkId}`, data);
}

export function deleteProjectLink(projectId: string, linkId: string): Promise<void> {
  return apiDelete(`/projects/${projectId}/links/${linkId}`);
}
```

- [ ] **Step 1: Add API functions**

---

### Task 7: Add frontend hooks

**Files:**
- Modify: `frontend/src/features/projects/hooks.ts`

Add:
```ts
import type { ProjectLinkCreate, ProjectLinkUpdate } from "@/shared/types";

export const projectLinkKeys = {
  list: (projectId: string) => ["projects", projectId, "links"] as const,
};

export function useProjectLinks(projectId: string) {
  return useQuery({
    queryKey: projectLinkKeys.list(projectId),
    queryFn: () => api.fetchProjectLinks(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProjectLink(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectLinkCreate) => api.createProjectLink(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectLinkKeys.list(projectId) });
    },
    onError: onMutationError,
  });
}

export function useUpdateProjectLink(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ linkId, data }: { linkId: string; data: ProjectLinkUpdate }) =>
      api.updateProjectLink(projectId, linkId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectLinkKeys.list(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteProjectLink(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (linkId: string) => api.deleteProjectLink(projectId, linkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectLinkKeys.list(projectId) });
    },
    onError: onMutationError,
  });
}
```

- [ ] **Step 1: Add hooks**

---

### Task 8: Add "Linked Projects" section to ProjectSettingsDialog

**Files:**
- Modify: `frontend/src/features/projects/components/project-settings-dialog.tsx`

Add a new section between the "Web App URL" field and the "Test Credentials" section:

```tsx
import { ArrowRight, Pencil, Trash2, Plus } from "lucide-react";
import { useProjectLinks, useCreateProjectLink, useUpdateProjectLink, useDeleteProjectLink } from "@/features/projects/hooks";
import { useProjects } from "@/features/projects/hooks";
import type { ProjectLink } from "@/shared/types";

// Inside component, after existing hooks:
const { data: links } = useProjectLinks(open ? project.id : "");
const createLink = useCreateProjectLink(project.id);
const updateLink = useUpdateProjectLink(project.id);
const deleteLink = useDeleteProjectLink(project.id);
const { data: allProjects } = useProjects(false); // non-archived projects for target selection

const [linkForm, setLinkForm] = useState({ target_project_id: "", description: "" });
const [addingLink, setAddingLink] = useState(false);
const [editingLinkId, setEditingLinkId] = useState<string | null>(null);
const [editDescription, setEditDescription] = useState("");

const availableTargets = (allProjects || []).filter(p => p.id !== project.id);

// Add section after Web App URL section:
{/* Linked Projects */}
<div className="pt-2 border-t">
  <label className="text-sm font-medium">Linked Projects</label>
  <p className="text-xs text-muted-foreground mt-1 mb-3">
    Declare how this project relates to other projects. Links are directional.
  </p>

  {links && links.length > 0 && (
    <div className="space-y-2 mb-3">
      {links.map((link: ProjectLink) => {
        const isSource = link.source_project_id === project.id;
        return (
          <div key={link.id} className="flex items-start justify-between rounded border px-3 py-2 text-sm">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-medium">{link.source_project_name}</span>
                <ArrowRight className="size-3.5 text-muted-foreground shrink-0" />
                <span className="font-medium">{link.target_project_name}</span>
                {!isSource && <span className="text-xs text-muted-foreground">(incoming)</span>}
              </div>
              {editingLinkId === link.id ? (
                <div className="flex gap-2 mt-1">
                  <Input
                    className="h-7 text-xs"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        updateLink.mutate({ linkId: link.id, data: { description: editDescription } }, {
                          onSuccess: () => setEditingLinkId(null),
                        });
                      }
                      if (e.key === "Escape") setEditingLinkId(null);
                    }}
                    autoFocus
                  />
                </div>
              ) : (
                <p className="text-xs text-muted-foreground mt-0.5">{link.description}</p>
              )}
            </div>
            <div className="flex items-center gap-1 shrink-0 ml-2">
              {isSource && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => {
                    setEditingLinkId(link.id);
                    setEditDescription(link.description);
                  }}
                >
                  <Pencil className="size-3" />
                </Button>
              )}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                disabled={deleteLink.isPending}
                onClick={() => deleteLink.mutate(link.id)}
              >
                <Trash2 className="size-3" />
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  )}

  {addingLink ? (
    <div className="space-y-2 rounded border p-3">
      <Select
        value={linkForm.target_project_id}
        onValueChange={(v) => setLinkForm({ ...linkForm, target_project_id: v })}
      >
        <SelectTrigger className="text-sm">
          <SelectValue placeholder="Select target project..." />
        </SelectTrigger>
        <SelectContent>
          {availableTargets.map((p) => (
            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Input
        placeholder="How are they linked? (e.g. exposes API for)"
        value={linkForm.description}
        onChange={(e) => setLinkForm({ ...linkForm, description: e.target.value })}
      />
      <div className="flex gap-2">
        <Button
          type="button"
          size="sm"
          disabled={!linkForm.target_project_id || !linkForm.description.trim() || createLink.isPending}
          onClick={() => {
            createLink.mutate(linkForm, {
              onSuccess: () => {
                setLinkForm({ target_project_id: "", description: "" });
                setAddingLink(false);
                toast.success("Link created");
              },
            });
          }}
        >
          {createLink.isPending ? "Adding..." : "Add Link"}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            setAddingLink(false);
            setLinkForm({ target_project_id: "", description: "" });
          }}
        >
          Cancel
        </Button>
      </div>
    </div>
  ) : (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="w-full"
      onClick={() => setAddingLink(true)}
    >
      <Plus className="size-3.5 mr-1.5" />
      Add Link
    </Button>
  )}
</div>
```

- [ ] **Step 1: Add imports and hooks**
- [ ] **Step 2: Add Linked Projects section JSX**
- [ ] **Step 3: Verify no TypeScript errors** with `cd frontend && npm run lint`

---

### Task 9: Integration smoke test

- [ ] **Step 1: Start backend** with `python start.py`
- [ ] **Step 2: Verify GET /api/projects/{id}/links returns 200 with empty list**
- [ ] **Step 3: Verify POST /api/projects/{id}/links creates a link**
- [ ] **Step 4: Verify PUT updates description**
- [ ] **Step 5: Verify DELETE removes link**
- [ ] **Step 6: Verify self-link rejected**
- [ ] **Step 7: Open frontend, verify "Linked Projects" section appears in settings dialog**

---

### Task 10: Commit

```bash
git add -A
git commit -m "feat: project linking with directional relationships

Add project_links table, CRUD API, and Linked Projects section
in project settings dialog. Directional links with free-text
description for impact analysis between projects."
```
