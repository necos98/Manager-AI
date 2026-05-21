# Issue Tagging & Grouping — Recap

## Cosa è stato implementato

Aggiunto sistema di tagging per le issue con supporto multi-tag, filtro e autocomplete.

### Backend (4 file modificati)

1. **issue_store.py** — Aggiunto campo `tags: list[str]` al dataclass `IssueRecord`. Serializzazione in `_record_to_payload` e deserializzazione in `load_issue` dal frontmatter YAML.

2. **schemas/issue.py** — Aggiunto `tags` a `IssueCreate`, `IssueUpdate`, `IssueResponse` (con `from_record`).

3. **issue_service.py** — Helper `_normalize_tags()` (lowercase, trim, deduplica, max 50 char, max 20 tag). Integrato in `create()` e `update_fields()`. Nuovo metodo `get_project_tags()` per aggregare tag univoci. Parametro `tag` in `list_by_project()` per filtro.

4. **issues.py** — Nuovo endpoint `GET /tags` (prima di `/{issue_id}` per evitare collisione path). Parametro `tag` in `list_issues`.

### Frontend (6 file modificati/creati)

5. **types/index.ts** + **api.ts** + **hooks.ts** — Aggiunto `tags` alle interfacce TypeScript. `fetchProjectTags()`, `fetchIssues` con param `tag`. Hook `useProjectTags`.

6. **tag-input.tsx** (nuovo) — Componente autocomplete multi-tag con chips Badge, dropdown suggerimenti, creazione inline nuovi tag, rimozione con X o backspace.

7. **new-issue-dialog.tsx** — TagInput sotto Priority nel form di creazione issue. Tags passati nella mutation.

8. **issue-detail.tsx** — Chips tag cliccabili (navigano a `?tag=...`) accanto a StatusBadge. Bottone `+` per aggiungere tag inline.

9. **kanban-filters.tsx** + **kanban-board.tsx** + **issues/index.tsx** — Dropdown filtro tag. Tag letto da URL search params, passato a `useIssues` per filtro server-side.

## Decisioni prese

- **Multi-tag, non single-tag** — L'utente ha scelto flessibilità su semplicità
- **Tag come stringhe in YAML, non entità separate** — Allineato all'architettura file-based, nessuna tabella separata
- **Tag normalizzati lowercase** — Case-insensitive per evitare duplicati (es. "Backend" = "backend")
- **Limiti: 20 tag/issue, 50 char/tag** — Protezione da abuso senza complicare l'UI
- **Filtro server-side via `?tag=`, non client-side** — Consistente con search e status esistenti
- **URL-driven tag filter** su KanbanBoard — Click su tag chip in IssueDetail naviga aggiornando URL, consistente con pattern SPA

## Test

- Backend: 181/182 test passano (1 fallimento pre-esistente in `test_db_backup.py`)
- Frontend: TypeScript compila senza errori
