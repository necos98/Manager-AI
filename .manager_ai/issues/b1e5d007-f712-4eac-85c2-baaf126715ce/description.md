## UI Globale della Coda Issue

Creare una sezione nell'interfaccia web di Manager AI che mostri a livello **globale** (non per-progetto) lo stato della coda delle issue.

### Cosa mostrare

**1. Sezione "In esecuzione"**
- Issue attualmente in esecuzione (status Reasoning/Planned/Accepted con terminale attivo)
- Progetto di appartenenza
- Link diretto alla issue

**2. Sezione "In coda"**
- Tutte le issue in stato QUEUED, ordinate per posizione FIFO
- Per ogni issue: posizione, nome, progetto di appartenenza, created_at
- Indicazione visiva di chi è il prossimo a partire

**3. Indicatori di stato**
- Se la coda è attiva o in pausa
- Quante issue sono in coda

### Requisiti tecnici
- Nuova pagina/route globale (es. `/queue` o `/global-queue`)
- Accessibile dal menu di navigazione principale (non dentro un progetto)
- Usa le API REST esistenti (se non esistono endpoint REST per la coda, crearli)
- Aggiornamento in tempo reale via WebSocket (EventService già emette eventi issue_status_changed)

### Cosa NON serve
- ❌ Nessuna azione di modifica dalla UI (drag&drop, rimozione) — solo visualizzazione
- ❌ Nessuna gestione prioritá — solo FIFO visivo

### API necessarie (se non esistono già)
- `GET /api/queue` — lista globale di tutte le QUEUED (tutti i progetti)
- `GET /api/queue/running` — lista globale di tutte le issue in esecuzione
- Alternativa: query via eventi WebSocket già esistenti