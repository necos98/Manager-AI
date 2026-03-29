# Manager AI — Roadmap Robustezza

Ultimo aggiornamento: 2026-03-29

Questa roadmap non aggiunge feature: consolida, rafforza e rende affidabile ciò che già esiste.

---

## R1 — Affidabilità del Core

Correggere i punti dove il sistema può silenziare errori o lasciare stato inconsistente.

### R1.1 Race condition sul completamento issue
- [ ] Aggiungere lock/serializzazione in `issue_service.complete_issue()` tra il check dei task pending e il flush
  - File: `backend/app/services/issue_service.py:131-177`
  - Rischio attuale: issue marcata FINISHED con task ancora pending se due richieste concorrenti
- [ ] Test: verifica che due chiamate `complete_issue` concorrenti su stessa issue non causino stato inconsistente

### R1.2 Propagazione errori negli hook
- [ ] `hook_registry.fire()` attualmente crea `asyncio.create_task` senza tracking — aggiungere riferimento alla task e log strutturato del risultato
  - File: `backend/app/hooks/registry.py:57-66`
- [ ] Aggiungere timeout esplicito per ogni hook execution (default 300s, configurabile)
- [ ] Emettere evento WebSocket `hook_failed` con dettagli anche quando l'eccezione viene swallowed
- [ ] Test: hook che lancia eccezione non deve bloccare il flusso principale

### R1.3 Cleanup PTY garantito
- [ ] Nel WebSocket handler dei terminali, assicurarsi che la chiusura PTY avvenga in `finally`, non solo su EOF
  - File: `backend/app/routers/terminals.py:316-389`
- [ ] `terminal_service.resize()` accede all'entry fuori dal lock — spostare dentro il lock
  - File: `backend/app/services/terminal_service.py:205-211`
- [ ] Test: disconnect brusco del WebSocket deve liberare la PTY

### R1.4 RAG embed non silenziato
- [ ] `rag_service.py` ha `except Exception: pass` che swallowa fallimenti embedding
- [ ] Loggare sempre al livello `warning` quando embed fallisce, includere issue_id
- [ ] In MCP `complete_issue`, loggare il task id dell'embed in modo tracciabile
  - File: `backend/app/mcp/server.py:148-155`

---

## R2 — Consistenza dei Pattern

Completare l'allineamento architetturale avviato in Fase 0/1 nei file rimasti indietro.

### R2.1 Gestione errori uniforme nel frontend
- [ ] `issue-detail.tsx`: i blocchi `catch {}` vuoti devono loggare o mostrare toast
  - File: `frontend/src/features/issues/components/issue-detail.tsx:62-78`
- [ ] Tutti i `useMutation()` senza `onError` devono avere almeno un toast di fallback
  - Pattern: scansionare `hooks.ts` di ogni feature e aggiungere `onError: (e) => toast.error(...)`
- [ ] `api/client.ts`: aggiungere timeout di default (30s) alle fetch
  - File: `frontend/src/shared/api/client.ts:13-24`

### R2.2 Validazione input coerente backend/frontend
- [ ] Schema `IssueCreate.description`: aggiungere `max_length` (es. 50_000 chars)
- [ ] Schema `IssueCompleteBody.recap`: aggiungere `max_length`
- [ ] Schema `IssueUpdate.spec` / `.plan`: aggiungere `max_length`
- [ ] Stessa logica nei form del frontend: disabilitare submit se campo supera limite

### R2.3 Transazioni MCP consistenti
- [ ] Alcuni MCP tool fanno `session.commit()` esplicitamente, altri no — uniformare il pattern
  - File: `backend/app/mcp/server.py` (linee 87, 110, 146, 176)
- [ ] Preferire un singolo commit al termine del tool, non commit parziali mid-function

