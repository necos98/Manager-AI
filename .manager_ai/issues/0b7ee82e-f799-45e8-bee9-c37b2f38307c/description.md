## Issue Queue System (Coda Issue Sincrona)

### Obiettivo
Aggiungere a Manager AI un sistema di **coda issue sincrona** — una coda FIFO dove le issue possono essere accodate e vengono eseguite **una per volta**, in sequenza. Appena una issue termina (status FINISHED), la successiva in coda parte automaticamente via `run_issue()`. Niente polling, tutto event-driven.

### Meccanismo

```
┌─────────────────────────────────────────────────────┐
│                   MANAGER AI                          │
│                                                        │
│  1. Nuovo status: QUEUED (aggiunto alla state machine) │
│                                                        │
│  2. Evento: issue_status_changed → FINISHED            │
│     ↓                                                  │
│     Check: esiste una QUEUED ordinata per created_at?  │
│     ↓                                                  │
│     Sì → run_issue(prossima QUEUED)                    │
│     No → non fare nulla                                │
│                                                        │
│  3. MCP tools (sul orchestrator):                      │
│     - queue_add(issue_id)       → setta status QUEUED  │
│     - queue_list()              → [QUEUED issues]      │
│     - queue_remove(issue_id)    → rimuove dalla coda   │
│     - queue_position(issue_id)  → posizione in coda    │
│                                                        │
│  4. Sincrono: una issue per volta, FIFO                │
│                                                        │
│  5. Se QUEUED viene cancellata → non parte             │
│                                                        │
│  6. Se una QUEUED fallisce → skip e passa alla prossima│
└─────────────────────────────────────────────────────────┘
```

### Cosa serve implementare

1. **Status `QUEUED`** — aggiungere alla state machine delle issue:
   - Transizioni: `New → QUEUED`, `Accepted → QUEUED`, `QUEUED → Reasoning` (auto quando parte)
   - `QUEUED` non è cancellabile? No, deve esserlo (forse via `CANCELED`)

2. **Event listener** — quando una issue va in `FINISHED`, controllare se esiste almeno una `QUEUED`:
   - Se sì: prendere la più vecchia per `created_at`, cambiarla in `REASONING` e chiamare `run_issue()`
   - Se no: non fare nulla

3. **MCP tools** — 4 tools semplici sull'orchestrator:
   - `queue_add(issue_id)` → imposta status `QUEUED`
   - `queue_list()` → elenca tutte le QUEUED con posizione
   - `queue_remove(issue_id)` → rimuove dalla coda (setta status `New` o `Canceled`)
   - `queue_position(issue_id)` → restituisce la posizione in coda

### Cosa NON serve (per adesso)

- ❌ Nessuna priorità — solo FIFO per created_at
- ❌ Nessun retry automatico su fallimento (si può aggiungere dopo)
- ❌ Nessun polling — solo event-driven su FINISHED
- ❌ Nessun worker Hermes esterno — tutto dentro Manager AI
- ❌ Nessuna UI dedicata (si vede già dalla lista issue filtrando per QUEUED)

### Comportamenti edge

- **Coda vuota quando FINISHED**: il listener non fa nulla, resta in attesa silenziosa
- **Nuova QUEUED aggiunta mentre una RUNNING è in corso**: resta in coda, partirà quando la RUNNING finisce
- **QUEUED cancellata manualmente**: non parte, coda passa alla prossima
- **QUEUED fallisce (status FAILED)**: il listener deve gestire anche `FAILED` come trigger per passare alla prossima? Oppure solo FINISHED? Da decidere.
- **Più QUEUED aggiunte insieme**: ordine FIFO per created_at

### Note tecniche
- Il listener si aggancia all'EventService (già esistente) sull'evento `issue_status_changed`
- `run_issue()` esiste già — va chiamata con `project_id` e `issue_id`
- I MCP tools vanno aggiunti all'orchestrator_server.py
- Stato iniziale: issue New → QUEUED (non parte subito, aspetta che le precedenti finiscano)