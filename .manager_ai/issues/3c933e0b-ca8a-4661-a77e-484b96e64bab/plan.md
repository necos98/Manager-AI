# Implementation Plan: PK Unification — Auto-Increment Integers with UUID Columns

## File Inventory

### Models to change (20 files — all in `backend/app/models/`):
- **UUID-PK → Integer PK + uuid**: project.py, issue.py, agent.py, task.py, pipeline.py, pipeline_run.py, pipeline_event_rule.py, memory.py, project_file.py, question.py, activity_log.py, issue_feedback.py, project_credential.py, project_link.py, credential_preset.py
- **Integer-PK → add uuid only**: issue_relation.py, project_skill.py, project_variable.py, prompt_template.py, terminal_command.py
- **Excluded**: setting.py, models/__init__.py

### Services to update (files with `session.get(Model, uuid_str)` — need lookup by uuid column):
- project_service.py (line 64)
- pipeline_run_service.py (lines 137, 417)
- project_variable_service.py (lines 22, 43, 53)
- question_service.py (lines 89, 101)
- terminal_command_service.py (lines 52, 66, 72)

### Services to update (files with `.where(Model.id == uuid_str)`):
- agent_service.py (line 109)
- credential_editor_service.py (line 79)
- pipeline_service.py (lines 51, 106, 173, 382)
- pipeline_run_service.py (lines 62, 617 — **NOT** lines 187, 375: those use DB-internal Integer refs, no change needed)
- project_link_service.py (line 63)
- project_service.py (line 116)

### Alembic:
- New migration file in `backend/alembic/versions/`

---

## Phase 1: Model Definition Changes

### Step 1 — UUID-PK Models: Add uuid column, change id to Integer

For each of these 18 UUID-PK models (excluding memory_links which has special handling), apply the pattern:

```python
# Before
id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

# After  
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
```

Models affected:
1. **project.py** — Project.id
2. **issue.py** — Issue.id
3. **agent.py** — Agent.id
4. **task.py** — Task.id
5. **pipeline.py** — Pipeline.id, PipelineStep.id
6. **pipeline_run.py** — PipelineRun.id, PipelineStepRun.id, PipelineMessage.id
7. **pipeline_event_rule.py** — PipelineEventRule.id
8. **memory.py** — Memory.id (NOT MemoryLink — see step 2)
9. **project_file.py** — ProjectFile.id
10. **question.py** — Question.id
11. **activity_log.py** — ActivityLog.id
12. **issue_feedback.py** — IssueFeedback.id
13. **project_credential.py** — ProjectCredential.id
14. **project_link.py** — ProjectLink.id
15. **credential_preset.py** — CredentialPreset.id

### Step 2 — MemoryLink Special Case (composite PK)

- DO NOT add `id` Integer PK column
- Convert `from_id` and `to_id` from String(36)→Integer
- Add `uuid` String(36) unique indexed column

```python
# Before
from_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
to_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True, index=True)

# After
from_id: Mapped[int] = mapped_column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
to_id: Mapped[int] = mapped_column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True, index=True)
uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
```

### Step 3 — Integer-PK Models: Add uuid column only

For these 5 models, keep existing Integer PK, just add uuid column:

```python
# Add after existing id:
uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
```

Models: issue_relation.py, project_skill.py, project_variable.py, prompt_template.py, terminal_command.py

### Step 4 — FK Column Type Changes

Convert all FK columns referencing UUID-PK tables from String(36)→Integer:

| File | Column | New Type | References |
|------|--------|----------|------------|
| issue.py | project_id | Integer | projects.id |
| task.py | issue_id | Integer | issues.id |
| pipeline.py (PipelineStep) | pipeline_id | Integer | pipelines.id |
| pipeline.py (PipelineStep) | agent_id | Integer | agents.id |
| pipeline_run.py (PipelineRun) | pipeline_id | Integer | pipelines.id |
| pipeline_run.py (PipelineStepRun) | pipeline_run_id | Integer | pipeline_runs.id |
| pipeline_run.py (PipelineStepRun) | pipeline_step_id | Integer | pipeline_steps.id |
| pipeline_run.py (PipelineMessage) | pipeline_run_id | Integer | pipeline_runs.id |
| pipeline_event_rule.py | pipeline_id | Integer | pipelines.id |
| pipeline_event_rule.py | source_step_id | Integer | pipeline_steps.id |
| pipeline_event_rule.py | target_step_id | Integer | pipeline_steps.id |
| memory.py (Memory) | project_id | Integer | projects.id |
| memory.py (Memory) | parent_id | Integer | memories.id (self-ref, nullable) |
| memory.py (MemoryLink) | from_id | Integer | memories.id |
| memory.py (MemoryLink) | to_id | Integer | memories.id |
| project_file.py | project_id | Integer | projects.id |
| question.py | project_id | Integer | projects.id |
| activity_log.py | project_id | Integer | projects.id |
| issue_feedback.py | issue_id | Integer | issues.id |
| issue_relation.py | source_id | Integer | issues.id |
| issue_relation.py | target_id | Integer | issues.id |
| project_variable.py | project_id | Integer | projects.id |
| terminal_command.py | project_id | Integer | projects.id |
| project_link.py | source_project_id | Integer | projects.id |
| project_link.py | target_project_id | Integer | projects.id |

