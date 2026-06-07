# Pipeline Event Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable event rules to pipelines — when a step rejects, auto-redirect to a configured target step.

**Architecture:** New `PipelineEventRule` model (SQLAlchemy, DB-backed like Pipeline/PipelineStep). CRUD via `PipelineService`. MCP tools for agent-side management. REST endpoints for frontend UI. Auto-resolution in `finished_pipeline_step` when `target_step_index` is omitted.

**Tech Stack:** Python/FastAPI/SQLAlchemy, React/TypeScript, Alembic

---

### Task 1: PipelineEventRule model + Alembic migration

**Files:**
- Create: `backend/app/models/pipeline_event_rule.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/pipeline.py`
- Create: Alembic migration

- [ ] **Step 1: Create model file**

`backend/app/models/pipeline_event_rule.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineEventRule(Base):
    __tablename__ = "pipeline_event_rules"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_id", "event_type", "source_step_id",
            name="uq_pipeline_event_rule",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_steps.id"), nullable=False
    )
    target_step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_steps.id"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    pipeline = relationship("Pipeline", back_populates="event_rules")
    source_step = relationship("PipelineStep", foreign_keys=[source_step_id])
    target_step = relationship("PipelineStep", foreign_keys=[target_step_id])
```

- [ ] **Step 2: Add relationship to Pipeline model**

In `backend/app/models/pipeline.py`, add to `Pipeline` class body (after `runs`):

```python
event_rules = relationship(
    "PipelineEventRule", back_populates="pipeline",
    cascade="all, delete-orphan",
)
```

- [ ] **Step 3: Register in models/__init__.py**

Add `from app.models.pipeline_event_rule import PipelineEventRule` to imports and `"PipelineEventRule"` to `__all__`.

- [ ] **Step 4: Generate + apply migration**

```bash
cd backend
python -m alembic revision --autogenerate -m "add pipeline_event_rules table"
python -m alembic upgrade head
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/pipeline_event_rule.py backend/app/models/pipeline.py backend/app/models/__init__.py backend/alembic/
git commit -m "feat: add PipelineEventRule model + migration"
```

---

### Task 2: Event rule CRUD in PipelineService + rejection target resolver

**Files:**
- Modify: `backend/app/services/pipeline_service.py`
- Modify: `backend/app/services/pipeline_run_service.py`

- [ ] **Step 1: Add import and CRUD to PipelineService**

In `pipeline_service.py`, add import:

```python
from app.models.pipeline_event_rule import PipelineEventRule
```

Add methods to `PipelineService` class:

```python
    # ── Event Rule CRUD ─────────────────────────────────────────────

    async def add_event_rule(
        self,
        pipeline_id: str,
        event_type: str,
        source_step_id: str,
        target_step_id: str,
    ) -> PipelineEventRule:
        """Add event rule. Validates both step IDs belong to pipeline."""
        pipeline = await self.get_pipeline(pipeline_id)
        step_ids = {s.id for s in pipeline.steps}
        if source_step_id not in step_ids:
            raise NotFoundError(f"source_step_id {source_step_id} not in pipeline steps")
        if target_step_id not in step_ids:
            raise NotFoundError(f"target_step_id {target_step_id} not in pipeline steps")
        rule = PipelineEventRule(
            pipeline_id=pipeline_id,
            event_type=event_type,
            source_step_id=source_step_id,
            target_step_id=target_step_id,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def remove_event_rule(self, rule_id: str) -> bool:
        result = await self.session.execute(
            select(PipelineEventRule).where(PipelineEventRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise NotFoundError(f"PipelineEventRule not found: {rule_id}")
        await self.session.delete(rule)
        await self.session.flush()
        return True

    async def list_event_rules(self, pipeline_id: str) -> list[PipelineEventRule]:
        result = await self.session.execute(
            select(PipelineEventRule)
            .where(PipelineEventRule.pipeline_id == pipeline_id)
            .order_by(PipelineEventRule.created_at)
        )
        return list(result.scalars().all())

    async def get_event_rule_for_step(
        self, pipeline_id: str, event_type: str, source_step_id: str
    ) -> PipelineEventRule | None:
        result = await self.session.execute(
            select(PipelineEventRule).where(
                PipelineEventRule.pipeline_id == pipeline_id,
                PipelineEventRule.event_type == event_type,
                PipelineEventRule.source_step_id == source_step_id,
                PipelineEventRule.enabled.is_(True),
            )
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 2: Add resolve_rejection_target to PipelineRunService**

In `pipeline_run_service.py`, add method:

```python
    async def resolve_rejection_target(
        self, run_id: str, step_id: str
    ) -> int | None:
        """Check event rules for rejection redirect. Returns target order_index or None."""
        from app.services.pipeline_service import PipelineService

        run = await self._get_run_with_session(run_id, self.session)
        pipeline_svc = PipelineService(self.session)
        rule = await pipeline_svc.get_event_rule_for_step(
            run.pipeline_id, "step_rejected", step_id
        )
        if rule is None:
            return None
        pipeline = await self.session.get(Pipeline, run.pipeline_id)
        if pipeline is None:
            return None
        for s in pipeline.steps:
            if s.id == rule.target_step_id:
                return s.order_index
        return None
