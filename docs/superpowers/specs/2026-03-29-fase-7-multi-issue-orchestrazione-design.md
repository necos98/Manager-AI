# Fase 7 — Multi-Issue & Orchestrazione: Design Spec

Data: 2026-03-29

---

## Overview

Fase 7 aggiunge quattro macro-funzionalità a Manager AI, implementate in sequenza per dipendenze crescenti:

1. **7.1 Kanban Board** — sostituisce la lista issue con una vista Kanban drag-and-drop
2. **7.2 Issue Collegate** — relazioni tra issue (blocca/correlata) con grafo visivo interattivo
3. **7.3 Multi-project Dashboard** — vista globale delle issue attive cross-progetto
4. **7.4 Terminal Grid** — layout dinamico per terminali multipli contemporanei

---

## Architettura generale

```
7.1 Kanban        → solo frontend, zero modifiche al DB
7.2 Issue collegate → nuovo modello DB + API + frontend
7.3 Multi-project → solo frontend + query aggregate (read-only)
7.4 Terminal grid  → solo frontend (layout dinamico CSS grid)
```

**Nuove dipendenze npm:**
- `@dnd-kit/core` + `@dnd-kit/sortable` — drag-and-drop per Kanban
- `reactflow` — grafo interattivo per issue collegate
- `@dagrejs/dagre` — layout automatico top-down per il grafo

---

## 7.1 Kanban Board

### Comportamento

La vista Kanban **sostituisce** completamente la lista issue nella route `/projects/$projectId/issues/`. Non esiste più il toggle lista/Kanban.

### Colonne

Una colonna per ogni stato: `New`, `Reasoning`, `Planned`, `Accepted`, `Finished`, `Canceled`.

### Componenti

```
KanbanBoard
├── KanbanFilters          (priorità dropdown, ricerca testo, ordinamento)
├── KanbanColumn (x6)
│   └── KanbanCard         (per ogni issue nella colonna)
```

**`KanbanCard`** mostra:
- Nome issue (o descrizione troncata se name è null)
- Priority badge (`P1`–`P5`)
- Task progress bar (`completed/total`)
- Icona terminale attivo (verde, come nella lista attuale)
- Badge "Bloccata" rosso se ha dipendenze non finite (aggiunto in 7.2)

### Drag-and-drop (`@dnd-kit`)

- `DndContext` wrappa l'intera board
- Ogni `KanbanCard` è un `Draggable`
- Ogni `KanbanColumn` è un `Droppable`
- Al drop su colonna diversa → apre la **modale di conferma** già esistente in `IssueActions` (stessa UX dei pulsanti di transizione)
- Transizioni non valide (es. `New → Finished`): la colonna non accetta visivamente il drag (overlay rosso, drop ignorato)
- **Optimistic update:** la card si sposta subito; se la chiamata API fallisce, torna alla colonna originale

### Filtri e ricerca

- **Ricerca full-text:** filtro lato client su `name` + `description`. Per spec e piano, ricerca lato server via query param `?search=` aggiunto all'endpoint `GET /api/projects/{id}/issues`
- **Filtro priorità:** dropdown multi-select (1–5), lato client
- **Ordinamento:** `created_at` / `updated_at` / `priority`, lato client

---

## 7.2 Issue Collegate

### Modello dati

Nuova tabella `issue_relations`:

```python
class RelationType(str, enum.Enum):
    BLOCKS = "blocks"    # source blocca target (direzionale)
    RELATED = "related"  # correlata (logicamente bidirezionale)

class IssueRelation(Base):
    __tablename__ = "issue_relations"
    id: int  # PK autoincrement
    source_id: str  # FK → issues.id, cascade delete
    target_id: str  # FK → issues.id, cascade delete
    relation_type: RelationType
    created_at: datetime
```

**Vincoli (validati nel service layer):**
- `source_id != target_id` (no self-relation)
- Per `related`: `source_id < target_id` alfabeticamente (evita duplicati bidirezionali)
- No cicli per `blocks`: se A→B e B→C, non si può aggiungere C→A (DFS sul grafo prima del salvataggio)

### API

```
GET    /api/issues/{id}/relations          → lista relazioni (source e target)
POST   /api/issues/{id}/relations          → body: { target_id, relation_type }
DELETE /api/issues/{id}/relations/{rel_id} → rimuovi relazione
```

### Enforcement hook

