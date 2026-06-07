# PK Unification: Auto-Increment Integers with UUID Columns

## Scope

Convert all SQLAlchemy models from mixed PK scheme (19 UUID String(36), 5 auto-increment Integer) to uniform auto-increment Integer PKs with separate `uuid` String(36) unique column for external references.

**In scope:** SQLAlchemy model definitions, Alembic migration, data backfill
**Out of scope:** API routes/schemas/DTOs (continue exposing UUIDs), frontend changes, Setting model (string-key PK, no change needed)

---

## 1. Target Schema — All 24 Tables

### 1.1 UUID-PK Tables (19) — Convert to Integer PK + uuid column

Each table gains:
- `id`: Integer, auto-increment, primary key (exception: memory_links keeps its composite PK — see 4.5)
- `uuid`: String(36), unique, non-null, indexed (for API lookups)
- All FK columns referencing this table change from String(36) to Integer

Full per-table mapping:

| # | Table | New PK | uuid | FK Ref Columns (change to int) | Notes |
|---|-------|--------|------|-------------------------------|-------|
| 1 | projects | Integer, auto | String(36) uq idx | project_id in issues, project_files, memories, questions, activity_logs, project_variables, terminal_commands, (project_credentials, project_skills, prompt_templates stay string — no FK) | |
| 2 | issues | Integer, auto | String(36) uq idx | issue_id in tasks, issue_feedback, issue_relations | |
| 3 | agents | Integer, auto | String(36) uq idx | agent_id in pipeline_steps | |
| 4 | tasks | Integer, auto | String(36) uq idx | (none) | |
| 5 | pipelines | Integer, auto | String(36) uq idx | pipeline_id in pipeline_steps, pipeline_runs, pipeline_event_rules | |
| 6 | pipeline_steps | Integer, auto | String(36) uq idx | pipeline_step_id in pipeline_step_runs, pipeline_event_rules(source/target) | Also pipeline_id, agent_id FKs change to int |
| 7 | pipeline_runs | Integer, auto | String(36) uq idx | pipeline_run_id in pipeline_step_runs, pipeline_messages | issue_id stays String(255) — no FK, references external system |
| 8 | pipeline_step_runs | Integer, auto | String(36) uq idx | (none) | Also pipeline_run_id, pipeline_step_id FKs change to int |
| 9 | pipeline_messages | Integer, auto | String(36) uq idx | (none) | |
| 10 | pipeline_event_rules | Integer, auto | String(36) uq idx | (none) | Also pipeline_id, source_step_id, target_step_id FKs change to int |
| 11 | memories | Integer, auto | String(36) uq idx | (none external) | parent_id self-ref FK changes to Integer |
| 12 | memory_links | **None (composite PK)** | String(36) uq idx | (none) | from_id, to_id FKs change to Integer within composite PK. No new auto-increment id — table uses composite PK (from_id, to_id, relation) |
| 13 | project_files | Integer, auto | String(36) uq idx | (none) | |
| 14 | questions | Integer, auto | String(36) uq idx | (none) | issue_id stays String(36) — no FK, references external issues |
| 15 | activity_logs | Integer, auto | String(36) uq idx | (none) | issue_id stays String(36) — no FK, audit trail |
| 16 | issue_feedback | Integer, auto | String(36) uq idx | (none) | |
| 17 | project_credentials | Integer, auto | String(36) uq idx | (none) | project_id stays String(36) — no FK |
| 18 | project_links | Integer, auto | String(36) uq idx | (none) | source_project_id, target_project_id FKs change to int |
| 19 | credential_presets | Integer, auto | String(36) uq idx | (none) | |

### 1.2 Integer-PK Tables (5) — Add uuid column only

These already have auto-increment Integer id. Only add `uuid` String(36) unique column:

| # | Table | Current PK | uuid | Notes |
|---|-------|-----------|------|-------|
| 20 | issue_relations | Integer, auto | String(36) uq idx | source_id, target_id FKs to issues.id — change to Integer |
| 21 | project_skills | Integer, auto | String(36) uq idx | project_id stays String(36) — no FK |
| 22 | project_variables | Integer, auto | String(36) uq idx | project_id FK changes to Integer |
| 23 | prompt_templates | Integer, auto | String(36) uq idx | project_id stays String(36) — no FK, nullable |
| 24 | terminal_commands | Integer, auto | String(36) uq idx | project_id FK changes to Integer (nullable) |

### 1.3 Excluded

- **Setting** — uses string `key` as PK, not involved in joins. No change.

---

## 2. FK Migration Strategy

### 2.1 FKs to Change (String(36) → Integer)

All columns below currently reference a String(36) PK and must become Integer. The Integer value is the new `id` of the parent row — lookup is via the parent's new sequential id.