### Step 5 — String Reference Columns (Keep As-Is)

These columns hold external UUID references, NOT DB FKs. Do NOT touch:

- pipeline_run.py: `issue_id` (String(255))
- question.py: `issue_id` (String(36))
- activity_log.py: `issue_id` (String(36))
- project_credential.py: `project_id` (String(36))
- project_skill.py: `project_id` (String(36))
- prompt_template.py: `project_id` (String(36))

### Step 6 — Imports

- Add `Integer` to SQLAlchemy imports in model files where missing (most already import it from existing Integer FK columns, but verify)
- Add `uuid` import removal consideration: files that only import `uuid` for `default=lambda: str(uuid.uuid4())` on PK can drop the `uuid` import (the PK no longer uses it). However, most files still need `uuid` for generating uuid column values in constructors.

---

## Phase 2: Migration

### Step 7 — Create Alembic Migration

New file: `backend/alembic/versions/<hash>_unify_pks_integer_uuid.py`

Migration approach per spec §5.1 (SQLite rename+recreate):

1. **For each UUID-PK table**: rename table → `old_<table>`, create new table with Integer PK + uuid column, copy data (id→uuid for existing rows), then drop old table
2. **For each Integer-PK table**: add uuid column as nullable first, backfill with Python uuid4, then recreate table with NOT NULL via rename+recreate
3. **FK remapping**: use a lookup dict (old_uuid → new_int_id) built during data copy to update child FK values

Migration order (respects FK dependencies):
```
projects → agents → pipelines → memories → issues →
pipeline_steps → pipeline_runs → pipeline_step_runs → pipeline_messages → pipeline_event_rules →
memory_links → project_files → questions → activity_logs → issue_feedback → project_links →
project_variables → terminal_commands → issue_relations → tasks →
project_skills → prompt_templates → project_credentials → credential_presets
```

---

## Phase 3: Service Layer Updates

### Step 8 — Update `session.get()` Lookups

In model services that call `session.get(Model, some_id)` where `some_id` is a UUID string passed from the API:

- `project_service.py:64` — `session.get(Project, project_id)` → `session.execute(select(Project).where(Project.uuid == project_id))`
- `pipeline_run_service.py:137` — `session.get(Pipeline, run.pipeline_id)` — `run.pipeline_id` is DB-internal Integer after migration. **NO CODE CHANGE** — the type change is handled in the model (Pipeline.id becomes Integer, and run.pipeline_id is the matching Integer FK value).
- `pipeline_run_service.py:417` — `session.get(Project, project_id)` where `project_id` comes from pipeline execution context (API-originated UUID string) → `session.execute(select(Project).where(Project.uuid == project_id))`
- `project_variable_service.py:22,43,53` — `session.get(ProjectVariable, var_id)` → `session.execute(select(ProjectVariable).where(ProjectVariable.uuid == var_id))`
- `question_service.py:89,101` — `session.get(Question, question_id)` → `session.execute(select(Question).where(Question.uuid == question_id))`
- `terminal_command_service.py:52,66,72` — `session.get(TerminalCommand, cmd_id)` → `session.execute(select(TerminalCommand).where(TerminalCommand.uuid == cmd_id))`

### Step 9 — Update `.where(Model.id == uuid_str)` Queries

In services that filter by `.id` using a UUID string (not Integer):

**API-facing lookups (must change to `.where(Model.uuid ==)`):**

- `agent_service.py:109` — `.where(Agent.id == agent_id)` where `agent_id` is API param → `.where(Agent.uuid == agent_id)`
- `credential_editor_service.py:79` — `.where(CredentialPreset.id == preset_id)` where `preset_id` is API param → `.where(CredentialPreset.uuid == preset_id)`
- `pipeline_service.py:51` — `.where(Pipeline.id == pipeline_id)` where `pipeline_id` is API param → `.where(Pipeline.uuid == pipeline_id)`
- `pipeline_service.py:106` — `.where(PipelineStep.id == step_id)` where `step_id` is API param → `.where(PipelineStep.uuid == step_id)`
- `pipeline_service.py:173` — `.where(Pipeline.id == pipeline_id)` where `pipeline_id` is API param → `.where(Pipeline.uuid == pipeline_id)`
- `pipeline_service.py:382` — `.where(PipelineEventRule.id == rule_id)` where `rule_id` is API param → `.where(PipelineEventRule.uuid == rule_id)`
- `pipeline_run_service.py:62` — `.where(Pipeline.id == pipeline_id)` where `pipeline_id` is API param → `.where(Pipeline.uuid == pipeline_id)`
- `pipeline_run_service.py:617` — `.where(PipelineRun.id == run_id)` where `run_id` is API param → `.where(PipelineRun.uuid == run_id)`
- `project_link_service.py:63` — `.where(ProjectLink.id == link_id)` where `link_id` is API param → `.where(ProjectLink.uuid == link_id)`
- `project_service.py:116` — `.where(Project.id == project_id)` where `project_id` is API param → `.where(Project.uuid == project_id)`

