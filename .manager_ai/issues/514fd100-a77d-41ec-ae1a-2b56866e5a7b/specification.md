# Specifica: Analisi passaggio MCP da HTTP a stdio

## Obiettivo

Analizzare le implicazioni del passaggio del server MCP principale di Manager AI da trasporto HTTP (StreamableHTTP) a trasporto stdio (subprocess stdin/stdout), con focus su compatibilita WSL e performance.

## Stato attuale

- **Transport**: FastMCP con `streamable_http_path="/"`, montato in FastAPI a `/mcp`
- **Configurazione**: `~/.claude.json` → `mcpServers.ManagerAi` → `type: "http"`, `url: "http://localhost:8001/mcp/"`
- **Processo**: Singolo server FastAPI, sempre attivo. MCP condivide il processo con web UI, event system, hook system
- **Plugin**: PluginManager avviato nel processo FastAPI, plugin esterni spawnati come subprocess (stdio o HTTP/SSE)
- **Storage**: MemoryStore RAM-first in-process, scritture asincrone su disco via BackgroundWorker + SQLite WAL
- **WSL**: Il server HTTP e sempre su Windows → accessibile da qualsiasi progetto (Windows o WSL) via `localhost`

## Architettura stdio (proposta)

```
Claude Code ──spawn──▶ python -m app.mcp.stdio_server
                          │
                          ├── SQLite (stesso DB, accesso diretto)
                          ├── PluginManager (per istanza MCP)
                          └── MemoryStore (per istanza MCP)
```

Configurazione: `~/.claude.json` → `type: "stdio"`, `command: "python"`, `args: ["-m", "app.mcp.stdio_server"]`

## Analisi problematiche

### 1. WSL — CRITICO

**Scenario**: Claude Code lanciato in progetto WSL (`//wsl.localhost/Ubuntu-18.04/home/jacopo/project`)

**Problemi**:
- Subprocess Python eredita CWD = path UNC WSL (`//wsl.localhost/...`)
- `Path.cwd()` restituisce path UNC → `manager.json` non trovato (non esiste nel progetto WSL)
- Il DB SQLite e in `data/` relativo alla directory di Manager AI (Windows), non al progetto WSL
- `project.path` nel DB puo essere WSL o Windows path. Per accedere a `.manager_ai/` su progetti WSL, Python Windows deve usare path UNC (`\\wsl.localhost\...`)
- `aiofiles`/`os.open` su UNC path: funziona ma e piu lento dei path locali
- `pathlib.Path` normalizza i path diversamente su Windows (backslash vs forward slash)

**Con HTTP**: Nessun problema. Il server e su Windows, risolve il progetto da DB, accede ai file con il path corretto. Claude Code chiama via `localhost` indipendentemente dal CWD.

**Conclusione WSL**: Lo scenario stdio + WSL e il problema piu grosso. Richiederebbe:
1. Rilevamento automatico se il CWD e WSL
2. Traduzione path WSL ↔ Windows UNC
3. Gestione separata di `manager.json` (che sta nel progetto Manager AI, non nel progetto WSL)
4. Test approfonditi su tutte le operazioni file I/O

### 2. Multi-istanza e contesa risorse

**Problema**: Piu sessioni Claude Code = piu processi MCP stdio = piu connessioni SQLite

- SQLite WAL mode supporta reader concorrenti ma un solo writer alla volta
- Scritture concorrenti da piu MCP generano `SQLITE_BUSY`
- MemoryStore in-process non condivide stato tra istanze → cambiamenti da un'istanza non visibili alle altre senza ricaricare da disco
- WriteQueue basata su SQLite (`pending_writes.db`): code separate per ogni istanza MCP → possibile duplicazione scritture

**Con HTTP**: Una singola istanza, nessuna contesa. MemoryStore e condiviso tra tutte le richieste.

### 3. Event System e WebSocket

**Problema**: MCP stdio non ha WebSocket → impossibile emettere eventi real-time

Tool come `create_issue_spec`, `update_task_status`, `accept_issue`, `send_notification`, `ask_user_question` emettono eventi WebSocket (`event_service.emit()`). Senza server HTTP:
- Eventi persi (nessun subscriber)
- Frontend non riceve aggiornamenti in tempo reale
- `ask_user_question` si blocca (usa `question_store.wait()` + `event_service.emit()` per notificare la risposta)

**Possibili soluzioni**:
- Mantenere un server HTTP leggero solo per eventi WebSocket
- Sostituire eventi WebSocket con polling dal frontend
- Usare un message broker esterno (Redis, file-system based)

**Con HTTP**: Funziona nativamente.

### 4. Hook System