```

Add `Pipeline` import at top if not present (it is: line 12 `from app.models.pipeline import Pipeline, PipelineStep`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/pipeline_service.py backend/app/services/pipeline_run_service.py
git commit -m "feat: add event rule CRUD + rejection target resolver"
```

---

### Task 3: MCP tool changes — finished_pipeline_step auto-resolve

**Files:**
- Modify: `backend/app/mcp/server.py`

- [ ] **Step 1: Modify `finished_pipeline_step` to make `target_step_index` optional**

Replace lines 1375-1392 (`if rejected:` block):

```python
        if rejected:
            if not rejection_reason:
                return {"error": "rejection_reason is required when rejected=True"}

            issue_service = IssueService(session)
            issue = await issue_service.get_by_id(issue_id)
            project_id = issue.project_id if issue else None
            if not project_id:
                return {"error": "Could not determine project_id for issue"}

            if target_step_index is None:
                resolved = await svc.resolve_rejection_target(run_id, step["id"])
                if resolved is None:
                    return {
                        "error": "No rejection redirect configured for this step. "
                                 "Provide target_step_index or configure an event rule."
                    }
                target_step_index = resolved

            reject_result = await svc.reject_step(
                run_id=run_id,
                reason=rejection_reason,
                target_step_index=target_step_index,
                project_id=project_id,
            )
```

Rest of function (summary message, set_step_completed, pipeline_finished) stays unchanged.

- [ ] **Step 2: Commit**

```bash
git add backend/app/mcp/server.py
git commit -m "feat: auto-resolve rejection target from event rules"
```

---

### Task 4: MCP tools for event rule CRUD

**Files:**
- Modify: `backend/app/mcp/default_settings.json`
- Modify: `backend/app/mcp/server.py`

- [ ] **Step 1: Add descriptions to default_settings.json**

```json
"tool.add_pipeline_event_rule.description": "Add an event rule to a pipeline. Parameters: pipeline_id (required), event_type (required, currently 'step_rejected'), source_step_id (required), target_step_id (required). Returns the created rule.",
"tool.remove_pipeline_event_rule.description": "Delete an event rule by ID. Returns {deleted: true}.",
"tool.list_pipeline_event_rules.description": "List all event rules for a pipeline. Parameters: pipeline_id (required). Returns list of rules."
```

- [ ] **Step 2: Add MCP tools in server.py**

Place right before `finished_pipeline_step` tool (around line 1350):

```python
# ── Pipeline event rule tools ──────────────────────────────────────────


@mcp.tool(description=_desc["tool.add_pipeline_event_rule.description"])
async def add_pipeline_event_rule(
    pipeline_id: str,
    event_type: str,
    source_step_id: str,
    target_step_id: str,
) -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        try:
            rule = await svc.add_event_rule(
                pipeline_id=pipeline_id,
                event_type=event_type,
                source_step_id=source_step_id,
                target_step_id=target_step_id,
            )
            await session.commit()
            return {
                "id": rule.id,
                "pipeline_id": rule.pipeline_id,
                "event_type": rule.event_type,
                "source_step_id": rule.source_step_id,
                "target_step_id": rule.target_step_id,
                "enabled": rule.enabled,
            }
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.remove_pipeline_event_rule.description"])
async def remove_pipeline_event_rule(rule_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        try:
            await svc.remove_event_rule(rule_id)
            await session.commit()
            return {"deleted": True}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.list_pipeline_event_rules.description"])
async def list_pipeline_event_rules(pipeline_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        rules = await svc.list_event_rules(pipeline_id)
        return {
            "rules": [
                {
                    "id": r.id,
                    "pipeline_id": r.pipeline_id,
                    "event_type": r.event_type,
                    "source_step_id": r.source_step_id,
                    "target_step_id": r.target_step_id,
                    "enabled": r.enabled,
                }
                for r in rules
            ]
        }
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/mcp/server.py backend/app/mcp/default_settings.json
git commit -m "feat: add MCP tools for pipeline event rule CRUD"
```

