# Specifica: Issue completate — ordine cronologico + paginazione

## Obiettivo
Nella colonna "Finished" della kanban board, mostrare le issue in ordine cronologico di chiusura (più recenti in cima), paginate a 10 per volta, con pulsante "Load more" per caricare le successive.

## Modifiche backend

### 1. Nuovo campo `finished_at` nel model Issue
- **File**: `backend/app/models/issue.py`
- Aggiungere `finished_at: Mapped[Optional[datetime]]` (nullable DateTime)
- Popolato solo quando l'issue passa a status `Finished` (in `complete_issue`)
- Serve per ordinamento cronologico di chiusura stabile (≠ `updated_at` che cambia a ogni modifica)

### 2. Nuovo campo in IssueRecord
- **File**: `backend/app/storage/issue_store.py`
- Aggiungere `finished_at: str | None = None` al dataclass `IssueRecord`
- Aggiornare `_to_index_entry`, `_index_to_light_record`, `_record_to_payload`, `_write_issue_record`, `rebuild_issues_index`

### 3. Nuovo campo in IssueResponse
- **File**: `backend/app/schemas/issue.py`
- Aggiungere `finished_at: datetime | None = None` a `IssueResponse`
- Aggiornare `from_record` per mappare il campo

### 4. Paginazione nell'endpoint list
- **File**: `backend/app/routers/issues.py`
- Aggiungere query params: `limit: int | None = None`, `offset: int = 0`
- Passarli al service

### 5. Logica di paginazione nel service
- **File**: `backend/app/services/issue_service.py`
- In `list_by_project`: quando `status == FINISHED`, ordinare per `finished_at DESC` (con fallback a `updated_at DESC` per issue completate prima della migration)
- Applicare slice `[offset : offset+limit]` solo quando `limit` è specificato
- Impostare `finished_at = _now_iso()` in `complete_issue()`

### 6. Frontend type
- **File**: `frontend/src/shared/types/index.ts`
- Aggiungere `finished_at: string | null` all'interfaccia `Issue`

### 7. API client
- **File**: `frontend/src/features/issues/api.ts`
- Aggiungere parametri `limit?` e `offset?` a `fetchIssues()`

### 8. Hook
- **File**: `frontend/src/features/issues/hooks.ts`
- Modificare `useIssues` per accettare e passare `limit` e `offset`

### 9. Kanban board
- **File**: `frontend/src/features/issues/components/kanban-board.tsx`
- Fetch separato per la colonna Finished: `useIssues(projectId, "Finished", undefined, undefined, 10, finishedOffset)`
- Stato locale `finishedOffset` che parte da 0
- Pulsante "Load more" in fondo alla colonna Finished che incrementa offset di 10
- Append dei nuovi risultati a quelli esistenti

### 10. Kanban column
- **File**: `frontend/src/features/issues/components/kanban-column.tsx`
- Accettare prop opzionale per "Load more" button e callback

## Comportamento atteso
1. La kanban board carica tutte le issue tranne le Finished come fa ora
2. La colonna Finished carica solo le ultime 10 issue completate (ordinamento: `finished_at DESC`)
3. In fondo alla colonna Finished, un pulsante "Load more" carica altre 10
4. Il page size di default è 10, configurabile via query param `limit`
5. Le issue completate prima di questa modifica avranno `finished_at = NULL` — in quel caso il fallback usa `updated_at DESC`

## Non fare
- Non cambiare il layout della kanban board
- Non modificare l'endpoint per stati diversi da Finished
- Non aggiungere paginazione lato server per altre colonne
- Non creare una nuova pagina separata