**DB-internal lookups (do NOT change — already use correct type after migration):**

- `pipeline_run_service.py:187` — `.where(Pipeline.id == run.pipeline_id)` — `run.pipeline_id` is DB-internal Integer after migration
- `pipeline_run_service.py:375` — `.where(Pipeline.id == run.pipeline_id)` — same, `run.pipeline_id` is DB-internal Integer

> **IMPORTANT:** Lines 187 and 375 in pipeline_run_service.py use `run.pipeline_id` which is a DB-internal FK value. After migration, Pipeline.id becomes Integer and run.pipeline_id (FK to Pipeline.id) becomes Integer too. The existing `.where(Pipeline.id == run.pipeline_id)` continues to work correctly. Do NOT change these to `.where(Pipeline.uuid == run.pipeline_id)` — that would break because `run.pipeline_id` is no longer a UUID string.

### Step 10 — Relationship Definitions

All `relationship()` definitions reference foreign keys by string name (e.g., `ForeignKey("projects.id")`). These stay as strings — SQLAlchemy resolves them at runtime by column name, not column type. No code changes needed.

However, verify that each `relationship()` back_populates still matches — the field names on the model haven't changed, so this should be fine.

### Step 11 — Add `by_uuid` Helper (Optional/Recommended)

Add a `by_uuid` classmethod on models that need frequent API-facing lookups. Pattern:

```python
@classmethod
async def by_uuid(cls, session: AsyncSession, uuid_str: str) -> Self | None:
    result = await session.execute(select(cls).where(cls.uuid == uuid_str))
    return result.scalar_one_or_none()
```

This can be added to individual model files as needed, or skipped entirely — the `session.execute(select(Model).where(Model.uuid == ...))` pattern in services directly is sufficient.

---

## Phase 4: Verification

### Step 12 — Test Migration

- Run `python -m alembic upgrade head` to apply migration
- Verify no errors
- Check that data is preserved (row counts match, uuid values match former id values for UUID-PK tables)

### Step 13 — Test Service Lookups

- Run existing test suite: `python -m pytest` from backend directory
- Verify all tests pass
- If tests use in-memory SQLite (which can't handle vector columns), verify the migration works with production SQLite database

---

## Task Breakdown (for TaskWriter)

The work breaks into these atomic tasks in dependency order:

1. **Add uuid + Integer PK to 18 UUID-PK model files** (project, issue, agent, task, pipeline, pipeline_run, pipeline_event_rule, memory, project_file, question, activity_log, issue_feedback, project_credential, project_link, credential_preset)
2. **Handle MemoryLink composite PK special case** (convert from_id/to_id to Integer, add uuid)
3. **Add uuid column to 5 Integer-PK model files** (issue_relation, project_skill, project_variable, prompt_template, terminal_command)
4. **Convert all FK columns from String(36)→Integer** across affected model files (24 FK columns in 15 model files)
5. **Verify/correct imports** (Integer import, uuid import cleanup)
6. **Create Alembic migration** — rename+recreate pattern for all tables with FK remapping
7. **Update service layer `session.get()` calls** for API-facing lookups (project_service, pipeline_run_service:417, project_variable_service, question_service, terminal_command_service)
8. **Update service layer `.where(Model.id ==)` queries** for API-facing lookups (agent_service, credential_editor_service, pipeline_service, pipeline_run_service:62/617, project_link_service, project_service)
9. **Run tests and verify** — `python -m pytest`

## Key Constraints

1. **MemoryLink is the only table without an auto-increment id PK** — it keeps composite PK, only converts from_id/to_id to Integer
2. **String reference columns stay String** — pipeline_runs.issue_id, questions.issue_id, activity_logs.issue_id, project_credentials.project_id, project_skills.project_id, prompt_templates.project_id
3. **No API/frontend changes** — the API continues to pass UUID strings; only the DB layer changes
4. **FK relationships in relationship() definitions reference columns by string name** — these do NOT need changes
5. **SQLite ALTER TABLE limitations** require rename+recreate pattern for columns changing to NOT NULL or changing type
6. **Migration order matters** — parents before children due to FK constraints
7. **Data integrity**: each existing UUID-PK row's id IS the uuid — copy id→uuid during migration. Integer-PK rows need new uuid4 generated.
8. **pipeline_run_service lines 187, 375 use DB-internal `run.pipeline_id`** — do NOT change these to uuid lookup; the FK value is already Integer after migration