**Problema**: `complete_issue` e `update_task_status` (quando tutti i task sono completati) fire hooks via `hook_registry.fire()`. Gli hook eseguono comandi shell (es. `claude -p`). Senza il server FastAPI:
- Hook eseguiti nel processo MCP stdio (funziona)
- Ma senza EventService, le notifiche hook (TTS, notifiche desktop) non funzionano
- La memoria `9b08de23` dice che gli agent eseguono come Windows subprocess → hook MCP stdio seguirebbero lo stesso pattern

**Con HTTP**: Hook eseguiti nel contesto del server, con accesso a tutti i servizi.

### 5. Plugin System

**Problema**: PluginManager attualmente vive nel processo FastAPI. Con stdio:
- Ogni istanza MCP avrebbe il proprio PluginManager
- `enable_plugin`/`disable_plugin` da un'istanza non visibile alle altre
- I plugin spawnati come subprocess (es. mysql via uvx) vengono avviati da ogni istanza MCP
- Rischio: N plugin MySQL simultanei se N sessioni Claude Code attive

**Con HTTP**: PluginManager centralizzato, stato unico.

### 6. Performance

| Aspetto | HTTP (attuale) | stdio |
|---------|---------------|-------|
| Latenza prima chiamata | ~5-10ms (TCP handshake) | ~1-2s (cold start Python + import) |
| Latenza chiamate successive | ~1-5ms (keep-alive) | ~0.1-0.5ms (pipe I/O) |
| Overhead serializzazione | JSON via HTTP body | JSON via stdin/stdout |
| Memoria | Condivisa col server FastAPI | ~50-100MB per istanza MCP |
| Concorrenza | Gestita da uvicorn (multi-worker possibile) | Single-thread, una richiesta alla volta |

**Con HTTP**: Latenza leggermente maggiore ma accettabile per tool MCP. Nessun cold start.
**Con stdio**: Latenza migliore dopo l'avvio, ma cold start significativo ad ogni nuova sessione.

### 7. Frontend / Web UI

**Problema**: Manager AI ha un frontend React che richiede il server FastAPI. Con stdio:
- Il server FastAPI deve comunque esistere per servire il frontend
- Due entry point da mantenere: `start.py` (server) + `stdio_server.py` (MCP)
- L'utente deve avviare entrambi (o lo script start avvia entrambi)

### 8. Lifecycle

**HTTP (attuale)**: Server sempre attivo → MCP sempre disponibile. Matcha il workflow "sempre in background".

**stdio**: MCP spawnato on-demand da Claude Code. Muore quando Claude Code esce.
- Pro: Nessun processo orfano, risparmio risorse quando non in uso
- Contro: Cold start ad ogni nuova sessione Claude Code (~1-2s)

## Raccomandazione

**Restare su HTTP** per lo scenario attuale. Motivi:

1. **WSL**: HTTP funziona gia perfettamente con progetti WSL. stdio richiederebbe gestione path UNC non banale
2. **Workflow attuale**: L'utente tiene Manager AI sempre in background → nessun beneficio dal "non avere un server"
3. **Sottosistemi**: Event system, hook, notifiche, plugin manager dipendono dall'architettura a server unico
4. **Performance**: La differenza di latenza (1-5ms HTTP vs 0.1-0.5ms stdio) e trascurabile per tool MCP che tipicamente durano 10-100ms
5. **Costo migrazione**: Alto, con rischi di regressione su WSL, plugin, eventi

## Se in futuro servisse stdio

Implementare **Approccio 2 (Dual Transport)**:

1. **Refactoring preliminare**: Estrarre le tool functions da `server.py` in `app/mcp/tools.py` come funzioni pure che accettano `AsyncSession`
2. **Entry point stdio**: `backend/app/mcp/stdio_main.py` — script autonomo che:
   - Crea FastMCP con trasporto stdio
   - Registra le stesse tool functions
   - Gestisce la propria sessione database
   - NON avvia EventService/WebSocket (eventi sarebbero fire-and-forget o queued)
3. **Configurazione duale**: Lo user sceglie il transport per progetto in `.mcp.json`
4. **Gestione WSL**: Il processo stdio rileva se il CWD e un path WSL e risolve il `manager.json` dalla directory di Manager AI (non dal CWD)
5. **Test**: Suite di test per entrambi i transport, con focus su race condition multi-istanza

### Stima effort

| Task | Effort |
|------|--------|
| Refactoring tool functions condivise | 2-3 giorni |
| Entry point stdio | 1-2 giorni |
| Gestione path WSL in stdio | 2-3 giorni |
| Coordinazione stato multi-istanza | 3-5 giorni |
| Test e validazione | 2-3 giorni |
| **Totale stimato** | **10-16 giorni** |