| Child Table | FK Column | References | Nullable? |
|-------------|-----------|-----------|-----------|
| issues | project_id | projects.id | No |
| tasks | issue_id | issues.id | No |
| pipeline_steps | pipeline_id | pipelines.id | No |
| pipeline_steps | agent_id | agents.id | No |
| pipeline_runs | pipeline_id | pipelines.id | No |
| pipeline_step_runs | pipeline_run_id | pipeline_runs.id | No |
| pipeline_step_runs | pipeline_step_id | pipeline_steps.id | No |
| pipeline_messages | pipeline_run_id | pipeline_runs.id | No |
| pipeline_event_rules | pipeline_id | pipelines.id | No |
| pipeline_event_rules | source_step_id | pipeline_steps.id | No |
| pipeline_event_rules | target_step_id | pipeline_steps.id | No |
| memories | project_id | projects.id | No |
| memories | parent_id | memories.id | Yes (self-ref) |
| memory_links | from_id | memories.id | No (PK part) |
| memory_links | to_id | memories.id | No (PK part) |
| project_files | project_id | projects.id | No |
| questions | project_id | projects.id | No |
| activity_logs | project_id | projects.id | No |
| issue_feedback | issue_id | issues.id | No |
| issue_relations | source_id | issues.id | No |
| issue_relations | target_id | issues.id | No |
| project_variables | project_id | projects.id | No |
| terminal_commands | project_id | projects.id | Yes |
| project_links | source_project_id | projects.id | No |
| project_links | target_project_id | projects.id | No |

### 2.2 String Reference Columns — Keep As-Is

These columns hold UUID strings referencing external `.manager_ai/` issues or have no FK constraint. Do NOT convert to Integer:

| Table | Column | Rationale |
|-------|--------|-----------|
| pipeline_runs | issue_id | External .manager_ai issue system, String(255) |
| questions | issue_id | References file-backed issues, no FK |
| activity_logs | issue_id | Audit trail — must survive issue deletion, no FK |
| project_credentials | project_id | String(36), no FK constraint |
| project_skills | project_id | String(36), no FK constraint |
| prompt_templates | project_id | String(36), nullable, no FK constraint |

---

## 3. Data Backfill

> **Note:** The steps below describe the logical intent. For the actual SQLite-compatible implementation (rename+recreate for PK changes, careful ALTER for uuid only), see Section 5.1.

### 3.1 UUID-PK Tables

For each table:
1. Add `uuid` String(36) NOT NULL column
2. Copy existing `id` value into `uuid` for every row (current id IS the uuid)
3. Add new `id` Integer auto-increment PK column
4. SQLite auto-assigns sequential ids; the insertion order from step 1 preserves row identity
5. Create index on `uuid` column

Migration order: parent tables first (projects → issues → agents → pipelines → pipeline_steps → pipeline_runs → pipeline_step_runs → pipeline_messages → pipeline_event_rules → memories → memory_links → project_files → questions → activity_logs → issue_feedback → project_credentials → project_links → credential_presets)

### 3.2 Integer-PK Tables

For each table:
1. Add `uuid` String(36) column (nullable initially, or with a temporary DEFAULT — see Section 5.1 for SQLite constraint)
2. Generate a UUID for every existing row (Python uuid4)
3. Make the column NOT NULL (requires table recreation in SQLite — see Section 5.1)
4. Create unique index on `uuid`

### 3.3 FK Value Remapping

After backfilling primary tables with new Integer ids:
1. Build a lookup map: old_uuid → new_int_id for each parent table
2. For each child table FK column, update the String(36) FK value to the corresponding Integer id using the lookup map
3. Then alter the FK column type from String(36) to Integer

---

## 4. SQLAlchemy Model Changes

### 4.1 Pattern for UUID-PK Tables (except memory_links)

```python
# Before
id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

# After
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
```

### 4.2 Pattern for memory_links (composite PK — no new id column)

```python
# Before
from_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
to_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True, index=True)

# After
from_id: Mapped[int] = mapped_column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
to_id: Mapped[int] = mapped_column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True, index=True)
uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
```

### 4.3 Pattern for Integer-PK Tables

```python
# Before
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

# After (add uuid column)
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
```

### 4.4 FK Column Pattern

```python
# Before
project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)

# After
project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
```

### 4.5 Self-Referencing FK (Memory.parent_id)

```python
# Before
parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("memories.id", ondelete="SET NULL"), nullable=True, index=True)

# After
parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("memories.id", ondelete="SET NULL"), nullable=True, index=True)
```

### 4.6 Composite PK (MemoryLink)

```python
# Before
from_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
to_id: Mapped[str] = mapped_column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True, index=True)

# After
from_id: Mapped[int] = mapped_column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
to_id: Mapped[int] = mapped_column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True, index=True)
uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
```

### 4.7 Imports to Add

