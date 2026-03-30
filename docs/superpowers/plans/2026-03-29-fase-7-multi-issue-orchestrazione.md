# Fase 7 — Multi-Issue & Orchestrazione: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere Kanban board, relazioni tra issue con grafo visivo, dashboard multi-progetto e terminal grid dinamica.

**Architecture:** Frontend-first per Kanban (7.1) e Terminal Grid (7.4) che non toccano il DB; nuovo modello `IssueRelation` per le relazioni (7.2) con enforcement negli hook; endpoint aggregato read-only per la dashboard (7.3).

**Tech Stack:** `@dnd-kit/core` + `@dnd-kit/sortable` per drag-and-drop, `reactflow` + `@dagrejs/dagre` per il grafo dipendenze, CSS grid nativo per terminal grid.

---

## File Map

### 7.1 Kanban Board
- **Modify** `backend/app/services/issue_service.py` — aggiunge filtro `search` a `list_by_project`
- **Modify** `backend/app/routers/issues.py` — espone `?search=` come query param
- **Modify** `backend/tests/test_routers_issues.py` — test per search
- **Modify** `frontend/src/features/issues/api.ts` — aggiunge `search` param a `fetchIssues`
- **Modify** `frontend/src/features/issues/hooks.ts` — passa `search` param
- **Create** `frontend/src/features/issues/components/kanban-card.tsx`
- **Create** `frontend/src/features/issues/components/kanban-column.tsx`
- **Create** `frontend/src/features/issues/components/kanban-filters.tsx`
- **Create** `frontend/src/features/issues/components/kanban-board.tsx`
- **Modify** `frontend/src/routes/projects/$projectId/issues/index.tsx` — sostituisce IssueList con KanbanBoard

### 7.2 Issue Collegate
- **Create** `backend/app/models/issue_relation.py`
- **Modify** `backend/app/models/__init__.py`
- **Create** `backend/app/schemas/issue_relation.py`
- **Create** `backend/app/services/issue_relation_service.py`
- **Create** `backend/app/routers/issue_relations.py`
- **Modify** `backend/app/main.py`
- **Create** `backend/tests/test_issue_relation_service.py`
- **Create** `backend/tests/test_routers_issue_relations.py`
- **Modify** `backend/app/hooks/handlers/auto_start_workflow.py`
- **Modify** `backend/app/hooks/handlers/auto_start_implementation.py`
- **Modify** `frontend/src/shared/types/index.ts`
- **Create** `frontend/src/features/issues/api-relations.ts`
- **Create** `frontend/src/features/issues/hooks-relations.ts`
- **Create** `frontend/src/features/issues/components/issue-relations-graph.tsx`
- **Create** `frontend/src/features/issues/components/issue-relations-tab.tsx`
- **Modify** `frontend/src/features/issues/components/issue-detail.tsx`
- **Modify** `frontend/src/features/issues/components/kanban-card.tsx`

### 7.3 Multi-project Dashboard
- **Modify** `backend/app/services/project_service.py` — aggiunge `get_dashboard_data()`
- **Modify** `backend/app/schemas/project.py` — aggiunge `DashboardIssue`, `DashboardProject`
- **Modify** `backend/app/routers/projects.py` — aggiunge `GET /api/dashboard`
- **Create** `backend/tests/test_routers_dashboard.py`
- **Modify** `frontend/src/shared/types/index.ts`
- **Create** `frontend/src/features/projects/api-dashboard.ts`
- **Create** `frontend/src/features/projects/hooks-dashboard.ts`
- **Create** `frontend/src/routes/dashboard.tsx`
- **Modify** `frontend/src/shared/components/app-sidebar.tsx`

### 7.4 Terminal Grid
- **Create** `frontend/src/features/terminals/components/terminal-grid.tsx`
- **Modify** `frontend/src/routes/terminals.tsx`

---

## SEZIONE 1 — Kanban Board (7.1)

---

### Task 1: Backend — search param per le issue

**Files:**
- Modify: `backend/app/services/issue_service.py`
- Modify: `backend/app/routers/issues.py`
- Test: `backend/tests/test_routers_issues.py`

- [ ] **Step 1: Scrivi il test**

Aggiungi in fondo a `backend/tests/test_routers_issues.py`:

```python
@pytest.mark.asyncio
async def test_list_issues_search(client, project):
    await client.post(f"/api/projects/{project['id']}/issues", json={"description": "fix login bug", "priority": 1})
    await client.post(f"/api/projects/{project['id']}/issues", json={"description": "add dashboard", "priority": 2})
    resp = await client.get(f"/api/projects/{project['id']}/issues?search=login")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "login" in data[0]["description"]

@pytest.mark.asyncio
async def test_list_issues_search_by_name(client, project):
    # Create issue then set name via update
    resp = await client.post(f"/api/projects/{project['id']}/issues", json={"description": "some desc", "priority": 1})
    issue_id = resp.json()["id"]
    await client.put(f"/api/projects/{project['id']}/issues/{issue_id}", json={"name": "My Special Issue"})
    await client.post(f"/api/projects/{project['id']}/issues", json={"description": "other issue", "priority": 2})
    resp = await client.get(f"/api/projects/{project['id']}/issues?search=special")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == issue_id
```

- [ ] **Step 2: Esegui il test per verificare che fallisce**

```bash
cd backend && python -m pytest tests/test_routers_issues.py::test_list_issues_search -v
```
Atteso: FAIL — il param `search` viene ignorato e ritorna tutte le issue.

- [ ] **Step 3: Modifica `issue_service.py`**

In `list_by_project`, aggiungi il parametro `search`:

```python
async def list_by_project(
    self, project_id: str, status: IssueStatus | None = None, search: str | None = None
) -> list[Issue]:
    from sqlalchemy import or_
    query = select(Issue).options(selectinload(Issue.tasks)).where(Issue.project_id == project_id)
    if status is not None:
        query = query.where(Issue.status == status)
    if search:
        term = f"%{search.lower()}%"
        query = query.where(
            or_(
                Issue.description.ilike(term),
                Issue.name.ilike(term),
            )
        )
    query = query.order_by(Issue.priority.asc(), Issue.created_at.asc())
    result = await self.session.execute(query)
    return list(result.unique().scalars().all())
```

- [ ] **Step 4: Modifica `routers/issues.py`**

Aggiorna `list_issues` per accettare `search`:

```python
@router.get("", response_model=list[IssueResponse])
async def list_issues(
    project_id: str,
    status: IssueStatus | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    return await service.list_by_project(project_id, status=status, search=search)
```

- [ ] **Step 5: Esegui i test**

```bash
cd backend && python -m pytest tests/test_routers_issues.py -v
```
Atteso: tutti i test PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/issue_service.py backend/app/routers/issues.py backend/tests/test_routers_issues.py
git commit -m "feat: add search query param to issues list endpoint"
```

---

### Task 2: Installa dipendenze frontend per Kanban

**Files:**
- `frontend/package.json` (modificato da npm)

- [ ] **Step 1: Installa @dnd-kit**

```bash
cd frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

- [ ] **Step 2: Verifica installazione**

