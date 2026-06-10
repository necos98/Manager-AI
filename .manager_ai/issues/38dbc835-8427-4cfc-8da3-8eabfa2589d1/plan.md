## Piano di implementazione: Bulk actions su Kanban board

### Task 1: Backend schemas per bulk operations
Aggiungere le classi Pydantic in `backend/app/schemas/issue.py`:
- `BulkStatusUpdate(issue_ids: list[str], status: IssueStatus)`
- `BulkTagsUpdate(issue_ids: list[str], tags: list[str], mode: Literal["add","remove","set"])`
- `BulkDeleteRequest(issue_ids: list[str])`
- `BulkPriorityUpdate(issue_ids: list[str], priority: int)`
- `BulkCategoryUpdate(issue_ids: list[str], category: str | None)`
- `BulkResponse(updated: int = 0, deleted: int = 0, errors: dict[str, str] = {})`

### Task 2: Backend service methods per bulk operations
Aggiungere in `backend/app/services/issue_service.py` i metodi:
- `bulk_update_status(project_id, issue_ids, status)` — itera chiamando `update_status`, raccoglie errori
- `bulk_update_tags(project_id, issue_ids, tags, mode)` — itera, aggiorna tags per ogni issue
- `bulk_delete(project_id, issue_ids)` — itera chiamando `delete`
- `bulk_update_priority(project_id, issue_ids, priority)` — itera chiamando `update_fields`
- `bulk_update_category(project_id, issue_ids, category)` — itera chiamando `update_fields`

### Task 3: Backend router per bulk operations
Creare `backend/app/routers/issues_bulk.py` con 5 endpoint PATCH/POST sotto `/api/projects/{project_id}/issues/bulk/`. Ognuno logga su ActivityService. Registrare il router in `main.py`.

### Task 4: Frontend API functions per bulk
Creare `frontend/src/features/issues/api-bulk.ts` con 5 funzioni:
- `bulkUpdateStatus(projectId, data)`, `bulkUpdateTags(projectId, data)`, `bulkDeleteIssues(projectId, data)`, `bulkUpdatePriority(projectId, data)`, `bulkUpdateCategory(projectId, data)`

### Task 5: Frontend hooks per bulk
Creare `frontend/src/features/issues/hooks-bulk.ts` con 5 useMutation hook, ciascuno invalida `issueKeys.all(projectId)`.

### Task 6: Select mode + checkbox su KanbanCard
- Aggiungere stato `selectMode` e `selectedIssueIds` a KanbanBoard
- Passare selectMode e selectedIssueIds a KanbanColumn → KanbanCard
- Aggiungere checkbox in KanbanCard visibile solo in selectMode
- Implementare toggle selezione, highlight visivo per card selezionata
- Pulsante "Select" nella toolbar di KanbanFilters / tra toolbar e board

### Task 7: BulkActionBar component
Creare `frontend/src/features/issues/components/bulk-action-bar.tsx` con:
- Count "N issues selected"
- Change Status dropdown (con validazione transizioni individuale)
- Assign Tags (TagInput + Add/Remove/Set mode)
- Change Priority (dropdown 1-5)
- Change Category (dropdown con categorie + None)
- Delete (pulsante rosso + dialogo conferma)
- Deselect all button

### Task 8: Select all in column
Aggiungere checkbox "Select all" nell'header di KanbanColumn in selectMode.