---

### Task 5: REST API endpoints for event rules

**Files:**
- Modify: `backend/app/routers/pipelines.py`
- Create: `backend/app/schemas/pipeline_event_rule.py`

- [ ] **Step 1: Create Pydantic schemas**

`backend/app/schemas/pipeline_event_rule.py`:

```python
from pydantic import BaseModel, Field


class PipelineEventRuleResponse(BaseModel):
    id: str
    pipeline_id: str
    event_type: str
    source_step_id: str
    target_step_id: str
    enabled: bool
    created_at: str | None = None
    updated_at: str | None = None


class PipelineEventRuleCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    source_step_id: str = Field(..., min_length=1)
    target_step_id: str = Field(..., min_length=1)
```

- [ ] **Step 2: Add REST endpoints to pipelines router**

In `backend/app/routers/pipelines.py`, add:

```python
from app.schemas.pipeline_event_rule import (
    PipelineEventRuleCreate,
    PipelineEventRuleResponse,
)
```

Add endpoints after the steps reorder endpoint (after line 335):

```python
# ── Event Rules ─────────────────────────────────────────────────


def _rule_response(rule) -> PipelineEventRuleResponse:
    return PipelineEventRuleResponse(
        id=rule.id,
        pipeline_id=rule.pipeline_id,
        event_type=rule.event_type,
        source_step_id=rule.source_step_id,
        target_step_id=rule.target_step_id,
        enabled=rule.enabled,
        created_at=str(rule.created_at) if rule.created_at else None,
        updated_at=str(rule.updated_at) if rule.updated_at else None,
    )


@router.get(
    "/{pipeline_id}/event-rules",
    response_model=list[PipelineEventRuleResponse],
)
async def list_event_rules(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    rules = await svc.list_event_rules(pipeline_id)
    return [_rule_response(r) for r in rules]


@router.post(
    "/{pipeline_id}/event-rules",
    response_model=PipelineEventRuleResponse,
    status_code=201,
)
async def create_event_rule(
    pipeline_id: str,
    data: PipelineEventRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    try:
        rule = await svc.add_event_rule(
            pipeline_id=pipeline_id,
            event_type=data.event_type,
            source_step_id=data.source_step_id,
            target_step_id=data.target_step_id,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
    return _rule_response(rule)


@router.delete(
    "/{pipeline_id}/event-rules/{rule_id}",
    status_code=204,
)
async def delete_event_rule(
    pipeline_id: str,
    rule_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    try:
        await svc.remove_event_rule(rule_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/pipeline_event_rule.py backend/app/routers/pipelines.py
git commit -m "feat: add REST API endpoints for pipeline event rules"
```

---

### Task 6: Frontend types, API, and hooks

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/features/pipelines/api.ts`
- Modify: `frontend/src/features/pipelines/hooks.ts`

- [ ] **Step 1: Add types**

In `frontend/src/shared/types/index.ts`, add after Pipeline types (after `StepReorderRequest`):

```typescript
// ── Pipeline Event Rules ──