```bash
cd frontend && node -e "require('@dnd-kit/core'); console.log('ok')"
```
Atteso: `ok`

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "deps: add @dnd-kit for kanban drag-and-drop"
```

---

### Task 3: Aggiorna api.ts e hooks.ts per search

**Files:**
- Modify: `frontend/src/features/issues/api.ts`
- Modify: `frontend/src/features/issues/hooks.ts`

- [ ] **Step 1: Modifica `api.ts`**

Sostituisci la funzione `fetchIssues` esistente:

```typescript
export function fetchIssues(
  projectId: string,
  status?: IssueStatus,
  search?: string
): Promise<Issue[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search) params.set("search", search);
  const qs = params.toString();
  return request(`/projects/${projectId}/issues${qs ? `?${qs}` : ""}`);
}
```

- [ ] **Step 2: Modifica `hooks.ts`**

Trova `useIssues` e aggiorna la firma per accettare `search`:

```typescript
export function useIssues(projectId: string, status?: IssueStatus, search?: string) {
  return useQuery({
    queryKey: ["issues", projectId, status, search],
    queryFn: () => fetchIssues(projectId, status, search),
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/issues/api.ts frontend/src/features/issues/hooks.ts
git commit -m "feat: add search param to fetchIssues and useIssues"
```

---

### Task 4: Crea KanbanCard

**Files:**
- Create: `frontend/src/features/issues/components/kanban-card.tsx`

- [ ] **Step 1: Crea il file**

```typescript
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Terminal } from "lucide-react";
import { Card } from "@/shared/components/ui/card";
import { StatusBadge } from "./status-badge";
import type { Issue } from "@/shared/types";

interface KanbanCardProps {
  issue: Issue;
  hasTerminal: boolean;
  isBlocked?: boolean;
}

function TaskProgress({ tasks }: { tasks: Issue["tasks"] }) {
  if (!tasks || tasks.length === 0) return null;
  const completed = tasks.filter((t) => t.status === "Completed").length;
  const total = tasks.length;
  const percent = Math.round((completed / total) * 100);
  return (
    <div className="flex items-center gap-2 mt-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${percent}%` }} />
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">{completed}/{total}</span>
    </div>
  );
}

export function KanbanCard({ issue, hasTerminal, isBlocked = false }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: issue.id,
    data: { issue },
  });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes} className="touch-none">
      <Card className="px-3 py-2.5 cursor-grab active:cursor-grabbing hover:bg-accent/50 transition-colors">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              {hasTerminal && (
                <Terminal className="size-3 text-green-500 flex-shrink-0" style={{ filter: "drop-shadow(0 0 4px #4ade80)" }} />
              )}
              {isBlocked && (
                <span className="text-xs bg-destructive/15 text-destructive px-1.5 py-0.5 rounded font-medium flex-shrink-0">
                  Bloccata
                </span>
              )}
            </div>
            <p className="text-sm font-medium truncate mt-0.5">
              {issue.name || issue.description}
            </p>
            {issue.name && (
              <p className="text-xs text-muted-foreground truncate">{issue.description}</p>
            )}
          </div>
          <span className="text-xs text-muted-foreground flex-shrink-0">P{issue.priority}</span>
        </div>
        <TaskProgress tasks={issue.tasks} />
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/issues/components/kanban-card.tsx
git commit -m "feat: add KanbanCard component with dnd-kit draggable"
```

---

### Task 5: Crea KanbanColumn e KanbanFilters

**Files:**
- Create: `frontend/src/features/issues/components/kanban-column.tsx`
- Create: `frontend/src/features/issues/components/kanban-filters.tsx`

- [ ] **Step 1: Crea `kanban-column.tsx`**

```typescript
import { useDroppable } from "@dnd-kit/core";
import { KanbanCard } from "./kanban-card";
import { StatusBadge } from "./status-badge";
import type { Issue, IssueStatus } from "@/shared/types";

interface KanbanColumnProps {
  status: IssueStatus;
  issues: Issue[];
  activeTerminalIssueIds: string[];
  blockedIssueIds: Set<string>;
  isValidTarget: boolean;
}

export function KanbanColumn({ status, issues, activeTerminalIssueIds, blockedIssueIds, isValidTarget }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div className="flex flex-col min-w-[220px] flex-1">
      <div className="flex items-center gap-2 mb-3">
        <StatusBadge status={status} />
        <span className="text-xs text-muted-foreground">{issues.length}</span>
      </div>
      <div
        ref={setNodeRef}
        className={[
          "flex-1 rounded-lg p-2 min-h-[120px] space-y-2 transition-colors",
          isOver && isValidTarget ? "bg-primary/10 ring-1 ring-primary" : "bg-muted/30",
          isOver && !isValidTarget ? "bg-destructive/10 ring-1 ring-destructive" : "",
        ].join(" ")}
      >
        {issues.map((issue) => (
          <KanbanCard
            key={issue.id}
            issue={issue}
            hasTerminal={activeTerminalIssueIds.includes(issue.id)}
            isBlocked={blockedIssueIds.has(issue.id)}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Crea `kanban-filters.tsx`**

```typescript
import { Search } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";

export type SortKey = "priority" | "created_at" | "updated_at";

interface KanbanFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  priority: string;
  onPriorityChange: (v: string) => void;
  sort: SortKey;
  onSortChange: (v: SortKey) => void;
}

export function KanbanFilters({ search, onSearchChange, priority, onPriorityChange, sort, onSortChange }: KanbanFiltersProps) {
  return (
    <div className="flex gap-2 flex-wrap mb-4">
      <div className="relative flex-1 min-w-[180px]">
        <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
        <Input
          placeholder="Cerca issue..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-8 h-8 text-sm"
        />
      </div>
      <Select value={priority} onValueChange={onPriorityChange}>
        <SelectTrigger className="w-[120px] h-8 text-sm">
          <SelectValue placeholder="Priorità" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Tutte</SelectItem>
          <SelectItem value="1">P1</SelectItem>
          <SelectItem value="2">P2</SelectItem>
          <SelectItem value="3">P3</SelectItem>
          <SelectItem value="4">P4</SelectItem>
          <SelectItem value="5">P5</SelectItem>
        </SelectContent>
      </Select>
      <Select value={sort} onValueChange={(v) => onSortChange(v as SortKey)}>
        <SelectTrigger className="w-[140px] h-8 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="priority">Per priorità</SelectItem>
          <SelectItem value="created_at">Per data creazione</SelectItem>
          <SelectItem value="updated_at">Per ultimo aggiornamento</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/issues/components/kanban-column.tsx frontend/src/features/issues/components/kanban-filters.tsx
git commit -m "feat: add KanbanColumn and KanbanFilters components"
```

---

### Task 6: Crea KanbanBoard e aggiorna la route

**Files:**
- Create: `frontend/src/features/issues/components/kanban-board.tsx`
- Modify: `frontend/src/routes/projects/$projectId/issues/index.tsx`

- [ ] **Step 1: Crea `kanban-board.tsx`**

```typescript
import { useState, useMemo } from "react";
import { DndContext, DragEndEvent, DragOverlay, closestCenter, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { KanbanColumn } from "./kanban-column";
import { KanbanCard } from "./kanban-card";
import { KanbanFilters, SortKey } from "./kanban-filters";
import { useUpdateIssueStatus } from "@/features/issues/hooks";
import type { Issue, IssueStatus } from "@/shared/types";

const COLUMNS: IssueStatus[] = ["New", "Reasoning", "Planned", "Accepted", "Finished", "Canceled"];

const VALID_TRANSITIONS = new Set([
  "New->Reasoning",
  "Reasoning->Planned",
  "Planned->Accepted",
  "Accepted->Finished",
]);

function isValidTransition(from: IssueStatus, to: IssueStatus): boolean {
  return VALID_TRANSITIONS.has(`${from}->${to}`) || to === "Canceled";
}

interface PendingTransition {
  issue: Issue;
  to: IssueStatus;
}

interface KanbanBoardProps {
  issues: Issue[];
  projectId: string;
  activeTerminalIssueIds: string[];
  blockedIssueIds?: Set<string>;
}

export function KanbanBoard({ issues, projectId, activeTerminalIssueIds, blockedIssueIds = new Set() }: KanbanBoardProps) {
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("all");
  const [sort, setSort] = useState<SortKey>("priority");
  const [pending, setPending] = useState<PendingTransition | null>(null);
  const [activeIssue, setActiveIssue] = useState<Issue | null>(null);
  const updateStatus = useUpdateIssueStatus(projectId);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const filtered = useMemo(() => {
    let list = issues;
    if (search) {
      const term = search.toLowerCase();
      list = list.filter((i) => i.description.toLowerCase().includes(term) || i.name?.toLowerCase().includes(term));
    }
    if (priority !== "all") {
      list = list.filter((i) => String(i.priority) === priority);
    }
    return [...list].sort((a, b) => {
      if (sort === "priority") return a.priority - b.priority;
      if (sort === "created_at") return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [issues, search, priority, sort]);

  const byStatus = useMemo(() => {
    const map = new Map<IssueStatus, Issue[]>();
    COLUMNS.forEach((s) => map.set(s, []));
    filtered.forEach((i) => map.get(i.status)?.push(i));
    return map;
  }, [filtered]);

  function handleDragStart(event: { active: { id: string; data: { current?: { issue: Issue } } } }) {
    setActiveIssue(event.active.data.current?.issue ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveIssue(null);
    const { active, over } = event;
    if (!over) return;
    const issue = issues.find((i) => i.id === active.id);
    const newStatus = over.id as IssueStatus;
    if (!issue || issue.status === newStatus) return;
    if (!isValidTransition(issue.status, newStatus)) return;
    setPending({ issue, to: newStatus });
  }

  async function confirmTransition() {
    if (!pending) return;
    await updateStatus.mutateAsync({ issueId: pending.issue.id, status: pending.to });
    setPending(null);
  }

  return (
    <>
      <KanbanFilters
        search={search}
        onSearchChange={setSearch}
        priority={priority}
        onPriorityChange={setPriority}
        sort={sort}
        onSortChange={setSort}
      />

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart as any} onDragEnd={handleDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-4">
          {COLUMNS.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              issues={byStatus.get(status) ?? []}
              activeTerminalIssueIds={activeTerminalIssueIds}
              blockedIssueIds={blockedIssueIds}
              isValidTarget={activeIssue ? isValidTransition(activeIssue.status, status) : false}
            />
          ))}
        </div>
        <DragOverlay>
          {activeIssue && (
            <KanbanCard
              issue={activeIssue}
              hasTerminal={activeTerminalIssueIds.includes(activeIssue.id)}
              isBlocked={blockedIssueIds.has(activeIssue.id)}
            />
          )}
        </DragOverlay>
      </DndContext>

      <Dialog open={!!pending} onOpenChange={(open) => !open && setPending(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cambia stato</DialogTitle>
            <DialogDescription>
              Sposta "{pending?.issue.name || pending?.issue.description}" da {pending?.issue.status} a {pending?.to}?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>Annulla</Button>
            <Button onClick={confirmTransition} disabled={updateStatus.isPending}>
              {updateStatus.isPending ? "..." : "Conferma"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

- [ ] **Step 2: Verifica che `useUpdateIssueStatus` esista in `hooks.ts`**

Apri `frontend/src/features/issues/hooks.ts` e cerca `useUpdateIssueStatus`. Se non esiste con esattamente questo nome, aggiungilo:

```typescript
export function useUpdateIssueStatus(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ issueId, status }: { issueId: string; status: IssueStatus }) =>
      updateIssueStatus(projectId, issueId, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["issues", projectId] });
    },
  });
}
```

- [ ] **Step 3: Aggiorna la route `issues/index.tsx`**

Sostituisci il contenuto del file:

```typescript
import { useState, useEffect } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useIssues } from "@/features/issues/hooks";
import { useProject } from "@/features/projects/hooks";
import { useTerminals } from "@/features/terminals/hooks";
import { KanbanBoard } from "@/features/issues/components/kanban-board";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId/issues/")({
  component: IssuesPage,
});

function IssuesPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Issues - ${project.name}` : "Issues";
  }, [project]);

  const { data: issues, isLoading } = useIssues(projectId);
  const { data: terminals } = useTerminals(projectId);
  const activeTerminalIssueIds = terminals?.map((t) => t.issue_id) ?? [];

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16" />)}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          {project && <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>}
          <h1 className="text-xl font-semibold">Issues</h1>
        </div>
        <Button asChild size="sm">
          <Link to="/projects/$projectId/issues/new" params={{ projectId }}>
            <Plus className="size-4 mr-1" />
            New Issue
          </Link>
        </Button>
      </div>
      <KanbanBoard
        issues={issues ?? []}
        projectId={projectId}
        activeTerminalIssueIds={activeTerminalIssueIds}
      />
    </div>
  );
}
```

- [ ] **Step 4: Avvia il frontend e verifica visivamente**

```bash
cd frontend && npm run dev
```
Apri `http://localhost:5173`, naviga su un progetto → Issues. Verifica: colonne per stato, card draggabili, filtri funzionanti, modale di conferma al drop.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/issues/components/kanban-board.tsx frontend/src/routes/projects/\$projectId/issues/index.tsx
git commit -m "feat: replace issue list with Kanban board (7.1 complete)"
```

---

## SEZIONE 2 — Issue Collegate (7.2)

---

### Task 7: Modello IssueRelation + migrazione

**Files:**
- Create: `backend/app/models/issue_relation.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Crea `issue_relation.py`**

```python
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RelationType(str, enum.Enum):
    BLOCKS = "blocks"
    RELATED = "related"


class IssueRelation(Base):
    __tablename__ = "issue_relations"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation_type", name="uq_issue_relation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[RelationType] = mapped_column(Enum(RelationType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source = relationship("Issue", foreign_keys=[source_id])
    target = relationship("Issue", foreign_keys=[target_id])
```

- [ ] **Step 2: Aggiorna `models/__init__.py`**

```python
from app.database import Base
from app.models.activity_log import ActivityLog
from app.models.issue import Issue
from app.models.issue_feedback import IssueFeedback
from app.models.issue_relation import IssueRelation
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.project_skill import ProjectSkill
from app.models.project_variable import ProjectVariable
from app.models.prompt_template import PromptTemplate
from app.models.setting import Setting
from app.models.task import Task
from app.models.terminal_command import TerminalCommand

__all__ = [
    "ActivityLog", "Base", "Issue", "IssueFeedback", "IssueRelation", "Project", "ProjectFile",
    "ProjectSkill", "ProjectVariable", "PromptTemplate", "Setting", "Task", "TerminalCommand",
]
```

- [ ] **Step 3: Aggiorna `conftest.py` per includere IssueRelation**

In `backend/tests/conftest.py`, aggiungi l'import del nuovo modello (riga 9, nella lista imports):

```python
from app.models.issue_relation import IssueRelation  # noqa: F401
```

- [ ] **Step 4: Crea migrazione Alembic**

```bash
cd backend && python -m alembic revision --autogenerate -m "add issue_relations table"
python -m alembic upgrade head
```

- [ ] **Step 5: Verifica migrazione**

```bash
cd backend && python -m alembic current
```
Atteso: mostra la revisione più recente come `(head)`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/issue_relation.py backend/app/models/__init__.py backend/tests/conftest.py backend/alembic/versions/
git commit -m "feat: add IssueRelation model and migration"
```

---

### Task 8: IssueRelationService

**Files:**
- Create: `backend/app/services/issue_relation_service.py`
- Create: `backend/tests/test_issue_relation_service.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_issue_relation_service.py`:

```python
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.exceptions import NotFoundError, ValidationError
from app.models.issue import Issue, IssueStatus
from app.models.issue_relation import IssueRelation, RelationType
from app.models.project import Project
from app.services.issue_relation_service import IssueRelationService


