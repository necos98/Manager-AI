# Frontend Refactor & UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medium-effort refactors that raise frontend maintainability and polish backend input discipline: split the `IssueDetail` mega-component, lazy-load admin routes, pass a mobile responsive audit, type-safe WebSocket events, introduce i18n, enforce stricter Pydantic validation, and bound activity-log growth.

**Architecture:** Independent phases. Mix of frontend (React 19 / TanStack Router / Tailwind) and backend (FastAPI / Pydantic / SQLAlchemy async). Visual changes manually verified in the browser; logic changes covered by tests.

**Tech Stack:** React 19, TanStack Router, TanStack Query, Tailwind CSS 4, shadcn/radix-ui, `i18next` + `react-i18next`, Python 3.11, FastAPI, Pydantic v2, SQLAlchemy async (SQLite/aiosqlite), pytest-asyncio (`asyncio_mode = "auto"`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/shared/context/event-context.tsx` | Modify | Discriminated union for `WsEventData` |
| `frontend/src/shared/types/events.ts` | Create | Event payload type definitions |
| `frontend/src/features/issues/components/issue-detail.tsx` | Split | Shrink to composition root |
| `frontend/src/features/issues/components/issue-header.tsx` | Create | Title, priority, description inline edit |
| `frontend/src/features/issues/components/issue-tabs.tsx` | Create | Description/Spec/Plan/Tasks/Relations/Recap tab shell |
| `frontend/src/features/issues/components/issue-actions.tsx` | Create | Accept/Cancel/Complete/Delete bar |
| `frontend/src/features/issues/components/issue-detail-context.tsx` | Create | Context provider to avoid prop drilling |
| `frontend/src/routes/library.tsx` | Modify | `React.lazy` |
| `frontend/src/routes/projects/$projectId/commands.tsx` | Modify | `React.lazy` |
| `frontend/src/routes/projects/$projectId/variables.tsx` | Modify | `React.lazy` |
| `frontend/src/routes/projects/$projectId/library.tsx` | Modify | `React.lazy` |
| `frontend/src/features/issues/components/kanban-board.tsx` | Modify | Mobile stacked layout |
| `frontend/src/features/terminals/components/terminal-panel.tsx` | Modify | Touch-friendly resize on narrow screens |
| `frontend/src/i18n.ts` | Create | `i18next` bootstrap |
| `frontend/src/locales/en.json` | Create | English strings |
| `frontend/src/locales/it.json` | Create | Italian strings |
| `frontend/src/main.tsx` | Modify | Import `./i18n` before render |
| `backend/app/schemas/issue.py` | Modify | Stricter `IssueCreate`, length limits, allowed chars |
| `backend/app/schemas/project.py` | Modify | Validate `path` absolute, `name` non-empty |
| `backend/app/schemas/terminal.py` | Modify | Validate cols/rows bounds |
| `backend/app/services/activity_service.py` | Modify | Retention policy purge |
| `backend/app/config.py` | Modify | `activity_retention_days: int = 90` |
| `backend/app/main.py` | Modify | Scheduled retention job on startup |
| `backend/tests/test_schemas_issue.py` | Create | Validation tests |
| `backend/tests/test_activity_retention.py` | Create | Retention purge tests |

---

## Phase 1: Discriminated Union for `WsEventData`

**Why:** `event-context.tsx:6-19` types every event field as optional, so every consumer has to guard every access. A discriminated union on `type` gives full type narrowing.

### Task 1.1: Extract event types

**Files:**
- Create: `frontend/src/shared/types/events.ts`

- [ ] **Step 1: Enumerate every emitted `type`**

```bash
cd backend && grep -rn '"type":' app/services/event_service.py app/hooks/registry.py app/services/rag_service.py app/mcp/server.py
```
Expected types (from backend): `hook_started`, `hook_completed`, `hook_failed`, `issue_status_changed`, `issue_content_updated`, `issue_created`, `issue_deleted`, `task_updated`, `task_status_updated`, `terminal_created`, `terminal_closed`, `project_updated`, `embedding_started`, `embedding_completed`, `embedding_failed`, `notification`.

- [ ] **Step 2: Write the union**

```ts
// frontend/src/shared/types/events.ts
export type WsEvent =
  | HookStartedEvent
  | HookCompletedEvent
  | HookFailedEvent
  | IssueStatusChangedEvent
  | IssueContentUpdatedEvent
  | IssueCreatedEvent
  | IssueDeletedEvent
  | TaskUpdatedEvent
  | TaskStatusUpdatedEvent
  | TerminalCreatedEvent
  | TerminalClosedEvent
  | ProjectUpdatedEvent
  | EmbeddingStartedEvent
  | EmbeddingCompletedEvent
  | EmbeddingFailedEvent
  | NotificationEvent;

export interface HookStartedEvent {
  type: "hook_started";
  project_id: string;
  issue_id: string;
  issue_name: string;
  project_name: string;
  hook_name: string;
  hook_description: string;
  timestamp: string;
}

export interface HookCompletedEvent {
  type: "hook_completed";
  project_id: string;
  issue_id: string;
  issue_name: string;
  project_name: string;
  hook_name: string;
  output: string | null;
  timestamp: string;
}

export interface HookFailedEvent {
  type: "hook_failed";
  project_id: string;
  issue_id: string;
  issue_name: string;
  project_name: string;
  hook_name: string;
  error: string;
  timestamp: string;
}

export interface IssueStatusChangedEvent {
  type: "issue_status_changed";
  project_id: string;
  issue_id: string;
  new_status: "New" | "Reasoning" | "Planned" | "Accepted" | "Finished" | "Canceled";
}

export interface IssueContentUpdatedEvent {
  type: "issue_content_updated";
  project_id: string;
  issue_id: string;
  content_type: "specification" | "plan" | "name" | "recap" | "description";
}

export interface IssueCreatedEvent {
  type: "issue_created";
  project_id: string;
  issue_id: string;
  issue_name: string;
}

export interface IssueDeletedEvent {
  type: "issue_deleted";
  project_id: string;
  issue_id: string;
}

export interface TaskUpdatedEvent {
  type: "task_updated";
  project_id: string;
  issue_id: string;
  task_id: string;
}

export interface TaskStatusUpdatedEvent {
  type: "task_status_updated";
  project_id: string;
  issue_id: string;
  task_id: string;
  new_status: "Pending" | "In Progress" | "Completed";
}

export interface TerminalCreatedEvent {
  type: "terminal_created";
  project_id: string;
  terminal_id: string;
}

export interface TerminalClosedEvent {
  type: "terminal_closed";
  project_id: string;
  terminal_id: string;
}

export interface ProjectUpdatedEvent {
  type: "project_updated";
  project_id: string;
}

export interface EmbeddingStartedEvent {
  type: "embedding_started";
  project_id: string;
  source_type: "file" | "issue" | "codebase" | "codebase_file";
  source_id: string;
}

export interface EmbeddingCompletedEvent {
  type: "embedding_completed";
  project_id: string;
  source_type: "file" | "issue" | "codebase" | "codebase_file";
  source_id: string;
}

export interface EmbeddingFailedEvent {
  type: "embedding_failed";
  project_id: string;
  source_type: "file" | "issue" | "codebase" | "codebase_file";
  source_id: string;
  error: string;
}

export interface NotificationEvent {
  type: "notification";
  project_id: string;
  issue_id?: string;
  title: string;
  message: string;
}
```

### Task 1.2: Replace `WsEventData` usage

**Files:**
- Modify: `frontend/src/shared/context/event-context.tsx`

- [ ] **Step 1: Replace the loose type**

```ts
// frontend/src/shared/context/event-context.tsx
import type { WsEvent } from "@/shared/types/events";
export type { WsEvent } from "@/shared/types/events";

type EventSubscriber = (event: WsEvent) => void;

// Parse guard:
function parseWsEvent(raw: unknown): WsEvent | null {
  if (typeof raw !== "object" || raw === null) return null;
  const t = (raw as { type?: unknown }).type;
  if (typeof t !== "string") return null;
  return raw as WsEvent;
}
```

- [ ] **Step 2: Switch on `event.type` with exhaustiveness**

```ts
function buildToastContent(event: WsEvent): ToastContent | null {
  switch (event.type) {
    case "hook_started": return { ... };
    case "hook_completed": return { ... };
    case "issue_status_changed": return { ... };
    // ... one case per variant
    default: {
      const _exhaustive: never = event;
      return null;
    }
  }
}
```

- [ ] **Step 3: Run type check**

```bash
cd frontend && npx tsc --noEmit
```
Fix any narrowing issues revealed.

- [ ] **Step 4: Manual verify** — trigger every event type in dev and confirm toasts still show correctly.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/types/events.ts frontend/src/shared/context/event-context.tsx
git commit -m "refactor(events): replace WsEventData with discriminated union"
```

---

## Phase 2: Split `IssueDetail`

**Why:** `issue-detail.tsx` exceeds 300 lines and mixes six domains (header, tabs, relations, feedback, actions, terminal panel). A local context + focused sub-components eliminates prop drilling and makes each piece individually testable.

### Task 2.1: Create context provider

**Files:**
- Create: `frontend/src/features/issues/components/issue-detail-context.tsx`

- [ ] **Step 1: Provider + hook**

```tsx
// frontend/src/features/issues/components/issue-detail-context.tsx
import { createContext, useContext, type ReactNode } from "react";
import type { Issue } from "@/shared/types";

interface IssueDetailCtxValue {
  projectId: string;
  issueId: string;
  issue: Issue;
  refetch: () => void;
}

const Ctx = createContext<IssueDetailCtxValue | null>(null);

export function IssueDetailProvider({
  value,
  children,
}: {
  value: IssueDetailCtxValue;
  children: ReactNode;
}) {
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useIssueDetail(): IssueDetailCtxValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useIssueDetail must be used inside IssueDetailProvider");
  return v;
}
```

### Task 2.2: Extract `IssueHeader`

**Files:**
- Create: `frontend/src/features/issues/components/issue-header.tsx`

- [ ] **Step 1: Move the title/priority/description inline-edit block**

Copy the relevant JSX (roughly the first card in `issue-detail.tsx`) into the new file, replace prop-receipt with `useIssueDetail()`, export as default.

```tsx
// frontend/src/features/issues/components/issue-header.tsx
import { useIssueDetail } from "./issue-detail-context";
import { InlineEditField } from "./inline-edit-field";
// ... other imports

export default function IssueHeader() {
  const { issue, projectId, issueId } = useIssueDetail();
  // ... the existing header JSX
}
```

### Task 2.3: Extract `IssueTabs`

**Files:**
- Create: `frontend/src/features/issues/components/issue-tabs.tsx`

- [ ] **Step 1: Move the `<Tabs>` block**

Preserve each tab's content by moving it into its own component file if still oversized (`issue-tab-specification.tsx`, `issue-tab-plan.tsx`, etc.). Each tab reads from `useIssueDetail()`.

### Task 2.4: Extract `IssueActions`

**Files:**
- Create: `frontend/src/features/issues/components/issue-actions.tsx`

- [ ] **Step 1: Move the action-button row**

Include Accept, Cancel, Complete, Delete, and any confirm dialogs that belong to those actions.

### Task 2.5: Recompose `IssueDetail`

**Files:**
- Modify: `frontend/src/features/issues/components/issue-detail.tsx`

- [ ] **Step 1: Shrink to composition**

```tsx
export function IssueDetail({ projectId, issueId }: { projectId: string; issueId: string }) {
  const { data: issue, refetch } = useIssue(projectId, issueId);
  if (!issue) return <Skeleton className="h-[80vh] w-full" />;

  return (
    <IssueDetailProvider value={{ projectId, issueId, issue, refetch }}>
      <div className="flex flex-col gap-4 p-4 md:p-6">
        <IssueHeader />
        <IssueActions />
        <IssueTabs />
        <IssueRelationsPanel />
        <IssueFeedbackPanel />
      </div>
    </IssueDetailProvider>
  );
}
```

- [ ] **Step 2: Manual verify**

```bash
cd frontend && npm run dev
```
Open every tab, edit title, change priority, toggle description, add/remove task, relation, feedback, and run Accept → Complete flow. Everything must still work.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/issues/components/
git commit -m "refactor(issues): split IssueDetail into context + focused sub-components"
```

---

## Phase 3: Lazy-Load Admin Routes

**Why:** `library`, `commands`, `variables`, and project-scoped `library` are rarely opened but ship in the initial bundle. Lazy-loading them trims TTI for the hot path.

### Task 3.1: Convert each route

**Files:**
- Modify: `frontend/src/routes/library.tsx`
- Modify: `frontend/src/routes/projects/$projectId/commands.tsx`
- Modify: `frontend/src/routes/projects/$projectId/variables.tsx`
- Modify: `frontend/src/routes/projects/$projectId/library.tsx`

- [ ] **Step 1: Use TanStack Router's built-in lazy pattern**

```tsx
// frontend/src/routes/library.tsx
import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/library")({
  component: lazyRouteComponent(() => import("@/features/library/components/library-page"), "LibraryPage"),
});
```

Repeat for each of the four files, pointing at the page component.

- [ ] **Step 2: Add a Suspense fallback at the root**

```tsx
// frontend/src/routes/__root.tsx  (inside main)
<Suspense fallback={<div className="p-6"><Skeleton className="h-8 w-48" /></div>}>
  <Outlet />
