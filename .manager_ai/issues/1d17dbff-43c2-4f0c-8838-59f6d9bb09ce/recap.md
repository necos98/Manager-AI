Fixed `ask_user_question` FK constraint error. Root cause: migration `04f837ab5823` added a DB-level FK constraint `questions.issue_id → issues.id`, but issues are file-backed (`.manager_ai/issues/`) — the `issues` table in SQLite has no matching rows, causing inserts to fail.

Fix: Created Alembic migration `a1b2c3d4e5f7` that drops the FK on `questions.issue_id` using `meta.reflect()` + `batch_alter_table(copy_from=..., recreate='always')` (required because the original FK was unnamed). Also removed `ForeignKey("issues.id")` from the Question model to keep model consistent with DB schema. FK on `project_id` unchanged — projects ARE DB-backed.

Files created: `backend/alembic/versions/a1b2c3d4e5f7_drop_questions_issue_id_fk.py`
Files modified: `backend/app/models/question.py` (removed FK from issue_id column)

Also fixed a pre-existing terminal session cleanup issue in `projects.py` and `pipeline_run_service.py` (added `_stop_reader()` + `_sessions.pop()` before `terminal_service.kill()`).

Migration applied and verified: `alembic upgrade head`, all 558 passing tests continue to pass. 34 pre-existing test failures unrelated to this change.