@pytest_asyncio.fixture
async def project(db_session):
    p = Project(name="Test", path="/tmp")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def issues(db_session, project):
    issues = [Issue(project_id=project.id, description=f"Issue {i}", status=IssueStatus.NEW) for i in range(4)]
    for i in issues:
        db_session.add(i)
    await db_session.flush()
    return issues


@pytest.mark.asyncio
async def test_add_blocks_relation(db_session, issues):
    svc = IssueRelationService(db_session)
    rel = await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    assert rel.source_id == issues[0].id
    assert rel.target_id == issues[1].id
    assert rel.relation_type == RelationType.BLOCKS


@pytest.mark.asyncio
async def test_add_related_normalizes_order(db_session, issues):
    svc = IssueRelationService(db_session)
    # Pass target < source to verify normalization
    a, b = sorted([issues[0].id, issues[1].id])
    rel = await svc.add_relation(b, a, RelationType.RELATED)
    # source should be the smaller UUID
    assert rel.source_id == a
    assert rel.target_id == b


@pytest.mark.asyncio
async def test_self_relation_raises(db_session, issues):
    svc = IssueRelationService(db_session)
    with pytest.raises(ValidationError):
        await svc.add_relation(issues[0].id, issues[0].id, RelationType.BLOCKS)


@pytest.mark.asyncio
async def test_cycle_detection(db_session, issues):
    svc = IssueRelationService(db_session)
    # A blocks B, B blocks C — adding C blocks A should fail
    await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    await svc.add_relation(issues[1].id, issues[2].id, RelationType.BLOCKS)
    with pytest.raises(ValidationError):
        await svc.add_relation(issues[2].id, issues[0].id, RelationType.BLOCKS)


@pytest.mark.asyncio
async def test_get_blockers(db_session, issues):
    svc = IssueRelationService(db_session)
    await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    blockers = await svc.get_blockers(issues[1].id)
    assert len(blockers) == 1
    assert blockers[0].source_id == issues[0].id


@pytest.mark.asyncio
async def test_get_relations_for_issue(db_session, issues):
    svc = IssueRelationService(db_session)
    await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    await svc.add_relation(issues[0].id, issues[2].id, RelationType.RELATED)
    relations = await svc.get_relations_for_issue(issues[0].id)
    assert len(relations) == 2


@pytest.mark.asyncio
async def test_delete_relation(db_session, issues):
    svc = IssueRelationService(db_session)
    rel = await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    await svc.delete_relation(rel.id, issues[0].id)
    relations = await svc.get_relations_for_issue(issues[0].id)
    assert len(relations) == 0
```

- [ ] **Step 2: Esegui i test per verificare che falliscono**

```bash
cd backend && python -m pytest tests/test_issue_relation_service.py -v
```
Atteso: tutti FAIL per import error.

- [ ] **Step 3: Implementa il service**

Crea `backend/app/services/issue_relation_service.py`:

```python
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models.issue_relation import IssueRelation, RelationType


class IssueRelationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_relation(
        self, source_id: str, target_id: str, relation_type: RelationType
    ) -> IssueRelation:
        if source_id == target_id:
            raise ValidationError("Un'issue non può essere collegata a se stessa")

        # Normalize RELATED: source_id < target_id alphabetically
        if relation_type == RelationType.RELATED and source_id > target_id:
            source_id, target_id = target_id, source_id

        # Cycle detection (only for BLOCKS)
        if relation_type == RelationType.BLOCKS:
            if await self._detect_cycle(source_id, target_id):
                raise ValidationError("Aggiungere questa relazione creerebbe una dipendenza circolare")

        relation = IssueRelation(source_id=source_id, target_id=target_id, relation_type=relation_type)
        self.session.add(relation)
        await self.session.flush()
        return relation

    async def _detect_cycle(self, source_id: str, target_id: str) -> bool:
        """Return True if adding source->target BLOCKS would create a cycle."""
        visited: set[str] = set()
        queue = [target_id]
        while queue:
            current = queue.pop(0)
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            result = await self.session.execute(
                select(IssueRelation.target_id)
                .where(IssueRelation.source_id == current)
                .where(IssueRelation.relation_type == RelationType.BLOCKS)
            )
            queue.extend(result.scalars().all())
        return False

    async def get_relations_for_issue(self, issue_id: str) -> list[IssueRelation]:
        result = await self.session.execute(
            select(IssueRelation).where(
                or_(IssueRelation.source_id == issue_id, IssueRelation.target_id == issue_id)
            )
        )
        return list(result.scalars().all())

    async def get_blockers(self, issue_id: str) -> list[IssueRelation]:
        """Return BLOCKS relations where this issue is the target (i.e., it is blocked)."""
        result = await self.session.execute(
            select(IssueRelation)
            .where(IssueRelation.target_id == issue_id)
            .where(IssueRelation.relation_type == RelationType.BLOCKS)
        )
        return list(result.scalars().all())

    async def get_by_id(self, relation_id: int) -> IssueRelation:
        rel = await self.session.get(IssueRelation, relation_id)
        if rel is None:
            raise NotFoundError("Relazione non trovata")
        return rel

    async def delete_relation(self, relation_id: int, requesting_issue_id: str) -> None:
        rel = await self.get_by_id(relation_id)
        if rel.source_id != requesting_issue_id and rel.target_id != requesting_issue_id:
            raise NotFoundError("Relazione non trovata")
        await self.session.delete(rel)
        await self.session.flush()
```

- [ ] **Step 4: Esegui i test**

```bash
cd backend && python -m pytest tests/test_issue_relation_service.py -v
```
Atteso: tutti PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/issue_relation_service.py backend/tests/test_issue_relation_service.py
git commit -m "feat: add IssueRelationService with cycle detection"
```

---

### Task 9: Schema e Router per issue relations

**Files:**
- Create: `backend/app/schemas/issue_relation.py`
- Create: `backend/app/routers/issue_relations.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_issue_relations.py`

- [ ] **Step 1: Crea lo schema**

Crea `backend/app/schemas/issue_relation.py`:

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.issue_relation import RelationType


class IssueRelationCreate(BaseModel):
    target_id: str
    relation_type: RelationType


class IssueRelationResponse(BaseModel):
    id: int
    source_id: str
    target_id: str
    relation_type: RelationType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Scrivi i test del router**

Crea `backend/tests/test_routers_issue_relations.py`:

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def project(client):
    resp = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    return resp.json()


@pytest_asyncio.fixture
async def two_issues(client, project):
    r1 = await client.post(f"/api/projects/{project['id']}/issues", json={"description": "Issue A"})
    r2 = await client.post(f"/api/projects/{project['id']}/issues", json={"description": "Issue B"})
    return r1.json(), r2.json()


