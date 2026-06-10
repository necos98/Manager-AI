# Issue Queue System — Specifica Tecnica

## 1. Overview

Aggiungere una coda FIFO sincrona per le issue di Manager AI. Le issue vengono accodate con status `QUEUED` e vengono eseguite **una per volta** in ordine di `created_at`. Appena una issue termina (status `FINISHED`), la successiva in coda parte automaticamente via `run_issue()`.

L'intero sistema è event-driven — nessun polling, nessun worker esterno.

## 2. Architettura

### 2.1 Nuovo status: `QUEUED`

Aggiungere `QUEUED = "Queued"` all'enum `IssueStatus` in `app/models/issue.py`.

**Transizioni consentite:**
- `NEW → QUEUED` — issue nuova messa in coda
- `ACCEPTED → QUEUED` — issue già pianificata ma rimandata
- `QUEUED → CANCELED` — rimossa manualmente dalla coda
- `QUEUED → REASONING` — quando la coda la fa partire automaticamente

Il `update_status()` in `IssueService` non fa validazione delle transizioni (usa `update_fields`), quindi l'enforcement è a livello MCP tool, non nel service. Aggiungeremo un helper di validazione in `shared_tools.py`.

### 2.2 IssueQueueService (event listener)

Nuovo file `app/services/issue_queue_service.py` — un `BaseNotifier` che si registra su `EventService` (come `NotificationService` e `TelegramNotifier`).

**Pattern:**
```python
class IssueQueueService(BaseNotifier):
    def __init__(self):
        event_service.register(self)

    async def notify(self, event: dict):
        if event.get("type") == "issue_status_changed" and event.get("new_status") == "Finished":
            asyncio.create_task(self._dequeue_and_run(event))
```

**Metodo `_dequeue_and_run(event)`:**
1. Legge `project_id` dall'evento
2. Query tutte le issue con status `QUEUED` per quel progetto, ordinate per `created_at` ASC
3. Se non ci sono QUEUED → esce
4. Se ce n'è almeno una → prende la prima (più vecchia)
5. Cambia il suo status da `QUEUED` a `REASONING` (perché `run_issue()` non parte da QUEUED — il workflow normale vuole che l'agente starti da New/Reasoning)
6. Chiama `run_issue(project_id, issue_id)` via il servizio `run_issue_service`

**Edge case: QUEUED fallisce.** Se la run fallisce (errore terminale, agente non parte), il listener dovrebbe gestire anche `FAILED`? Per ora: no — `run_issue()` crea un terminale e ritorna subito. Il fallimento sarebbe visibile in UI. Se si vuole skip automatico su fallimento, sarà una estensione futura.

### 2.3 MCP Tools (su orchestrator)

4 nuovi tool in `app/mcp/shared_tools.py` e registrati su `orchestrator_server.py`:

#### `queue_add(project_id, issue_id)`
- Validazione: issue deve esistere ed essere in status `NEW` o `ACCEPTED`
- Imposta status a `QUEUED`
- Emette evento `issue_status_changed`
- Se è la prima/UNICA QUEUED e nessuna issue è running per questo progetto → **auto-start immediato**: cambia in `REASONING` e chiama `run_issue`. Questo evita che la prima issue in coda aspetti un FINISHED che non arriverà mai.

#### `queue_list(project_id)`
- Elenca tutte le issue con status `QUEUED` per il progetto
- Restituisce lista ordinata per `created_at` ASC, con posizione (1-based)
- Ogni entry: `{position, issue_id, issue_name, created_at}`

#### `queue_remove(project_id, issue_id)`
- Validazione: issue deve essere in status `QUEUED`
- Imposta status a `NEW` (se veniva da New) o `CANCELED` (se veniva da Accepted)
- Emette evento `issue_status_changed`

#### `queue_position(project_id, issue_id)`
- Se issue non è QUEUED → restituisce `null`
- Altrimenti restituisce la posizione 1-based nella coda ordinata per `created_at`

### 2.4 Registrazione all'avvio

In `backend/app/main.py`, nel `lifespan`, aggiungere:
```python
from app.services.issue_queue_service import IssueQueueService
# ...
_ = IssueQueueService()  # register as event listener
```
Subito dopo la riga `_ = NotificationService()`.

## 3. Dettaglio implementazione

### 3.1 File da modificare

| File | Modifica |
|------|----------|
| `backend/app/models/issue.py` | Aggiungere `QUEUED = "Queued"` a IssueStatus |
| `backend/app/mcp/shared_tools.py` | Aggiungere 4 funzioni: queue_add, queue_list, queue_remove, queue_position |
| `backend/app/mcp/orchestrator_server.py` | Importare e registrare i 4 nuovi tool sul server orchestrator |
| `backend/app/services/issue_queue_service.py` | **NUOVO**: IssueQueueService event listener |
| `backend/app/main.py` | Registrare IssueQueueService nel lifespan |

### 3.2 Nuovo file

**`backend/app/services/issue_queue_service.py`**: ~70 linee
- Classe `IssueQueueService(BaseNotifier)`
- `__init__` → registra su event_service
- `notify(event)` → filtra `issue_status_changed` con `new_status == "Finished"` e `new_status == "Queued"` (per auto-start della prima coda)
- `_dequeue_and_run(project_id)` → logica core
- Usa `async_session()` dal DB per query, `IssueService` per update status, `run_issue_service.run_issue()` per avviare

### 3.3 Comportamenti edge

| Scenario | Comportamento |
|----------|--------------|
| Coda vuota quando FINISHED | Listener non fa nulla |
| Nuova QUEUED mentre una running è in corso | Resta in coda, partirà quando la running finisce |
| QUEUED cancellata manualmente | Non parte, la coda passa alla prossima |
| Più QUEUED aggiunte insieme | Ordine FIFO per created_at |
| Prima QUEUED aggiunta (coda vuota, nessuna running) | Auto-start immediato via `queue_add` |
| run_issue fallisce nel creare il terminale | Errore loggato, coda non avanzata (miglioramento futuro: skip su fallimento) |

## 4. Cosa NON serve (per questa issue)

- ❌ Nessuna priorità — solo FIFO per created_at
- ❌ Nessun retry automatico su fallimento
- ❌ Nessun polling — solo event-driven su FINISHED
- ❌ Nessun worker Hermes esterno — tutto dentro Manager AI
- ❌ Nessuna UI dedicata (si vede già filtrando per QUEUED)
- ❌ Nessuna notifica Telegram aggiuntiva per eventi di coda