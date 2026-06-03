## Implementation Plan: Drop FK Constraint on questions.issue_id

### Overview
Single Alembic migration to drop the foreign key constraint on `questions.issue_id → issues.id`. Issues are file-backed (`.manager_ai/issues/`), not stored in the DB `issues` table, so the FK causes `ask_user_question` MCP tool to fail with integrity errors.

---

### Step 1: Create Alembic migration

**File**: `backend/alembic/versions/XXXXXX_drop_questions_issue_id_fk.py`
**Depends on**: `04f837ab5823` (the migration that added the FK)

**Logic**:
- Use `op.batch_alter_table('questions')` (render_as_batch=True is already set in alembic/env.py)
- Use `sqlalchemy.inspect(op.get_bind())` to discover the auto-generated FK constraint name (the original migration had no explicit `name=` parameter)
- Drop only the FK referencing `issues` — preserve the FK on `project_id → projects.id`
- No data changes needed — constraint drop is metadata-only for SQLite

**Pseudocode**:
```python
def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    
    with op.batch_alter_table('questions') as batch_op:
        for fk in inspector.get_foreign_keys('questions'):
            if fk['referred_table'] == 'issues':
                batch_op.drop_constraint(fk['name'], type_='foreignkey')


def downgrade():
    with op.batch_alter_table('questions') as batch_op:
        batch_op.create_foreign_key(
            None, 'issues', ['issue_id'], ['id']
        )
```

### Step 2: Create revision ID and update down_revision chain

- Run `alembic revision --autogenerate -m "drop_questions_issue_id_fk"` OR write migration manually
- Set `down_revision = '04f837ab5823'`
- Verify chain: `... → 9a752a193fcf → 04f837ab5823 → [NEW MIGRATION]`

### Step 3: Test the migration

- Apply: `python -m alembic upgrade head`
- Verify `ask_user_question` MCP tool creates questions without FK error
- Run existing test suite: `python -m pytest`
- Verify `QuestionService.get_all()` and `get_pending()` still work (outer joins to issues table return nulls for file-backed issues)

### Files to Create
- `backend/alembic/versions/XXXXXX_drop_questions_issue_id_fk.py`

### Files to Modify
- None — no Python code changes needed

### Dependencies & Constraints
- **No model changes**: Question model (`app/models/question.py:16`) already has `issue_id` as plain `Mapped[str]` without ForeignKey
- **No service changes**: QuestionService and MCP tools unchanged
- **Preserve**: FK on `project_id` must remain (projects are DB-backed)
- **Batch mode**: SQLite requires batch mode for constraint drops — confirmed enabled in alembic/env.py
- **Inspector**: Must use `sqlalchemy.inspect()` to discover auto-generated FK name since original migration specified no explicit constraint name