</Suspense>
```

- [ ] **Step 3: Build and inspect bundle**

```bash
cd frontend && npm run build
```
Confirm the 4 routes produce their own chunks (check `dist/assets/`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/
git commit -m "perf(ui): lazy-load admin routes (library, commands, variables)"
```

---

## Phase 4: Mobile Responsive Pass

**Why:** Audit found 2-3 `md:` breakpoints only. Target viewport: 375 px (iPhone SE). Focus: project list grid, issue list, kanban board, issue detail, terminal panel.

### Task 4.1: Kanban stacked layout

**Files:**
- Modify: `frontend/src/features/issues/components/kanban-board.tsx`

- [ ] **Step 1: Swap horizontal scroll for stacked accordion under `md:`**

```tsx
<div className="flex flex-col gap-4 md:flex-row md:overflow-x-auto">
  {columns.map((column) => (
    <Collapsible key={column.status} defaultOpen={column.status === "Accepted"}
                 className="md:w-80 md:shrink-0">
      <CollapsibleTrigger className="md:hidden flex w-full items-center justify-between rounded-md border p-3">
        <span>{column.status} ({column.items.length})</span>
        <ChevronDown className="h-4 w-4" />
      </CollapsibleTrigger>
      <CollapsibleContent className="md:hidden">
        {/* cards */}
      </CollapsibleContent>
      <div className="hidden md:block">
        {/* desktop cards */}
      </div>
    </Collapsible>
  ))}
</div>
```