In `auto_start_workflow` e `auto_start_implementation`: prima di avviare, `IssueRelationService.get_blockers(issue_id)` ritorna le issue con `relation_type=blocks` e `target_id=issue.id`. Se uno qualsiasi non è `FINISHED`, lo hook si ferma e logga un `ActivityLog` con tipo `issue_blocked`.

### Frontend — tab "Relations"

Nuovo tab nell'`IssueDetail` (accanto a Spec/Plan/Tasks).

**Grafo con `reactflow` + layout dagre:**
- Nodo centrale = issue corrente (colore primario)
- Nodi adiacenti = issue collegate (colore secondario)
- Edges colorati: rosso per `blocks`, grigio per `related`
- Frecce direzionali per `blocks`, linee non direzionali per `related`
- Click su nodo → naviga all'issue corrispondente
- Layout automatico top-down via dagre

**UI aggiunta relazione** (sopra il grafo):
```
[Cerca issue ▼]  [blocca / correlata ▼]  [Aggiungi]
```
- Dropdown ricerca issue dello stesso progetto (esclude issue già collegate e se stessa)
- Rimozione: pulsante X su ogni nodo adiacente nel grafo, o lista testuale sotto

**Indicatore blocco:** in `KanbanCard` e nell'header di `IssueDetail`, badge rosso "Bloccata" con tooltip che lista i nomi delle issue bloccanti non ancora finite.

---

## 7.3 Multi-project Dashboard

### Route

Nuova route `/dashboard`, voce nella sidebar globale.

### Contenuto

Lista di tutti i progetti. Per ciascuno:
- Nome progetto (link a `/projects/$projectId/issues`)
- Conteggio issue per stato (badge colorati per stato)
- Issue attive (non Finished/Canceled) elencate con nome, stato, priority
- Indicatore "In lavorazione" se esiste un hook in esecuzione (evento `hook_started` non ancora chiuso)

### Backend

Nuovo endpoint: `GET /api/projects/dashboard` — ritorna tutti i progetti con le loro issue non finite (`status NOT IN ['Finished', 'Canceled']`), usando le query già disponibili in `ProjectService` e `IssueService`.

### UX

Nessuna paginazione inizialmente (lista scrollabile). Se un progetto non ha issue attive, mostra "Nessuna issue attiva" invece di ometterlo.

---

## 7.4 Terminal Grid

### Comportamento

Nella route `/terminals`, il layout passa da un singolo pannello fisso a una **CSS grid dinamica** basata sul numero di terminali aperti:

| Terminali aperti | Layout |
|---|---|
| 1 | full width |
| 2 | 2 colonne 50/50 |
| 3–4 | 2 colonne, rows automatiche |
| 5+ | 3 colonne, rows automatiche |

### Implementazione

- CSS: `grid-template-columns: repeat(auto-fill, minmax(500px, 1fr))`
- Ogni cella è un `TerminalPanel` wrappato in un container con header
- Header: nome issue + nome progetto + pulsante chiudi (× che chiude il terminale via `DELETE /api/terminals/{id}`)
- `ResizeObserver` su ogni cella per aggiornare `cols`/`rows` del PTY al resize
- Nessuna libreria aggiuntiva

### Context switching rapido

Sidebar "Terminali attivi" (già presente nella route `/terminals`) mostra la lista; click porta in focus visivo il terminale corrispondente scrollando/evidenziando la cella.

---

## Error handling

| Scenario | Comportamento |
|---|---|
| Drop su transizione invalida | Drop ignorato, colonna mostra overlay rosso temporaneo |
| API fallisce dopo optimistic update Kanban | Card torna alla colonna originale, toast rosso |
| Aggiunta relazione con ciclo | Errore 422 dal service, toast "Creerebbe una dipendenza circolare" |
| Hook bloccato da dipendenze | ActivityLog `issue_blocked`, nessun crash, issue resta nello stato attuale |
| Terminal grid: PTY crash | Cella mostra "Terminale disconnesso" con pulsante "Riconnetti" |

---

## Testing

- **Kanban:** test per `IssueRelationService.detect_cycle()` (unit test), test optimistic update rollback (React Testing Library)
- **Issue relations:** test API CRUD relazioni, test enforcement blocco in hook, test ciclo detection
- **Dashboard:** test endpoint aggregate, snapshot test componente
- **Terminal grid:** test resize handler, nessun test PTY aggiuntivo (già coperti)