export interface PipelineEventRule {
  id: string;
  pipeline_id: string;
  event_type: string;
  source_step_id: string;
  target_step_id: string;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface PipelineEventRuleCreate {
  event_type: string;
  source_step_id: string;
  target_step_id: string;
}
```

- [ ] **Step 2: Add API functions**

In `frontend/src/features/pipelines/api.ts`, add:

```typescript
import type { PipelineEventRule, PipelineEventRuleCreate } from "@/shared/types";

export function fetchEventRules(pipelineId: string): Promise<PipelineEventRule[]> {
  return apiGet<PipelineEventRule[]>(`/pipelines/${pipelineId}/event-rules`);
}

export function createEventRule(pipelineId: string, data: PipelineEventRuleCreate): Promise<PipelineEventRule> {
  return apiPost<PipelineEventRule>(`/pipelines/${pipelineId}/event-rules`, data);
}

export function deleteEventRule(pipelineId: string, ruleId: string): Promise<null> {
  return apiDelete(`/pipelines/${pipelineId}/event-rules/${ruleId}`);
}
```

- [ ] **Step 3: Add hooks**

In `frontend/src/features/pipelines/hooks.ts`, add:

```typescript
import type { PipelineEventRuleCreate } from "@/shared/types";

export function useEventRules(pipelineId: string) {
  return useQuery({
    queryKey: [...pipelineKeys.detail(pipelineId), "event-rules"],
    queryFn: () => api.fetchEventRules(pipelineId),
    enabled: Boolean(pipelineId),
  });
}

export function useCreateEventRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: PipelineEventRuleCreate }) =>
      api.createEventRule(pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useDeleteEventRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, ruleId }: { pipelineId: string; ruleId: string }) =>
      api.deleteEventRule(pipelineId, ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function usePipelineEventRules(pipelineId: string) {
  return useQuery({
    queryKey: [...pipelineKeys.detail(pipelineId), "event-rules"],
    queryFn: () => api.fetchEventRules(pipelineId),
    enabled: Boolean(pipelineId),
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/types/index.ts frontend/src/features/pipelines/api.ts frontend/src/features/pipelines/hooks.ts
git commit -m "feat: frontend types, API, hooks for event rules"
```

---

### Task 7: Frontend UI — event rules section in PipelinesTab

**Files:**
- Modify: `frontend/src/features/pipelines/components/PipelinesTab.tsx`

- [ ] **Step 1: Add imports**

Add to existing imports:

```typescript
import {
  useEventRules,
  useCreateEventRule,
  useDeleteEventRule,
} from "@/features/pipelines/hooks";
import type { PipelineEventRule } from "@/shared/types";
```

- [ ] **Step 2: Add event rules section inside expanded pipeline card**

Inside the expanded section, after the steps builder (after the "Add Step" button div, before the closing `</div>` of the expanded section), add:

```tsx
{/* Event Rules */}
<div className="pt-3 border-t mt-3">
  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
    Event Rules
  </p>
  <EventRulesSection
    pipelineId={pipeline.id}
    steps={sortedSteps}
    agents={agentMap}
  />
</div>
```

- [ ] **Step 3: Create EventRulesSection component**

Add before `PipelinesTab` component or at the bottom of the file:

```tsx
function EventRulesSection({
  pipelineId,
  steps,
  agents,
}: {
  pipelineId: string;
  steps: PipelineStep[];
  agents: Map<string, string>;
}) {
  const { data: rules = [] } = useEventRules(pipelineId);
  const createRule = useCreateEventRule();
  const deleteRule = useDeleteEventRule();
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");

  const handleAdd = () => {
    if (!sourceId || !targetId) return;
    createRule.mutate(
      {
        pipelineId,
        data: {
          event_type: "step_rejected",
          source_step_id: sourceId,
          target_step_id: targetId,
        },
      },
      {
        onSuccess: () => {
          setSourceId("");
          setTargetId("");
        },
      }
    );
  };

  return (
    <div className="space-y-2">
      {rules.length === 0 ? (
        <p className="text-sm text-muted-foreground py-1">
          No event rules configured.
        </p>
      ) : (
        <div className="space-y-1.5">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center gap-2 bg-muted/30 rounded px-3 py-2 text-sm"
            >
              <Badge variant="outline" className="text-xs">
                {rule.event_type}
              </Badge>
              <span className="text-muted-foreground">when</span>
              <span className="font-medium">
                {agents.get(rule.source_step_id) ?? "Unknown"}
              </span>
              <span className="text-muted-foreground">→</span>
              <span className="font-medium">
                {agents.get(rule.target_step_id) ?? "Unknown"}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="size-6 ml-auto text-destructive hover:text-destructive"
                disabled={deleteRule.isPending}
                onClick={() =>
                  deleteRule.mutate({ pipelineId, ruleId: rule.id })
                }
              >
                <X className="size-3" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Add rule form */}
      <div className="flex items-center gap-2 pt-1">
        <Select value={sourceId} onValueChange={setSourceId}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="When step..." />
          </SelectTrigger>
          <SelectContent>
            {steps.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {agents.get(s.agent_id) ?? "Unknown"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">rejects → go to</span>
        <Select value={targetId} onValueChange={setTargetId}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="Target step..." />
          </SelectTrigger>
          <SelectContent>
            {steps.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {agents.get(s.agent_id) ?? "Unknown"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          className="h-8 text-xs"
          disabled={!sourceId || !targetId || createRule.isPending}
          onClick={handleAdd}
        >
          <Plus className="size-3 mr-1" />
          Add Rule
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/pipelines/components/PipelinesTab.tsx
git commit -m "feat: event rules UI in PipelinesTab"
```

---

### Task 8: Export/Import event rules

**Files:**
- Modify: `backend/app/schemas/export_import.py`
- Modify: `backend/app/services/pipeline_service.py`

- [ ] **Step 1: Add export format for event rules**

In `export_import.py`, add:

```python
def format_pipeline_event_rule_export(rule) -> dict:
    return {
        "id": rule.id,
        "event_type": rule.event_type,
        "source_step_id": rule.source_step_id,
        "target_step_id": rule.target_step_id,
        "enabled": rule.enabled,
    }
```

Update `format_pipeline_export`:

```python
def format_pipeline_export(pipeline) -> dict:
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "steps": [format_pipeline_step_export(s) for s in (pipeline.steps or [])],
        "event_rules": [format_pipeline_event_rule_export(r) for r in (pipeline.event_rules or [])],
    }
```

Add eager load of `event_rules` in `export_by_id` and `export_all`: add `.options(selectinload(Pipeline.event_rules))` to the query. Wait — `Pipeline` already has lazy-loaded relationships by default. Let me add `selectinload` for `event_rules`:

In `export_by_id`, after `.options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))`, add:
```python
selectinload(Pipeline.event_rules)
```

Same for `export_all`.

- [ ] **Step 2: Update Pipeline.export_by_id**

```python
async def export_by_id(self, pipeline_id: str) -> Pipeline:
    result = await self.session.execute(
        select(Pipeline)
        .where(Pipeline.id == pipeline_id)
        .options(
            selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
            selectinload(Pipeline.event_rules),
        )
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        raise NotFoundError(f"Pipeline not found: {pipeline_id}")
    return pipeline
```

- [ ] **Step 3: Update Pipeline.export_all**

```python
async def export_all(self) -> list[Pipeline]:
    result = await self.session.execute(
        select(Pipeline)
        .options(
            selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
            selectinload(Pipeline.event_rules),
        )
    )
    return list(result.unique().scalars().all())
```

- [ ] **Step 4: Handle import of event rules in import_pipelines**

In `import_pipelines` method, after the steps creation block and before `Imported += 1`, add event rule import for both "overwrite" and "new" cases.

For the "overwrite" case (after `replace_steps`):

```python
                    # Delete existing event rules and re-import
                    existing_rules = await self.session.execute(
                        select(PipelineEventRule).where(
                            PipelineEventRule.pipeline_id == pipeline_id
                        )
                    )
                    for r in existing_rules.scalars().all():
                        await self.session.delete(r)
                    await self.session.flush()

                    # Map old step IDs to new by order_index
                    new_steps = await self.session.execute(
                        select(PipelineStep)
                        .where(PipelineStep.pipeline_id == pipeline_id)
                        .order_by(PipelineStep.order_index)
                    )
                    new_step_list = new_steps.scalars().all()
                    step_id_map = {}
                    for i, sd in enumerate(steps_data):
                        old_id = sd.get("id")
                        if old_id and i < len(new_step_list):
                            step_id_map[old_id] = new_step_list[i].id

                    for rule_data in item.get("event_rules", []):
                        new_source = step_id_map.get(rule_data.get("source_step_id", ""))
                        new_target = step_id_map.get(rule_data.get("target_step_id", ""))
                        if new_source and new_target:
                            rule = PipelineEventRule(
                                pipeline_id=pipeline_id,
                                event_type=rule_data["event_type"],
                                source_step_id=new_source,
                                target_step_id=new_target,
                                enabled=rule_data.get("enabled", True),
                            )
                            self.session.add(rule)
                    await self.session.flush()
```

For the "new" case (after step creation), same logic but `pipeline.id` instead of `pipeline_id`.

Add import at top of `pipeline_service.py`:

```python
from app.models.pipeline_event_rule import PipelineEventRule
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/export_import.py backend/app/services/pipeline_service.py
git commit -m "feat: export/import pipeline event rules"
```

---

### Task 9: Tests

**Files:**
- Modify: `backend/tests/` (create test file for event rules)

- [ ] **Step 1: Test event rule CRUD + rejection target resolution**

`backend/tests/test_pipeline_event_rules.py`:

```python
import pytest
from sqlalchemy import select

from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_event_rule import PipelineEventRule
from app.models.pipeline_run import PipelineRun, PipelineRunStatus, PipelineStepRun, PipelineStepRunStatus
from app.services.pipeline_service import PipelineService
from app.services.pipeline_run_service import PipelineRunService
from app.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_add_and_list_event_rules(db_session):
    svc = PipelineService(db_session)
    pipeline = await svc.seed_defaults()
    steps = pipeline.steps
    assert len(steps) >= 2

    rule = await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps[1].id,
        target_step_id=steps[0].id,
    )
    assert rule.event_type == "step_rejected"
    assert rule.source_step_id == steps[1].id
    assert rule.target_step_id == steps[0].id
    assert rule.enabled is True

    rules = await svc.list_event_rules(pipeline.id)
    assert len(rules) == 1
    assert rules[0].id == rule.id


@pytest.mark.asyncio
async def test_get_event_rule_for_step(db_session):
    svc = PipelineService(db_session)
    pipeline = await svc.seed_defaults()
    steps = pipeline.steps

    await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps[1].id,
        target_step_id=steps[0].id,
    )

    found = await svc.get_event_rule_for_step(
        pipeline.id, "step_rejected", steps[1].id
    )
    assert found is not None
    assert found.target_step_id == steps[0].id

    not_found = await svc.get_event_rule_for_step(
        pipeline.id, "step_rejected", steps[2].id
    )
    assert not_found is None


@pytest.mark.asyncio
async def test_remove_event_rule(db_session):
    svc = PipelineService(db_session)
    pipeline = await svc.seed_defaults()
    steps = pipeline.steps

    rule = await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps[1].id,
        target_step_id=steps[0].id,
    )
    await svc.remove_event_rule(rule.id)

    rules = await svc.list_event_rules(pipeline.id)
    assert len(rules) == 0


@pytest.mark.asyncio
async def test_add_event_rule_invalid_step_id(db_session):
    svc = PipelineService(db_session)
    pipeline = await svc.seed_defaults()

    with pytest.raises(NotFoundError):
        await svc.add_event_rule(
            pipeline_id=pipeline.id,
            event_type="step_rejected",
            source_step_id="non-existent",
            target_step_id="non-existent",
        )


@pytest.mark.asyncio
async def test_resolve_rejection_target(db_session):
    svc = PipelineService(db_session)
    pipeline = await svc.seed_defaults()
    steps = sorted(pipeline.steps, key=lambda s: s.order_index)
    assert len(steps) >= 2

    await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps[1].id,
        target_step_id=steps[0].id,
    )
    await db_session.commit()

    # Create a pipeline run
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id="test-issue-123",
        status=PipelineRunStatus.RUNNING,
        current_step_index=1,
    )
    db_session.add(run)
    await db_session.flush()

    run_svc = PipelineRunService(db_session)
    target = await run_svc.resolve_rejection_target(run.id, steps[1].id)
    assert target == 0


@pytest.mark.asyncio
async def test_resolve_rejection_target_no_rule(db_session):
    svc = PipelineService(db_session)
    pipeline = await svc.seed_defaults()
    steps = sorted(pipeline.steps, key=lambda s: s.order_index)

    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id="test-issue-456",
        status=PipelineRunStatus.RUNNING,
        current_step_index=1,
    )
    db_session.add(run)
    await db_session.flush()

    run_svc = PipelineRunService(db_session)
    target = await run_svc.resolve_rejection_target(run.id, steps[1].id)
    assert target is None
```

- [ ] **Step 2: Run tests**

```bash
cd backend
python -m pytest tests/test_pipeline_event_rules.py -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_pipeline_event_rules.py
git commit -m "test: pipeline event rule CRUD + rejection target resolution"
```

---

## Self-Review

**Spec coverage:**
- Model + migration → Task 1 ✓
- CRUD in PipelineService → Task 2 ✓
- rejection target resolver → Task 2 ✓
- `finished_pipeline_step` auto-resolve → Task 3 ✓
- MCP tools for rule management → Task 4 ✓
- REST API → Task 5 ✓
- Frontend types, API, hooks → Task 6 ✓
- Frontend UI → Task 7 ✓
- Export/Import → Task 8 ✓
- Tests → Task 9 ✓

**Placeholder scan:** No TBD, TODO, or vague steps. All code blocks filled.

**Type consistency:** Method signatures consistent across tasks. `PipelineEventRuleCreate` → `add_event_rule` → `PipelineEventRule` model — types align. `resolve_rejection_target` returns `int | None` — used in MCP tool accordingly.