### Task 4.2: Issue detail — responsive split

**Files:**
- Modify: `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`

- [ ] **Step 1: Collapse terminal panel under `md:`**

```tsx
<ResizablePanelGroup direction="horizontal" className="hidden md:flex">
  {/* existing split */}
</ResizablePanelGroup>

<div className="md:hidden">
  <IssueDetail projectId={projectId} issueId={issueId} />
  {terminalIds.length > 0 && (
    <Sheet>
      <SheetTrigger className="fixed bottom-4 right-4 rounded-full bg-primary p-4 text-primary-foreground shadow-lg">
        <Terminal className="h-5 w-5" />
      </SheetTrigger>
      <SheetContent side="bottom" className="h-[80vh]">
        <TerminalPanel terminalId={terminalIds[0]} />
      </SheetContent>
    </Sheet>
  )}
</div>
```

### Task 4.3: Touch-friendly controls

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx`

- [ ] **Step 1: Enlarge hit targets under 768 px**

Replace `size="sm"` buttons in the toolbar with `size="icon"` at `md:size-sm`, ensuring 44 × 44 px minimum on touch.

- [ ] **Step 2: Manual verify on 375 × 667 viewport** in Chrome DevTools device mode.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/issues/components/kanban-board.tsx frontend/src/routes/projects/$projectId/issues/$issueId.tsx frontend/src/features/terminals/components/terminal-panel.tsx
git commit -m "feat(ui): mobile-responsive kanban, issue detail, terminal"
```