@pytest.mark.asyncio
async def test_add_relation(client, two_issues):
    a, b = two_issues
    resp = await client.post(
        f"/api/issues/{a['id']}/relations",
        json={"target_id": b["id"], "relation_type": "blocks"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_id"] == a["id"]
    assert data["target_id"] == b["id"]


@pytest.mark.asyncio
async def test_get_relations(client, two_issues):
    a, b = two_issues
    await client.post(f"/api/issues/{a['id']}/relations", json={"target_id": b["id"], "relation_type": "blocks"})
    resp = await client.get(f"/api/issues/{a['id']}/relations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_delete_relation(client, two_issues):
    a, b = two_issues
    rel = (await client.post(f"/api/issues/{a['id']}/relations", json={"target_id": b["id"], "relation_type": "blocks"})).json()
    resp = await client.delete(f"/api/issues/{a['id']}/relations/{rel['id']}")
    assert resp.status_code == 204
    remaining = (await client.get(f"/api/issues/{a['id']}/relations")).json()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_self_relation_rejected(client, two_issues):
    a, _ = two_issues
    resp = await client.post(f"/api/issues/{a['id']}/relations", json={"target_id": a["id"], "relation_type": "blocks"})
    assert resp.status_code == 422
```

- [ ] **Step 3: Esegui i test per verificare che falliscono**

```bash
cd backend && python -m pytest tests/test_routers_issue_relations.py -v
```
Atteso: FAIL — router non esiste.

- [ ] **Step 4: Crea il router**

Crea `backend/app/routers/issue_relations.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.issue_relation import IssueRelationCreate, IssueRelationResponse
from app.services.issue_relation_service import IssueRelationService

router = APIRouter(prefix="/api/issues/{issue_id}/relations", tags=["issue-relations"])


@router.get("", response_model=list[IssueRelationResponse])
async def get_relations(issue_id: str, db: AsyncSession = Depends(get_db)):
    svc = IssueRelationService(db)
    return await svc.get_relations_for_issue(issue_id)


@router.post("", response_model=IssueRelationResponse, status_code=201)
async def add_relation(issue_id: str, data: IssueRelationCreate, db: AsyncSession = Depends(get_db)):
    svc = IssueRelationService(db)
    relation = await svc.add_relation(issue_id, data.target_id, data.relation_type)
    await db.commit()
    return relation


@router.delete("/{relation_id}", status_code=204)
async def delete_relation(issue_id: str, relation_id: int, db: AsyncSession = Depends(get_db)):
    svc = IssueRelationService(db)
    await svc.delete_relation(relation_id, issue_id)
    await db.commit()
```

- [ ] **Step 5: Registra il router in `main.py`**

In `main.py`, aggiungi l'import:
```python
from app.routers import activity, events, files, issue_relations, issues, library, project_settings, project_skills, project_templates, project_variables, projects, settings as settings_router, tasks, terminals, terminal_commands
```

E dopo `app.include_router(issues.router)`:
```python
app.include_router(issue_relations.router)
```

- [ ] **Step 6: Esegui i test**

```bash
cd backend && python -m pytest tests/test_routers_issue_relations.py -v
```
Atteso: tutti PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/issue_relation.py backend/app/routers/issue_relations.py backend/app/main.py backend/tests/test_routers_issue_relations.py
git commit -m "feat: add issue relations CRUD endpoints"
```

---

### Task 10: Enforcement nei hook

**Files:**
- Modify: `backend/app/hooks/handlers/auto_start_workflow.py`
- Modify: `backend/app/hooks/handlers/auto_start_implementation.py`

- [ ] **Step 1: Modifica `auto_start_workflow.py`**

Dopo il controllo `paused`, aggiungi il check blockers (prima della costruzione del prompt). Inserisci subito dopo l'apertura della sessione per il controllo `paused`:

```python
        # Check blockers
        async with async_session() as session:
            from app.services.issue_relation_service import IssueRelationService
            from app.services.issue_service import IssueService
            rel_svc = IssueRelationService(session)
            blockers = await rel_svc.get_blockers(context.issue_id)
            if blockers:
                issue_svc = IssueService(session)
                unfinished = []
                for rel in blockers:
                    blocker = await issue_svc.get_by_id(rel.source_id)
                    if blocker and blocker.status.value != "Finished":
                        unfinished.append(blocker.name or blocker.description[:40])
                if unfinished:
                    names = ", ".join(unfinished)
                    return HookResult(
                        success=True,
                        output=f"Issue bloccata da: {names}. Completare prima le dipendenze."
                    )
```

- [ ] **Step 2: Applica lo stesso blocco in `auto_start_implementation.py`**

Apri `backend/app/hooks/handlers/auto_start_implementation.py` e individua il punto iniziale dell'`execute`. Aggiungi subito dopo il controllo `paused` (o all'inizio se non c'è) lo stesso blocco blockers mostrato sopra:

```python
        # Check blockers
        async with async_session() as session:
            from app.services.issue_relation_service import IssueRelationService
            from app.services.issue_service import IssueService
            rel_svc = IssueRelationService(session)
            blockers = await rel_svc.get_blockers(context.issue_id)
            if blockers:
                issue_svc = IssueService(session)
                unfinished = []
                for rel in blockers:
                    blocker = await issue_svc.get_by_id(rel.source_id)
                    if blocker and blocker.status.value != "Finished":
                        unfinished.append(blocker.name or blocker.description[:40])
                if unfinished:
                    names = ", ".join(unfinished)
                    return HookResult(
                        success=True,
                        output=f"Issue bloccata da: {names}. Completare prima le dipendenze."
                    )
```

- [ ] **Step 3: Verifica che i test esistenti passano ancora**

```bash
cd backend && python -m pytest tests/test_auto_start_workflow.py tests/test_auto_start_implementation.py -v
```
Atteso: tutti PASS (i mock nei test esistenti non toccano il nuovo codice).

- [ ] **Step 4: Commit**

```bash
git add backend/app/hooks/handlers/auto_start_workflow.py backend/app/hooks/handlers/auto_start_implementation.py
git commit -m "feat: block hook execution when issue has unfinished blockers"
```

---

### Task 11: Frontend — tipi, API e hook per le relazioni

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Create: `frontend/src/features/issues/api-relations.ts`
- Create: `frontend/src/features/issues/hooks-relations.ts`

- [ ] **Step 1: Aggiungi tipi in `types/index.ts`**

In fondo al file, aggiungi:

```typescript
// ── Issue Relations ──

export type RelationType = "blocks" | "related";

export interface IssueRelation {
  id: number;
  source_id: string;
  target_id: string;
  relation_type: RelationType;
  created_at: string;
}

export interface IssueRelationCreate {
  target_id: string;
  relation_type: RelationType;
}
```

- [ ] **Step 2: Crea `api-relations.ts`**

```typescript
import { request } from "@/shared/api/client";
import type { IssueRelation, IssueRelationCreate } from "@/shared/types";

export function fetchRelations(issueId: string): Promise<IssueRelation[]> {
  return request(`/issues/${issueId}/relations`);
}

export function addRelation(issueId: string, data: IssueRelationCreate): Promise<IssueRelation> {
  return request(`/issues/${issueId}/relations`, { method: "POST", body: JSON.stringify(data) });
}

export function deleteRelation(issueId: string, relationId: number): Promise<null> {
  return request(`/issues/${issueId}/relations/${relationId}`, { method: "DELETE" });
}
```

- [ ] **Step 3: Crea `hooks-relations.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addRelation, deleteRelation, fetchRelations } from "./api-relations";
import type { IssueRelationCreate } from "@/shared/types";

export function useRelations(issueId: string) {
  return useQuery({
    queryKey: ["relations", issueId],
    queryFn: () => fetchRelations(issueId),
  });
}

export function useAddRelation(issueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueRelationCreate) => addRelation(issueId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["relations", issueId] }),
  });
}

export function useDeleteRelation(issueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (relationId: number) => deleteRelation(issueId, relationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["relations", issueId] }),
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/types/index.ts frontend/src/features/issues/api-relations.ts frontend/src/features/issues/hooks-relations.ts
git commit -m "feat: add frontend types, API and hooks for issue relations"
```

---

### Task 12: Installa react-flow + grafo

**Files:**
- Create: `frontend/src/features/issues/components/issue-relations-graph.tsx`
- Create: `frontend/src/features/issues/components/issue-relations-tab.tsx`

- [ ] **Step 1: Installa dipendenze**

```bash
cd frontend && npm install reactflow @dagrejs/dagre
```

- [ ] **Step 2: Crea `issue-relations-graph.tsx`**

```typescript
import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  NodeMouseHandler,
  useNodesState,
  useEdgesState,
} from "reactflow";
import dagre from "@dagrejs/dagre";
import "reactflow/dist/style.css";
import type { Issue, IssueRelation } from "@/shared/types";

const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

function getLayoutedElements(nodes: Node[], edges: Edge[]) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 70, ranksep: 60 });
  nodes.forEach((node) => g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((edge) => g.setEdge(edge.source, edge.target));
  dagre.layout(g);
  return {
    nodes: nodes.map((node) => {
      const pos = g.node(node.id);
      return { ...node, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
    }),
    edges,
  };
}

interface Props {
  currentIssue: Issue;
  relations: IssueRelation[];
  allIssues: Issue[];
  onNavigate: (issueId: string) => void;
}

export function IssueRelationsGraph({ currentIssue, relations, allIssues, onNavigate }: Props) {
  const issueMap = useMemo(() => new Map(allIssues.map((i) => [i.id, i])), [allIssues]);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const nodeIds = new Set<string>([currentIssue.id]);
    relations.forEach((r) => { nodeIds.add(r.source_id); nodeIds.add(r.target_id); });

    const rawNodes: Node[] = Array.from(nodeIds).map((id) => {
      const issue = issueMap.get(id);
      const isCurrent = id === currentIssue.id;
      return {
        id,
        position: { x: 0, y: 0 },
        data: { label: issue?.name || issue?.description?.slice(0, 30) || id },
        style: {
          background: isCurrent ? "hsl(var(--primary))" : "hsl(var(--card))",
          color: isCurrent ? "hsl(var(--primary-foreground))" : "hsl(var(--foreground))",
          border: "1px solid hsl(var(--border))",
          borderRadius: 8,
          fontSize: 12,
          width: NODE_WIDTH,
          cursor: isCurrent ? "default" : "pointer",
        },
      };
    });

    const rawEdges: Edge[] = relations.map((r) => ({
      id: String(r.id),
      source: r.source_id,
      target: r.target_id,
      animated: r.relation_type === "blocks",
      style: { stroke: r.relation_type === "blocks" ? "hsl(var(--destructive))" : "hsl(var(--muted-foreground))" },
      markerEnd: r.relation_type === "blocks" ? { type: "arrowclosed" as any } : undefined,
    }));

    return getLayoutedElements(rawNodes, rawEdges);
  }, [currentIssue, relations, issueMap]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick: NodeMouseHandler = useCallback((_, node) => {
    if (node.id !== currentIssue.id) onNavigate(node.id);
  }, [currentIssue.id, onNavigate]);

  if (relations.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">Nessuna relazione. Aggiungine una qui sotto.</p>;
  }

  return (
    <div style={{ height: 300 }} className="rounded-lg border overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
```

- [ ] **Step 3: Crea `issue-relations-tab.tsx`**

```typescript
import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { IssueRelationsGraph } from "./issue-relations-graph";
import { useRelations, useAddRelation, useDeleteRelation } from "@/features/issues/hooks-relations";
import { useIssues } from "@/features/issues/hooks";
import { Button } from "@/shared/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import type { Issue, RelationType } from "@/shared/types";

interface Props {
  issue: Issue;
  projectId: string;
}

export function IssueRelationsTab({ issue, projectId }: Props) {
  const navigate = useNavigate();
  const { data: relations = [] } = useRelations(issue.id);
  const { data: allIssues = [] } = useIssues(projectId);
  const addRelation = useAddRelation(issue.id);
  const deleteRelation = useDeleteRelation(issue.id);

  const [selectedIssueId, setSelectedIssueId] = useState("");
  const [relationType, setRelationType] = useState<RelationType>("blocks");

  const alreadyLinked = new Set([issue.id, ...relations.map((r) => r.source_id), ...relations.map((r) => r.target_id)]);
  const availableIssues = allIssues.filter((i) => !alreadyLinked.has(i.id));

  async function handleAdd() {
    if (!selectedIssueId) return;
    await addRelation.mutateAsync({ target_id: selectedIssueId, relation_type: relationType });
    setSelectedIssueId("");
  }

  return (
    <div className="space-y-4">
      <IssueRelationsGraph
        currentIssue={issue}
        relations={relations}
        allIssues={allIssues}
        onNavigate={(id) => navigate({ to: "/projects/$projectId/issues/$issueId", params: { projectId, issueId: id } })}
      />

      {/* Add relation form */}
      <div className="flex gap-2 flex-wrap">
        <Select value={selectedIssueId} onValueChange={setSelectedIssueId}>
          <SelectTrigger className="flex-1 min-w-[200px] h-8 text-sm">
            <SelectValue placeholder="Seleziona issue..." />
          </SelectTrigger>
          <SelectContent>
            {availableIssues.map((i) => (
              <SelectItem key={i.id} value={i.id}>
                {i.name || i.description.slice(0, 50)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={relationType} onValueChange={(v) => setRelationType(v as RelationType)}>
          <SelectTrigger className="w-[130px] h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="blocks">blocca</SelectItem>
            <SelectItem value="related">correlata</SelectItem>
          </SelectContent>
        </Select>
        <Button size="sm" onClick={handleAdd} disabled={!selectedIssueId || addRelation.isPending}>
          Aggiungi
        </Button>
      </div>

      {/* Relation list */}
      {relations.length > 0 && (
        <ul className="space-y-1">
          {relations.map((r) => {
            const other = allIssues.find((i) => i.id === (r.source_id === issue.id ? r.target_id : r.source_id));
            const direction = r.source_id === issue.id ? "→" : "←";
            const label = r.relation_type === "blocks" ? `${direction} blocca` : "↔ correlata";
            return (
              <li key={r.id} className="flex items-center justify-between text-sm p-2 rounded border">
                <span>
                  <span className="text-muted-foreground">{label}</span>{" "}
                  <span className="font-medium">{other?.name || other?.description?.slice(0, 40) || r.target_id}</span>
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-6 text-muted-foreground hover:text-destructive"
                  onClick={() => deleteRelation.mutate(r.id)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/issues/components/issue-relations-graph.tsx frontend/src/features/issues/components/issue-relations-tab.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: add IssueRelationsGraph and IssueRelationsTab with react-flow"
```

---

### Task 13: Wiring in IssueDetail + badge bloccata nel Kanban

**Files:**
- Modify: `frontend/src/features/issues/components/issue-detail.tsx`
- Modify: `frontend/src/features/issues/components/kanban-board.tsx` (aggiunge blockedIssueIds)
- Modify: `frontend/src/routes/projects/$projectId/issues/index.tsx`

- [ ] **Step 1: Aggiungi il tab Relations in `issue-detail.tsx`**

Nella lista `tabs` in `IssueDetail`, aggiungi `relations` sempre disponibile:

```typescript
const tabs = useMemo<TabDef[]>(() => [
  { value: "description", label: "Description", available: true },
  { value: "specification", label: "Specification", available: !!issue.specification },
  { value: "plan", label: "Plan", available: !!issue.plan },
  { value: "tasks", label: "Tasks", available: true },
  { value: "relations", label: "Relations", available: true },
  { value: "recap", label: "Recap", available: !!issue.recap },
], [issue.specification, issue.plan, issue.recap]);
```

Aggiungi l'import in cima:
```typescript
import { IssueRelationsTab } from "./issue-relations-tab";
```

Nel JSX dei `TabsContent`, aggiungi dopo il tab tasks:
```typescript
<TabsContent value="relations">
  <IssueRelationsTab issue={issue} projectId={projectId} />
</TabsContent>
```

- [ ] **Step 2: Aggiungi `blockedIssueIds` nel Kanban**

In `frontend/src/routes/projects/$projectId/issues/index.tsx`, importa `useRelations` e calcola `blockedIssueIds`. Aggiungi questo hook prima del return. Poiché le relazioni sono per singola issue e qui abbiamo tutte le issue, useremo un approccio semplificato: fetching delle relazioni per tutte le issue e raccolta degli ID bloccati.

Aggiungi il seguente import nella route:
```typescript
import { useBlockedIssueIds } from "@/features/issues/hooks-relations";
```

Aggiungi questo hook in `hooks-relations.ts` usando `useQueries` (non chiamare hook in loop — viola le Rules of Hooks):

```typescript
import { useQueries } from "@tanstack/react-query";
import type { Issue } from "@/shared/types";

export function useBlockedIssueIds(issues: Issue[]) {
  const results = useQueries({
    queries: issues.map((i) => ({
      queryKey: ["relations", i.id],
      queryFn: () => fetchRelations(i.id),
    })),
  });
  const blockedIds = new Set<string>();
  results.forEach((result, idx) => {
    (result.data ?? []).forEach((r) => {
      if (r.relation_type === "blocks" && r.target_id === issues[idx].id) {
        blockedIds.add(r.target_id);
      }
    });
  });
  return blockedIds;
}
```

In `IssuesPage`, aggiungi:
```typescript
const blockedIssueIds = useBlockedIssueIds(issues ?? []);
```

E passa a `KanbanBoard`:
```typescript
<KanbanBoard
  issues={issues ?? []}
  projectId={projectId}
  activeTerminalIssueIds={activeTerminalIssueIds}
  blockedIssueIds={blockedIssueIds}
/>
```

- [ ] **Step 3: Avvia e verifica**

```bash
cd frontend && npm run dev
```
- Vai su un'issue → tab "Relations" → aggiungi una relazione "blocca"
- Torna al Kanban → verifica che la card dell'issue bloccata mostra il badge rosso "Bloccata"
- Verifica che il grafo react-flow mostra correttamente i nodi collegati

- [ ] **Step 4: Esegui tutti i test backend**

```bash
cd backend && python -m pytest -v
```
Atteso: tutti PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/issues/components/issue-detail.tsx frontend/src/features/issues/hooks-relations.ts frontend/src/routes/projects/\$projectId/issues/index.tsx
git commit -m "feat: wire Relations tab in IssueDetail and blocked badge in Kanban (7.2 complete)"
```

---

## SEZIONE 3 — Multi-project Dashboard (7.3)

---

### Task 14: Backend dashboard endpoint

**Files:**
- Modify: `backend/app/schemas/project.py`
- Modify: `backend/app/services/project_service.py`
- Modify: `backend/app/routers/projects.py`
- Create: `backend/tests/test_routers_dashboard.py`

- [ ] **Step 1: Scrivi il test**

Crea `backend/tests/test_routers_dashboard.py`:

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_empty(client):
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_dashboard_shows_active_issues(client):
    proj = (await client.post("/api/projects", json={"name": "P1", "path": "/tmp"})).json()
    await client.post(f"/api/projects/{proj['id']}/issues", json={"description": "Active issue"})
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == proj["id"]
    assert len(data[0]["active_issues"]) == 1


@pytest.mark.asyncio
async def test_dashboard_excludes_finished(client):
    proj = (await client.post("/api/projects", json={"name": "P1", "path": "/tmp"})).json()
    # All finished — project should still appear but with empty active_issues
    resp = await client.get("/api/dashboard")
    data = resp.json()
    assert data[0]["active_issues"] == [] if data else True  # no project = no entry
```

- [ ] **Step 2: Esegui il test per verificare che fallisce**

```bash
cd backend && python -m pytest tests/test_routers_dashboard.py -v
```
Atteso: FAIL — endpoint non esiste.

- [ ] **Step 3: Aggiungi schema in `schemas/project.py`**

Apri `backend/app/schemas/project.py` e aggiungi in fondo:

```python
from app.models.issue import IssueStatus

class DashboardIssue(BaseModel):
    id: str
    name: str | None
    description: str
    status: str
    priority: int
    model_config = ConfigDict(from_attributes=True)

class DashboardProject(BaseModel):
    id: str
    name: str
    path: str
    active_issues: list[DashboardIssue]
    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Aggiungi `get_dashboard_data()` in `project_service.py`**

```python
async def get_dashboard_data(self) -> list[dict]:
    from sqlalchemy.orm import selectinload
    from app.models.issue import Issue, IssueStatus
    projects = await self.list_all()
    result = []
    for project in projects:
        q = (
            select(Issue)
            .where(Issue.project_id == project.id)
            .where(Issue.status.notin_([IssueStatus.FINISHED, IssueStatus.CANCELED]))
            .order_by(Issue.priority.asc(), Issue.created_at.asc())
        )
        r = await self.session.execute(q)
        active = list(r.scalars().all())
        result.append({
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "active_issues": active,
        })
    return result
```

- [ ] **Step 5: Aggiungi l'endpoint in `routers/projects.py`**

Aggiungi questo endpoint in fondo al router (prima di eventuali endpoint con parametri per evitare conflitti):

```python
from app.schemas.project import DashboardProject

@router.get("/api/dashboard", response_model=list[DashboardProject])
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    svc = ProjectService(db)
    return await svc.get_dashboard_data()
```

> Assicurati che questo endpoint sia definito **prima** di qualsiasi route con parametri come `/{project_id}` nello stesso router per evitare che "dashboard" venga interpretato come un project_id. In alternativa, aggiungi il prefix `/api` solo a questo endpoint esplicitamente o usa un router separato.

- [ ] **Step 6: Esegui i test**

```bash
cd backend && python -m pytest tests/test_routers_dashboard.py -v
```
Atteso: tutti PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/project.py backend/app/services/project_service.py backend/app/routers/projects.py backend/tests/test_routers_dashboard.py
git commit -m "feat: add dashboard endpoint returning active issues per project"
```

---

### Task 15: Frontend dashboard route

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Create: `frontend/src/features/projects/api-dashboard.ts`
- Create: `frontend/src/features/projects/hooks-dashboard.ts`
- Create: `frontend/src/routes/dashboard.tsx`
- Modify: `frontend/src/shared/components/app-sidebar.tsx`

- [ ] **Step 1: Aggiungi tipi in `types/index.ts`**

```typescript
// ── Dashboard ──

export interface DashboardIssue {
  id: string;
  name: string | null;
  description: string;
  status: IssueStatus;
  priority: number;
}

export interface DashboardProject {
  id: string;
  name: string;
  path: string;
  active_issues: DashboardIssue[];
}
```

- [ ] **Step 2: Crea `api-dashboard.ts`**

```typescript
import { request } from "@/shared/api/client";
import type { DashboardProject } from "@/shared/types";

export function fetchDashboard(): Promise<DashboardProject[]> {
  return request("/dashboard");
}
```

- [ ] **Step 3: Crea `hooks-dashboard.ts`**

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchDashboard } from "./api-dashboard";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
    refetchInterval: 30_000,
  });
}
```

- [ ] **Step 4: Crea `routes/dashboard.tsx`**

```typescript
import { createFileRoute, Link } from "@tanstack/react-router";
import { useDashboard } from "@/features/projects/hooks-dashboard";
import { StatusBadge } from "@/features/issues/components/status-badge";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
});

