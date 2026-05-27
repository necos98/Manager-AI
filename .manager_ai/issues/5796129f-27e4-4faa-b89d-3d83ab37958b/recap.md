## Riepilogo

Aggiunta paginazione nella colonna "Finished" della kanban board. Le issue completate sono ora ordinate per data di chiusura (più recenti in cima) e caricate 10 alla volta con pulsante "Load more".

### Modifiche backend (5 file)
- **Model**: aggiunto campo `finished_at` (DateTime nullable) su `Issue` — popolato quando l'issue viene completata
- **IssueRecord / IssueResponse**: aggiunto `finished_at`
- **Service**: `complete_issue()` imposta `finished_at = now()`. `list_by_project()` supporta `limit`/`offset` e ordina per `finished_at DESC` quando `status=Finished`
- **Router**: esposti query params `limit` e `offset`
- **Migration**: Alembic `5922b9fdc87a_add_finished_at_to_issues.py`

### Modifiche frontend (5 file)
- **Types**: `Issue.finished_at: string | null`
- **API / hooks**: `fetchIssues` e `useIssues` accettano `limit`/`offset`
- **KanbanBoard**: query separata per Finished con paginazione; accumulo risultati in `allFinished` state; reset su cambio tag
- **KanbanColumn**: accetta props opzionali `onLoadMore`, `hasMore`, `isLoadingMore` per il pulsante "Load more"

### Comportamento
1. La kanban carica tutte le issue NON-Finished come prima
2. La colonna Finished carica solo le ultime 10 issue completate
3. Pulsante "Load more" carica le successive 10
4. Cambio tag resetta la paginazione
5. Page size configurabile via query param `limit` (default 10)
6. Issue completate prima di questa modifica hanno `finished_at=NULL` e vengono ordinate per `updated_at` come fallback