---

## Phase 5: i18n (English Default + Italian Track)

**Why:** Project mixes Italian strings ("Nessun terminale attivo") into an otherwise English UI. Pick English as the default and ship Italian as an optional locale.

### Task 5.1: Bootstrap i18next

**Files:**
- Create: `frontend/src/i18n.ts`
- Create: `frontend/src/locales/en.json`
- Create: `frontend/src/locales/it.json`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Install**

```bash
cd frontend && npm install i18next react-i18next i18next-browser-languagedetector
```

- [ ] **Step 2: Configure**

```ts
// frontend/src/i18n.ts
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./locales/en.json";
import it from "./locales/it.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, it: { translation: it } },
    fallbackLng: "en",
    interpolation: { escapeValue: false },
  });

export default i18n;
```

- [ ] **Step 3: Seed locale files with a flat key-per-string map**

```json
// frontend/src/locales/en.json
{
  "terminals.empty": "No active terminals",
  "issue.action.accept": "Accept",
  "issue.action.cancel": "Cancel",
  "issue.action.complete": "Complete",
  "issue.tab.description": "Description",
  "issue.tab.specification": "Specification",
  "issue.tab.plan": "Plan",
  "issue.tab.tasks": "Tasks",
  "issue.tab.relations": "Relations",
  "issue.tab.recap": "Recap",
  "common.save": "Save",
  "common.cancel": "Cancel",
  "common.retry": "Retry",
  "common.loading": "Loading…"
}
```

