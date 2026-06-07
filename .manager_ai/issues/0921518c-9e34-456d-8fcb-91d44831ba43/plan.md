# Implementation Plan: Add missing database indexes and constraints

## Overview
Add 6 indexes to Issue model, 1 UniqueConstraint to Agent model, and 1 index to Project model. Schema-only changes — no service logic or test modifications.

## Step 1: Add `__table_args__` to Issue model

**File:** `backend/app/models/issue.py`

Add `Index` to imports:
```python
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
```

Add `__table_args__` after `__tablename__`:
```python
__table_args__ = (
    Index("ix_issues_project_id", "project_id"),
    Index("ix_issues_status", "status"),
    Index("ix_issues_priority", "priority"),
    Index("ix_issues_category", "category"),
    Index("ix_issues_name", "name"),
    Index("ix_issues_project_id_status", "project_id", "status"),
)
```

**Why composite index included despite project_id overlap:** Composite `(project_id, status)` serves `WHERE project_id = X AND status = Y` queries efficiently via leftmost prefix. Single-column `project_id` index still valuable for queries filtering ONLY by project_id without status. Both included per spec.

## Step 2: Add `__table_args__` to Agent model

**File:** `backend/app/models/agent.py`

`UniqueConstraint` already imported. Add `__table_args__`:
```python
__table_args__ = (
    UniqueConstraint("name", name="uq_agent_name"),
)
```

## Step 3: Add `__table_args__` to Project model

**File:** `backend/app/models/project.py`

Add `Index` to imports:
```python
from sqlalchemy import DateTime, Index, String, Text, func
```

Add `__table_args__`:
```python
__table_args__ = (
    Index("ix_projects_name", "name"),
)
```

## Step 4: Create Alembic migration

**File:** `backend/alembic/versions/xxxx_add_db_indexes_and_constraints.py`

Parent revision: `fa326b3a9bb1`

Migration contents:
- `op.create_index("ix_issues_project_id", "issues", ["project_id"])`
- `op.create_index("ix_issues_status", "issues", ["status"])`
- `op.create_index("ix_issues_priority", "issues", ["priority"])`
- `op.create_index("ix_issues_category", "issues", ["category"])`
- `op.create_index("ix_issues_name", "issues", ["name"])`
- `op.create_index("ix_issues_project_id_status", "issues", ["project_id", "status"])`
- `op.create_unique_constraint("uq_agent_name", "agents", ["name"])`
- `op.create_index("ix_projects_name", "projects", ["name"])`

Downgrade reverses all:
- `op.drop_index("ix_issues_project_id")` etc.
- `op.drop_constraint("uq_agent_name", "agents", type_="unique")`

## Step 5: Verify migration runs

```bash
cd backend
python -m alembic upgrade head
```

Confirm no errors. Migration should apply cleanly with `render_as_batch=True` for SQLite compatibility.

## Dependencies & Ordering
- Steps 1-3 (model changes) are independent — can be done in any order
- Step 4 (migration) must come after all model changes are saved
- Step 5 verifies everything works end-to-end
