## Summary
Aggiunto sistema di categorizzazione issue con categorie predefinite, singola selezione, opzionale.

## Categorie
Bug, Feature, Improvement, Documentation, Refactor, Security, Performance, UI/UX

## Modifiche

### Backend
- **Model**: Aggiunto `category` (String(50), nullable) a `Issue` + costante `ALLOWED_CATEGORIES` in `backend/app/models/issue.py`
- **Storage**: Aggiunto `category` a `IssueRecord` dataclass, `_to_index_entry()`, `_index_to_light_record()`, `_record_to_payload()`, `_write_issue_record()`, `rebuild_issues_index()`, `load_issue()` in `backend/app/storage/issue_store.py`
- **Schemas**: Aggiunto `category` a `IssueCreate`, `IssueUpdate`, `IssueResponse` (con `from_record`) in `backend/app/schemas/issue.py`
- **Service**: Validazione categoria in `create()` e `update_fields()` contro `ALLOWED_CATEGORIES` in `backend/app/services/issue_service.py`
- **Router**: Passa `category` da `IssueCreate` a `service.create()` in `backend/app/routers/issues.py`
- **Migration**: `f75dc9e9f3ff_add_category_to_issues.py` — batch ALTER TABLE per SQLite

### Frontend
- **Types**: Aggiunto `category` a `Issue`, `IssueCreate`, `IssueUpdate` in `frontend/src/shared/types/index.ts`
- **NewIssueDialog**: Dropdown Select per categoria opzionale
- **IssueDetail**: Select inline per cambiare categoria nell'header
- **IssueList**: Badge categoria nella riga lista
- **KanbanCard**: Badge categoria nella card kanban

### Fix collaterale
- Corretto `down_revision` in `04f837ab5823_add_questions_table.py` da `6fbb705de97e` (inesistente) a `9a752a193fcf` per riparare la catena Alembic rotta

## Test
- 160 test issue: tutti passati
- Frontend build: successo
- 1 test pre-esistente fallito (`test_db_backup.py`) — non correlato