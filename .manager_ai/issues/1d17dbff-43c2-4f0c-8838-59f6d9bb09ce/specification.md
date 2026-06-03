## Problem

`ask_user_question` MCP tool fails with foreign key constraint error when creating a question. Root cause: migration `04f837ab5823` added `ForeignKeyConstraint(['issue_id'], ['issues.id'])` to the `questions` table, but issues are stored as file-backed records (YAML+markdown under `.manager_ai/issues/`) — not in the SQL `issues` table. When `QuestionService.create()` calls `session.add(q)` + `session.commit()`, SQLite enforces the FK constraint and rejects the insert because no matching row exists in `issues.id`.

## Scope

Drop the FK constraint on `questions.issue_id`. That's it — one database migration.

## Details

- The `Question` SQLAlchemy model (`backend/app/models/question.py:16`) already declares `issue_id` as a plain `Mapped[str]` column with **no** `ForeignKey` — the model is correct
- Only the migration (`backend/alembic/versions/04f837ab5823_add_questions_table.py:33`) added the FK constraint as a DDL-level `ForeignKeyConstraint`
- The FK on `project_id` (`ForeignKey("projects.id")` at line 15 of the model) must be preserved — projects ARE stored in the DB
- `QuestionService.get_all()` (line 136-138) uses `outerjoin(Issue, Question.issue_id == Issue.id)` — this is a SQL-level join on column values, not dependent on the FK constraint. It continues working after the FK is dropped (outer join just returns nulls for unmatched issue_ids)

## Acceptance Criteria

1. `ask_user_question` MCP tool creates a question without FK constraint error
2. `QuestionService.get_pending()` and `get_all()` continue to work — outer joins to `issues` table simply return null for file-backed issues
3. FK on `project_id` is unchanged — project lookups still enforced
4. No Python code changes to models, services, or MCP tools

## Non-goals

- No changes to the Question SQLAlchemy model
- No changes to QuestionService
- No changes to the MCP `ask_user_question` tool
- No changes to issue storage
- No data migration (constraint drop is metadata-only for SQLite)

## Files Affected

- **New**: `backend/alembic/versions/XXXXXX_drop_questions_issue_id_fk.py` — migration to drop FK on `questions.issue_id`