```json
// frontend/src/locales/it.json
{
  "terminals.empty": "Nessun terminale attivo",
  "issue.action.accept": "Accetta",
  "issue.action.cancel": "Annulla",
  "issue.action.complete": "Completa",
  "issue.tab.description": "Descrizione",
  "issue.tab.specification": "Specifica",
  "issue.tab.plan": "Piano",
  "issue.tab.tasks": "Task",
  "issue.tab.relations": "Relazioni",
  "issue.tab.recap": "Riepilogo",
  "common.save": "Salva",
  "common.cancel": "Annulla",
  "common.retry": "Riprova",
  "common.loading": "Caricamento…"
}
```

- [ ] **Step 4: Import before render**

```tsx
// frontend/src/main.tsx
import "./i18n";
// ... existing imports
```

### Task 5.2: Migrate strings

**Files:**
- Modify: every component with user-facing literals

- [ ] **Step 1: Grep for Italian substrings to find the debt**

```bash
cd frontend && grep -rnE "Nessun|Aggiungi|Salva|Elimina|Crea nuovo" src/
```

- [ ] **Step 2: Replace with `useTranslation`**

```tsx
import { useTranslation } from "react-i18next";

function MyComponent() {
  const { t } = useTranslation();
  return <p>{t("terminals.empty")}</p>;
}
```

- [ ] **Step 3: Add a language switch in Settings**

```tsx
// frontend/src/features/settings/components/language-select.tsx
import { useTranslation } from "react-i18next";

export function LanguageSelect() {
  const { i18n } = useTranslation();
  return (
    <Select value={i18n.language.slice(0, 2)} onValueChange={(v) => i18n.changeLanguage(v)}>
      <SelectTrigger className="w-40" aria-label="Language">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="en">English</SelectItem>
        <SelectItem value="it">Italiano</SelectItem>
      </SelectContent>
    </Select>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat(i18n): add English + Italian locales via i18next"
```

---

## Phase 6: Stricter Pydantic Validation

**Why:** Schemas accept unbounded strings and loose `path` fields. Tighten where an attacker-controlled value is saved to disk, interpolated into a prompt, or passed to a subprocess.

### Task 6.1: Tighten `IssueCreate`

**Files:**
- Modify: `backend/app/schemas/issue.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_schemas_issue.py
import pytest
from pydantic import ValidationError
from app.schemas.issue import IssueCreate


def test_name_must_be_bounded():
    with pytest.raises(ValidationError):
        IssueCreate(name="x" * 300, description="ok")

def test_description_required():
    with pytest.raises(ValidationError):
        IssueCreate(description="")

def test_description_bounded():
    with pytest.raises(ValidationError):
        IssueCreate(description="x" * 100_001)

def test_priority_range():
    with pytest.raises(ValidationError):
        IssueCreate(description="ok", priority=10)
    with pytest.raises(ValidationError):
        IssueCreate(description="ok", priority=0)
```

- [ ] **Step 2: Tighten the schema**

```python
# backend/app/schemas/issue.py
from pydantic import BaseModel, Field, field_validator

class IssueCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str = Field(..., min_length=1, max_length=100_000)
    priority: int = Field(default=3, ge=1, le=5)

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be blank")
        return v
```

- [ ] **Step 3: Tests green**

```bash
cd backend && python -m pytest tests/test_schemas_issue.py -v
```

### Task 6.2: Validate project paths

**Files:**
- Modify: `backend/app/schemas/project.py`

- [ ] **Step 1: Enforce absolute path + existence warning (but do not block if missing — may be set before creation)**

```python
# backend/app/schemas/project.py
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    path: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=10_000)
    tech_stack: str | None = Field(default=None, max_length=10_000)
    shell: str | None = Field(default=None, max_length=500)

    @field_validator("path")
    @classmethod
    def path_must_be_absolute(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        p = Path(v)
        if not p.is_absolute():
            raise ValueError("project path must be absolute")
        return str(p)
```

