## Recap

Added missing DB indexes and constraints to 3 models:

### Changes
- **issue.py** — 6 indexes: project_id, status, priority, category, name, composite (project_id, status)
- **agent.py** — UniqueConstraint on name (uq_agent_name)
- **project.py** — Index on name (ix_projects_name)
- **Migration** `b5e9f3d2c4a6` from head fa326b3a9bb1

### Verification
- All indexes + constraint confirmed in SQLite
- Models import without errors
- Alembic head = b5e9f3d2c4a6

### Note
Pipeline failed early during migration (SQLite batch mode issue on first attempt). All implementation tasks completed despite pipeline failure state.