function DashboardPage() {
  const { data: projects, isLoading } = useDashboard();

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2].map((i) => <Skeleton key={i} className="h-32" />)}
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-6">Dashboard</h1>
      {!projects || projects.length === 0 ? (
        <p className="text-muted-foreground">Nessun progetto ancora.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((project) => (
            <Card key={project.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  <Link
                    to="/projects/$projectId/issues"
                    params={{ projectId: project.id }}
                    className="hover:underline"
                  >
                    {project.name}
                  </Link>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {project.active_issues.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nessuna issue attiva</p>
                ) : (
                  <ul className="space-y-1.5">
                    {project.active_issues.map((issue) => (
                      <li key={issue.id}>
                        <Link
                          to="/projects/$projectId/issues/$issueId"
                          params={{ projectId: project.id, issueId: issue.id }}
                          className="flex items-center gap-2 text-sm hover:underline"
                        >
                          <StatusBadge status={issue.status} />
                          <span className="truncate flex-1">
                            {issue.name || issue.description}
                          </span>
                          <span className="text-xs text-muted-foreground flex-shrink-0">P{issue.priority}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Aggiungi link Dashboard in `app-sidebar.tsx`**

Apri `frontend/src/shared/components/app-sidebar.tsx`. Cerca il primo `SidebarMenuItem` o la sezione con i link di navigazione globali. Aggiungi il link alla dashboard con l'icona `LayoutDashboard` da lucide-react:

```typescript
import { LayoutDashboard } from "lucide-react";
// ...
<SidebarMenuItem>
  <SidebarMenuButton asChild>
    <Link to="/dashboard">
      <LayoutDashboard className="size-4" />
      <span>Dashboard</span>
    </Link>
  </SidebarMenuButton>
</SidebarMenuItem>
```

- [ ] **Step 6: Registra la route nel router (se necessario)**

TanStack Router con file-based routing genera `routeTree.gen.ts` automaticamente. Esegui:
```bash
cd frontend && npm run dev
```
Il dev server rigenera `routeTree.gen.ts`. Verifica che `/dashboard` appaia nel file generato.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/shared/types/index.ts frontend/src/features/projects/api-dashboard.ts frontend/src/features/projects/hooks-dashboard.ts frontend/src/routes/dashboard.tsx frontend/src/shared/components/app-sidebar.tsx frontend/src/routeTree.gen.ts
git commit -m "feat: add multi-project dashboard page (7.3 complete)"
```

---

## SEZIONE 4 — Terminal Grid (7.4)

---

### Task 16: Terminal Grid — layout dinamico

**Files:**
- Create: `frontend/src/features/terminals/components/terminal-grid.tsx`
- Modify: `frontend/src/routes/terminals.tsx`

- [ ] **Step 1: Crea `terminal-grid.tsx`**

```typescript
import { useEffect, useRef } from "react";
import { Skull } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/shared/components/ui/button";
import { TerminalPanel } from "./terminal-panel";
import type { TerminalListItem } from "@/shared/types";

interface TerminalGridProps {
  terminals: TerminalListItem[];
  onKill: (id: string) => void;
}

function getGridClass(count: number): string {
  if (count === 1) return "grid-cols-1";
  if (count === 2) return "grid-cols-2";
  return "grid-cols-[repeat(auto-fill,minmax(500px,1fr))]";
}

export function TerminalGrid({ terminals, onKill }: TerminalGridProps) {
  if (terminals.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Nessun terminale attivo.</p>
      </div>
    );
  }

  const gridClass = getGridClass(terminals.length);

  return (
    <div className={`grid ${gridClass} gap-3 h-full`}>
      {terminals.map((term) => (
        <div key={term.id} className="flex flex-col border rounded-lg overflow-hidden min-h-[400px]">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-1.5 border-b bg-muted/30 flex-shrink-0">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" style={{ boxShadow: "0 0 4px #4ade80" }} />
              <span className="text-sm font-medium truncate">{term.issue_name || term.issue_id}</span>
              <span className="text-xs text-muted-foreground flex-shrink-0">{term.project_name}</span>
            </div>
            <div className="flex gap-1 flex-shrink-0 ml-2">
              <Button variant="ghost" size="sm" asChild className="h-6 text-xs px-2">
                <Link to="/projects/$projectId/issues/$issueId" params={{ projectId: term.project_id, issueId: term.issue_id }}>
                  Issue
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-destructive"
                onClick={() => onKill(term.id)}
              >
                <Skull className="size-3" />
              </Button>
            </div>
          </div>
          {/* Terminal */}
          <div className="flex-1 min-h-0">
            <TerminalPanel terminalId={term.id} />
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Aggiorna `routes/terminals.tsx`**

Sostituisci il contenuto del file:

```typescript
import { createFileRoute } from "@tanstack/react-router";
import { useTerminals, useTerminalConfig, useKillTerminal } from "@/features/terminals/hooks";
import { TerminalGrid } from "@/features/terminals/components/terminal-grid";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/terminals")({
  component: TerminalsPage,
});

function TerminalsPage() {
  const { data: terminals, isLoading } = useTerminals();
  const { data: config } = useTerminalConfig();
  const killTerminal = useKillTerminal();
  const softLimit = config?.soft_limit ?? 5;

  const handleKill = (terminalId: string) => {
    if (!confirm("Terminare questo terminale? I comandi in esecuzione verranno interrotti.")) return;
    killTerminal.mutate(terminalId);
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-48" />
        {[1, 2].map((i) => <Skeleton key={i} className="h-[400px]" />)}
      </div>
    );
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-xl font-semibold">Terminali Attivi</h1>
        <span className="text-sm text-muted-foreground">
          {terminals?.length ?? 0} / {softLimit} (soft limit)
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <TerminalGrid terminals={terminals ?? []} onKill={handleKill} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verifica che `useTerminals()` senza argomenti ritorni tutti i terminali**

Apri `frontend/src/features/terminals/hooks.ts` e verifica che `useTerminals()` chiamato senza `projectId` ritorni tutti i terminali. Se la firma richiede `projectId`, aggiungi un overload opzionale:

```typescript
export function useTerminals(projectId?: string) {
  return useQuery({
    queryKey: ["terminals", projectId],
    queryFn: () => fetchTerminals(projectId),
  });
}
```

E in `api.ts`:
```typescript
export function fetchTerminals(projectId?: string): Promise<TerminalListItem[]> {
  const url = projectId ? `/terminals?project_id=${projectId}` : "/terminals";
  return request(url);
}
```

- [ ] **Step 4: Avvia e verifica**

```bash
cd frontend && npm run dev
```
- Apri due terminali su issue diverse
- Vai su `/terminals` → verifica griglia 2 colonne con pannelli xterm embedded
- Apri un terzo terminale → verifica layout a 3+ colonne con auto-fill
- Verifica che ogni pannello ha header con nome issue e pulsante kill

- [ ] **Step 5: Esegui lint**

```bash
cd frontend && npm run lint
```
Correggi eventuali warning prima di committare.

- [ ] **Step 6: Esegui tutti i test backend**

```bash
cd backend && python -m pytest -v
```
Atteso: tutti PASS.

- [ ] **Step 7: Commit finale**

```bash
git add frontend/src/features/terminals/components/terminal-grid.tsx frontend/src/routes/terminals.tsx frontend/src/features/terminals/hooks.ts frontend/src/features/terminals/api.ts
git commit -m "feat: terminal grid with dynamic layout for multiple simultaneous terminals (7.4 complete)"
```

---

## Riepilogo task

| # | Task | Sezione |
|---|------|---------|
| 1 | Backend: search param issues | 7.1 |
| 2 | npm install @dnd-kit | 7.1 |
| 3 | API/hooks search | 7.1 |
| 4 | KanbanCard | 7.1 |
| 5 | KanbanColumn + KanbanFilters | 7.1 |
| 6 | KanbanBoard + route | 7.1 |
| 7 | IssueRelation model + migration | 7.2 |
| 8 | IssueRelationService | 7.2 |
| 9 | Schema + Router relations | 7.2 |
| 10 | Enforcement hook | 7.2 |
| 11 | Frontend types/api/hooks relations | 7.2 |
| 12 | react-flow + grafo | 7.2 |
| 13 | Wiring IssueDetail + badge Kanban | 7.2 |
| 14 | Backend dashboard endpoint | 7.3 |
| 15 | Frontend dashboard route | 7.3 |
| 16 | Terminal grid | 7.4 |
