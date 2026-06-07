# Add missing database indexes and constraints

## Summary
Add database indexes and a uniqueness constraint to three SQLAlchemy models to improve query performance and enforce data integrity. Current models have columns that are frequently filtered, sorted, or joined but lack indexes, causing full table scans.

## Scope

### 1. Issue model (`issues` table)
Add `__table_args__` with indexes on columns used in queries, filters, sorts, and joins:

| Column | Index type | Rationale |
|--------|-----------|-----------|
| `project_id` | single-column index | Foreign key — used in JOINs from PipelineRun queries (e.g., `get_active_runs_for_project` joins Issue on project_id) |
| `status` | single-column index | Frequently filtered — used for status-based queries |
| `priority` | single-column index | Used in sorting/filtering |
| `category` | single-column index | Used in category filtering |
| `name` | single-column index | Used in name-based lookups |
| `project_id`, `status` | composite index | Common filtering pattern — `WHERE project_id = X AND status = Y` |

**Why not file-backed storage relevance**: IssueService is file-backed, but the `issues` table is still queried directly by `pipeline_run_service` (JOINs via `Issue.id` / `Issue.project_id`) and other services. Indexes remain valuable for these queries.

### 2. Agent model (`agents` table)
Add `UniqueConstraint("name", name="uq_agent_name")` via `__table_args__`. Service already queries by `Agent.name` and lists agents ordered by `name` — uniqueness at DB level prevents duplicate agent names from slipping through.

Note: `Agent` model already imports `UniqueConstraint` — only `__table_args__` declaration needs wiring.

### 3. Project model (`projects` table)
Add single-column index on `name`. Service lists projects sorted by `lower(name)`.

## Constraints
- Must use SQLAlchemy declarative `__table_args__` pattern with `Index()` and `UniqueConstraint()` — consistent with existing models (`task.py`, `project_variable.py`, `pipeline_event_rule.py`, etc.)
- Migration must be chainable from current alembic head
- Migration must use `render_as_batch=True` (SQLite constraint)
- Zero change to model relationships, columns, or service logic — schema-only change
- Must preserve all existing indexes (none exist on these tables currently)

## Acceptance Criteria
1. `issues` table has indexes on: `project_id`, `status`, `priority`, `category`, `name`, and composite `(project_id, status)`
2. `agents` table has `UniqueConstraint` on `name` column
3. `projects` table has index on `name` column
4. All changes are applied via an Alembic migration
5. Existing tests pass after migration
6. Application starts without errors after migration

## Non-Goals
- Do NOT add indexes on `created_at`, `updated_at`, `finished_at`, or other temporal columns — no query patterns currently benefit
- Do NOT change any column types, nullable constraints, defaults, or relationships
- Do NOT modify service layer logic or add new query methods
- Do NOT add validation logic in service layer for agent name uniqueness (covered by DB constraint)

## Files to Modify
- `backend/app/models/issue.py` — add `__table_args__` with Index entries
- `backend/app/models/agent.py` — add `__table_args__` with UniqueConstraint on name
- `backend/app/models/project.py` — add `__table_args__` with Index on name
- New Alembic migration file — apply the schema changes

## Migration Details
- Parent revision: `fa326b3a9bb1` (latest head per alembic history)
- Use `op.create_index()` and `op.create_unique_constraint()` with `render_as_batch=True`
- Standard rollback should drop indexes / drop the constraint
