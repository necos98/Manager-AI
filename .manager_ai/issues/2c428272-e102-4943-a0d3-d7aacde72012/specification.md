# Issue Tagging & Grouping — Specifica

## Obiettivo
Permettere all'utente di assegnare uno o più tag testuali liberi a ogni issue, e filtrare le issue per tag nella lista.

## Data Model

### Issue YAML
Aggiungere campo `tags` (lista di stringhe) nel frontmatter YAML di ogni issue:
```yaml
tags: [backend, ricerca semantica]
```
Campo opzionale, default `[]`.

### IssueRecord (issue_store.py)
Nuovo campo: `tags: list[str] = field(default_factory=list)`

### Schemas (schemas/issue.py)
- `IssueResponse`: aggiungere `tags: list[str] = []`
- `IssueCreate`: aggiungere `tags: list[str] | None = None`
- `IssueUpdate`: aggiungere `tags: list[str] | None = None`

### Frontend Types (types/index.ts)
- `Issue`: aggiungere `tags: string[]`
- `IssueCreate`: aggiungere `tags?: string[]`
- `IssueUpdate`: aggiungere `tags?: string[]`

## API

### GET /api/projects/{project_id}/tags (NUOVO)
Ritorna lista di tutti i tag univoci usati nel progetto, ordinati alfabeticamente.
Scansiona tutti gli issue YAML, estrae i tag, deduplica.
Risposta: `["backend", "frontend", "ricerca semantica"]`

### GET /api/projects/{project_id}/issues (MODIFICA)
Nuovo query param opzionale `tag: str | None`.
Se fornito, filtra le issue che contengono quel tag nella lista `tags`.
Combinabile con `status` e `search` esistenti.

### IssueUpdate / PUT /api/projects/{project_id}/issues/{id} (MODIFICA)
Supportare campo `tags` nell'update payload.
Se fornito, sovrascrive la lista tag dell'issue.

## Frontend

### NewIssueDialog
Nuovo campo "Tags" sotto Priority.
- Input testuale con autocomplete: dropdown mostra tag esistenti del progetto che matchano il testo
- Se il testo non matcha alcun tag esistente, mostrare opzione "Crea 'testo'"
- Tag selezionati appaiono come chips con `×` per rimuoverli
- Usa nuovo hook `useProjectTags(projectId)`

### IssueDetail header
- Chips dei tag visualizzati accanto allo StatusBadge
- Click su un tag chip → naviga a `/projects/$projectId/issues?tag=...`
- Bottone `+` per aggiungere tag inline (apre mini-input con autocomplete)

### IssueList
- Dropdown filtro in cima: `Select` con tutti i tag univoci del progetto + opzione "All tags"
- Selezionando un tag, le issue nella lista vengono filtrate lato server (query param `tag`)
- Il dropdown mostra il conteggio issue per tag (opzionale, nice-to-have)

### Nuovo hook: useProjectTags
```typescript
useProjectTags(projectId: string) → { data: string[], ... }
```
Chiama `GET /api/projects/{project_id}/tags`.

### Hook modificati
- `useIssues`: accetta nuovo param `tag?: string`
- `useUpdateIssue`: supporta `tags` nel mutation payload
- `useCreateIssue`: supporta `tags` nel payload iniziale

## Comportamento

- **Tag sono case-insensitive**: `Backend` e `backend` sono lo stesso tag (normalizzati lowercase)
- **Tag vuoti ignorati**: stringhe vuote o solo whitespace non vengono salvate
- **Massimo 20 tag per issue**: limite arbitrario per evitare abuso
- **Massimo 50 caratteri per tag**
- **I tag sopravvivono senza issue**: un tag rimosso dall'ultima issue scompare dalla lista automaticamente (nessuna tabella tag separata)
