# Issue Categorization System

## Overview

Aggiungere campo `category` alle issue per classificarle. Categorie predefinite, singola selezione, opzionale.

## Categorie disponibili

```
Bug, Feature, Improvement, Documentation, Refactor, Security, Performance, UI/UX
```

## Implementation

### 1. Database

- **Migration**: `ALTER TABLE issues ADD COLUMN category VARCHAR(50)` (nullable, default NULL)
- **Issue model** (`backend/app/models/issue.py`): Aggiungere `category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)`

### 2. Storage layer (`backend/app/storage/issue_store.py`)

- `IssueRecord` dataclass: aggiungere `category: str | None = None`
- `_to_index_entry()`: includere `category`
- `_index_to_light_record()`: includere `category`
- `_record_to_payload()`: includere `category`
- `_write_issue_record()`: scrivere `category` nel YAML
- `rebuild_issues_index()`: leggere `category` dai dati YAML

### 3. Schemas (`backend/app/schemas/issue.py`)

- `IssueCreate`: aggiungere `category: str | None = None` con validazione contro lista consentita
- `IssueUpdate`: aggiungere `category: str | None = None` con validazione
- `IssueResponse`: aggiungere `category: str | None`

### 4. Validazione

Definire `ALLOWED_CATEGORIES` in `backend/app/models/issue.py`:
```python
ALLOWED_CATEGORIES = {
    "Bug", "Feature", "Improvement", "Documentation",
    "Refactor", "Security", "Performance", "UI/UX"
}
```
Validare in `IssueService.update_fields()` quando viene impostato category.

### 5. Service (`backend/app/services/issue_service.py`)

- `create()`: passare `category` al `IssueRecord` constructor
- `update_fields()`: validare category contro `ALLOWED_CATEGORIES` se presente

### 6. Router — nessuna modifica necessaria. `update_issue` usa gia `update_fields` pass-through.

### 7. Frontend

#### Types (`frontend/src/shared/types/index.ts`)
- `Issue` interface: aggiungere `category: string | null`
- `IssueCreate`: aggiungere `category?: string | null`
- `IssueUpdate`: aggiungere `category?: string | null`

#### New Issue Dialog (`frontend/src/features/issues/components/new-issue-dialog.tsx`)
- Aggiungere `Select` dropdown per category (opzionale) sotto Priority

#### Issue Detail (`frontend/src/features/issues/components/issue-detail.tsx`)
- Mostrare category badge vicino a StatusBadge
- Permettere inline edit della category (Select dropdown)

#### Issue List / Kanban
- Mostrare category badge nelle card per filtering visivo

### 8. API layer frontend
- `createIssue()`: includere `category` nel body
- `updateIssue()`: supportare `category` nel payload

## Test plan

- Unit: validazione category in `test_routers_issues.py`
- Unit: `test_issue_store.py` per category in payload/index roundtrip
- Frontend: verificare dropdown category in new-issue-dialog e issue-detail