### R2.4 `.env.example` completo
- [ ] Documentare tutte le variabili usate dall'app: `EMBEDDING_MODEL`, `CLAUDE_LIBRARY_PATH`, `RECORDINGS_PATH`, `BACKEND_PORT`
- [ ] Aggiungere validazione in `config.py` (Pydantic validators) per i valori obbligatori

---

## R3 — Test Coverage

Coprire i percorsi critici non ancora testati.

### R3.1 Test servizi core
- [ ] `terminal_service.py`: test per close/resize concorrente, buffer overflow, cleanup su disconnect
- [ ] `issue_service.py`: test per race condition su `complete_issue` (async concurrent calls)
- [ ] `rag_service.py`: test per lock cleanup con N thread concorrenti

### R3.2 Test hook system
- [ ] Hook che lancia eccezione: verificare che il flusso principale non si interrompa
- [ ] Hook con timeout: verificare che venga cancellato e loggato
- [ ] `ISSUE_CREATED` hook: test end-to-end del trigger

### R3.3 Test router terminali
- [ ] Creazione terminale: risposta corretta
- [ ] WebSocket connect/disconnect: PTY cleanup verificato
- [ ] Resize con terminale inesistente: 404 pulito

### R3.4 Test MCP tools
- [ ] Transazione atomica: errore nel tool non lascia DB in stato parziale
- [ ] Tool call con project_id inesistente: `NotFoundError` propagato correttamente

---

## R4 — Pipeline di Sviluppo

Rendere lo startup, le migrazioni e il ciclo di sviluppo più robusti.

### R4.1 start.py più resiliente
- [ ] Se le migrazioni falliscono, stampare l'errore e uscire con exit code non-zero (ora silenzia)
  - File: `start.py:94-103`
- [ ] Timeout backend readiness: aumentare da 15s a 30s, con messaggi di progresso ogni 5s
  - File: `start.py:137-150`
- [ ] Health check backend: verificare `/api/health` invece di solo TCP connect

### R4.2 Endpoint `/api/health`
- [ ] Aggiungere route GET `/api/health` che verifica: DB connesso, RAG pipeline inizializzata
- [ ] Risposta: `{ "status": "ok", "db": true, "rag": true }` — usato da start.py e monitoring

### R4.3 Logging strutturato
- [ ] Aggiungere middleware FastAPI che logga: method, path, status_code, duration_ms per ogni request
- [ ] Standardizzare il formato log: usare `structlog` o formato JSON in produzione
- [ ] Nessun `except Exception: pass` senza almeno `logger.warning`

### R4.4 Migrazioni verificabili
- [ ] Aggiungere script `check_migrations.py` che verifica: `alembic current` == `alembic head`
- [ ] Integrare in start.py come check pre-avvio (fallisce veloce se DB non allineato)
- [ ] Test: migration upgrade + downgrade per le ultime 3 revisioni

---

## Priorità Raccomandata

| Priorità | Item | Impatto | Effort |
|----------|------|---------|--------|
| 1 | R1.2 — Hook error propagation | Alto | Basso |
| 2 | R1.3 — PTY cleanup garantito | Alto | Basso |
| 3 | R2.1 — Error handling frontend | Alto | Medio |
| 4 | R1.1 — Race condition issue completion | Alto | Medio |
| 5 | R4.2 — Health endpoint | Medio | Basso |
| 6 | R4.1 — start.py resiliente | Medio | Basso |
| 7 | R2.2 — Validazione input max_length | Medio | Basso |
| 8 | R3.1 — Test servizi core | Alto | Alto |
| 9 | R2.3 — Transazioni MCP | Medio | Basso |
| 10 | R4.3 — Logging strutturato | Medio | Medio |
| 11 | R1.4 — RAG embed logging | Basso | Basso |
| 12 | R3.2-R3.4 — Test hook/router/MCP | Alto | Alto |
| 13 | R4.4 — Migration check | Basso | Basso |
| 14 | R2.4 — .env.example completo | Basso | Minimo |