- `Integer` import to every model file that currently uses String(36) PKs (if not already imported)
- `uuid` import may be removed from files where it's only used for id generation (still needed if model uses uuid for other purposes)

### 4.8 Relationship Definitions

All `relationship()` definitions in models remain unchanged — SQLAlchemy resolves FKs by column name, not type. Foreign key references in relationship definitions like `ForeignKey("projects.id")` stay as strings — no code changes needed there.

---

## 5. Alembic Migration

### 5.1 Migration Approach

SQLite ALTER TABLE support is limited. This migration requires:

**For UUID-PK tables:**
1. Rename existing table → old_<table>
2. Create new table with Integer PK + uuid column
3. Copy data, generating uuid from old id
4. Update FK values in child tables using UUID → Integer lookup
5. Drop old table
6. Create indexes and unique constraints

**For Integer-PK tables (add uuid column only):**
1. ALTER TABLE ADD COLUMN uuid VARCHAR(36) — must be nullable initially since SQLite does not support ADD COLUMN with NOT NULL without a DEFAULT
2. UPDATE uuid = generated UUID (Python uuid4) per row
3. ALTER TABLE to set NOT NULL — requires the same rename+recreate pattern since SQLite cannot ALTER COLUMN. Alternative: create new table with desired schema, INSERT ... SELECT from old, drop old, rename new.
4. CREATE UNIQUE INDEX on uuid

> **Note:** For Integer-PK tables, the uuid column is added in TWO steps because SQLite cannot `ALTER TABLE ADD COLUMN ... NOT NULL` without a `DEFAULT`. Adding as nullable first, backfilling, then recreating the table with NOT NULL is the required pattern.

### 5.2 Migration Order

1. **projects** (most-referenced parent, no FKs TO other changing tables)
2. **agents**
3. **pipelines**
4. **memories** (self-ref parent_id → needs memories.id first, then update parent_id)
5. **issues** (FK to projects)
6. **pipeline_steps** (FKs to pipelines, agents)
7. **pipeline_runs** (FK to pipelines)
8. **pipeline_step_runs** (FKs to pipeline_runs, pipeline_steps)
9. **pipeline_messages** (FK to pipeline_runs)
10. **pipeline_event_rules** (FKs to pipelines, pipeline_steps)
11. **memory_links** (FKs to memories)
12. **project_files** (FK to projects)
13. **questions** (FK to projects)
14. **activity_logs** (FK to projects)
15. **issue_feedback** (FK to issues)
16. **project_links** (FKs to projects)
17. **project_variables** (FK to projects)
18. **terminal_commands** (FK to projects)
19. **issue_relations** (FKs to issues)
20. **tasks** (FK to issues)
21. **project_skills**, **prompt_templates**, **project_credentials**, **credential_presets** (no FK changes, add uuid only)

After all tables: create uuid indexes and unique constraints.

---

## 6. Service Layer Impact

### 6.1 Lookup Pattern

Services that look up records by UUID for API consumption must change from:

```python
# Before — id IS the uuid
record = await session.get(Model, uuid_str)

# After — id is Integer, uuid is separate
record = await session.execute(
    select(Model).where(Model.uuid == uuid_str)
)
result = record.scalar_one_or_none()
```

Or add a helper method:
```python
@classmethod
async def by_uuid(cls, session: AsyncSession, uuid_str: str) -> Self | None:
    result = await session.execute(select(cls).where(cls.uuid == uuid_str))
    return result.scalar_one_or_none()
```

### 6.2 API Layer

No changes required. All API routes currently pass UUID strings. Service layer translates uuid → query using `Model.uuid` column. Response DTOs continue to return UUID strings.

---

## 7. Acceptance Criteria

1. All 24 tables have unique, indexed `uuid` String(36) column (except Setting model)
2. All UUID-PK tables (18 of 19 — memory_links is special) have Integer auto-increment `id` PK column
3. MemoryLink keeps its composite PK (from_id, to_id, relation) with from_id, to_id converted to Integer
4. All FK columns reference Integer PKs correctly
5. Data integrity preserved: every row's uuid matches its previous String(36) id (for UUID-PK tables) or is a newly generated uuid (for Integer-PK tables)
6. String reference columns (issue_id in pipeline_runs, questions, activity_logs; project_id in project_credentials, project_skills, prompt_templates) remain String
7. All existing API endpoints continue working without modification
8. Alembic migration is reversible (downgrade restores UUID-PK scheme)
9. All tests pass

---

## 8. Non-Goals

- No API schema or DTO changes
- No frontend changes
- No Setting model changes
- No performance optimization beyond the PK change itself
- No adding/removing tables or columns beyond what's specified
- No changes to how UUIDs are generated for new records (still use uuid4)
- No adding an auto-increment `id` column to memory_links — it keeps its composite PK