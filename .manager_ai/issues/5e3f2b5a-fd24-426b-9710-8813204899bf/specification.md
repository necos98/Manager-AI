# Race Condition: duplicazione dell'ordine FIFO in IssueQueueService.register()

## Problema

Il metodo `IssueQueueService.register()` apre una `async with async_session() as session:` per ogni chiamata. Due chiamate concorrenti a `register()` (ad es. due `queue_add` simultanei per lo stesso progetto) creano sessioni/transazioni separate. Entrambe leggono lo stesso `max(QueueEntry.order)` — perché nessuna delle due ha ancora committato — e assegnano lo stesso `order = max_order + 1`. Il risultato: due `QueueEntry` con ordine identico, rompendo la garanzia FIFO.

## Root Cause

- `register()` usa una sessione SQLAlchemy dedicata per ogni chiamata (standard pattern).
- SQLite + aiosqlio non supportano `SELECT ... FOR UPDATE`.
- Non esiste un vincolo `UNIQUE(project_id, order)` sulla tabella `queue_entries` che possa rilevare o prevenire il conflitto.
- Non esiste un lock applicativo per serializzare le registrazioni per-progetto.

## Soluzione

### Primaria: Lock applicativo per-progetto in register()

`asyncio.Lock` per-progetto esattamente come già fatto per `_dequeue_and_run()` (che usa `self._dequeue_locks`). Aggiungere un `self._register_locks: dict[str, asyncio.Lock]` e avvolgere il body di `register()` in `async with self._get_register_lock(project_id):`.

**Vantaggi:**
- Pattern già consolidato e testato nella stessa classe (campo `_dequeue_locks`).
- Nessun cambiamento DB schema o migrazione.
- Overhead trascurabile: lock conteso solo durante window di commit.

### Secondaria (difesa in profondità): unique constraint

Aggiungere un vincolo `UniqueConstraint(project_id, order)` sulla tabella `queue_entries` come migrazione Alembic, così anche se il lock fallisce (o viene rimosso in futuro), il DB impedisce duplicati. Opzionale ma consigliato come safety net.

## Non-goals

- **Non toccare** `_dequeue_and_run()` — ha già il suo lock e funziona correttamente.
- **Non modificare** `list_queue()`, `get_next_pending()`, `mark_*()` — sono letture singole o hanno già logica safe.
- **Non cambiare** il modello concorrenziale (ogni metodo apre la propria sessione) — è corretto, mancava solo il lock per la race window in register().