### Task 6.3: Terminal dimensions

**Files:**
- Modify: `backend/app/schemas/terminal.py`

- [ ] **Step 1: Bound cols/rows**

```python
class TerminalCreate(BaseModel):
    project_id: str
    cols: int = Field(default=120, ge=20, le=400)
    rows: int = Field(default=30, ge=5, le=200)
```

- [ ] **Step 2: Run schema tests**

```bash
cd backend && python -m pytest tests/test_schemas_issue.py tests/test_routers_projects.py tests/test_routers_terminals.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/ backend/tests/test_schemas_issue.py
git commit -m "security(schemas): tighten length bounds and path validation"
```

---

## Phase 7: Activity Log Retention

**Why:** `activity_logs` table grows unbounded. Add a configurable retention window + a periodic purge.

### Task 7.1: Purge service

**Files:**
- Modify: `backend/app/services/activity_service.py`
- Modify: `backend/app/config.py` (already updated in Plan A Phase 3 — add new field)

- [ ] **Step 1: Add setting**

```python
# backend/app/config.py
activity_retention_days: int = 90  # 0 = keep forever
```

- [ ] **Step 2: Failing test**

```python
# backend/tests/test_activity_retention.py
from datetime import datetime, timedelta, timezone
from app.models import ActivityLog, Project
from app.services.activity_service import ActivityService


async def test_purge_removes_rows_older_than_retention(db_session):
    project = Project(id="p1", name="P", path="/p")
    db_session.add(project)
    old_ts = datetime.now(timezone.utc) - timedelta(days=100)
    recent_ts = datetime.now(timezone.utc) - timedelta(days=1)

    db_session.add_all([
        ActivityLog(id="a1", project_id="p1", event_type="x", details="{}", created_at=old_ts),
        ActivityLog(id="a2", project_id="p1", event_type="y", details="{}", created_at=recent_ts),
    ])
    await db_session.commit()

    svc = ActivityService(db_session)
    deleted = await svc.purge_older_than(days=90)
    assert deleted == 1

    remaining = await db_session.execute(__import__("sqlalchemy").select(ActivityLog))
    rows = remaining.scalars().all()
    assert {r.id for r in rows} == {"a2"}
```

- [ ] **Step 3: Implement**

```python
# backend/app/services/activity_service.py  (append to ActivityService)
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete

async def purge_older_than(self, days: int) -> int:
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await self.db.execute(delete(ActivityLog).where(ActivityLog.created_at < cutoff))
    await self.db.commit()
    return result.rowcount or 0
```

- [ ] **Step 4: Schedule on startup**

```python
# backend/app/main.py  (inside lifespan)
async def _purge_loop():
    while True:
        await asyncio.sleep(60 * 60 * 24)  # daily
        try:
            async with async_session() as session:
                await ActivityService(session).purge_older_than(settings.activity_retention_days)
        except Exception as exc:
            logger.error("Activity purge failed: %s", exc)

purge_task = asyncio.create_task(_purge_loop())
try:
    yield
finally:
    purge_task.cancel()
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_activity_retention.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/services/activity_service.py backend/app/main.py backend/tests/test_activity_retention.py
git commit -m "feat(activity): daily purge governed by activity_retention_days setting"
```

---

## Self-Review Checklist

- [ ] `grep -rn "WsEventData" frontend/src/` returns only the re-export line — no raw-typed usages.
- [ ] `issue-detail.tsx` below 100 lines after split.
- [ ] `npm run build` yields separate chunks for `library`, `commands`, `variables`.
- [ ] Mobile audit: every critical route renders without horizontal scroll at 375 px.
- [ ] `grep -rn "Nessun\|Aggiungi" frontend/src/` returns empty after migration.
- [ ] Pydantic tests cover boundary cases (length, range, blank-after-strip).
- [ ] Activity purge test passes and covers the `days=0 means keep forever` branch.

---

## Execution

Estimated effort:
1. Phase 1 (discriminated union) — 4 h
2. Phase 2 (IssueDetail split) — 6 h
3. Phase 3 (lazy routes) — 1 h
4. Phase 4 (mobile pass) — 8 h
5. Phase 5 (i18n) — 8 h (depends on string count)
6. Phase 6 (Pydantic tighten) — 3 h
7. Phase 7 (activity retention) — 2 h

Total: ~32 hours. Recommend splitting across two sprints if shipping with a single engineer.
