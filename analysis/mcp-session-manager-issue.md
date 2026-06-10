# MCP Session Manager — Problema e Soluzione

**Data:** 10 Giugno 2026
**Backend:** FastAPI + FastMCP (Streamable HTTP)

---

## Il Problema

L'MCP orchestrator (`/mcp-orchestrator/`) espone 44 tools per Hermes Agent, ma le sessioni MCP funzionano solo per **un singolo tool call** per sessione.

### Sintomi

| Step | Descrizione | Risultato |
|------|-------------|-----------|
| `POST` con `initialize` | Crea sessione, ritorna `mcp-session-id` nell'header | ✅ OK |
| `POST` con `mcp-session-id` + tool call (1° call) | Tool eseguito con successo | ✅ OK |
| `POST` con stesso `mcp-session-id` (2° call) | Server risponde **"Missing session ID"** | ❌ FAIL |
| Tentativi ripetuti di nuove sessioni | Server non risponde piu (HTTP 000) | ❌ BLOCCATO |

### Root Cause

FastMCP usa il protocollo **Streamable HTTP**, dove:

1.  **Primo POST** (`initialize`): il server crea una sessione e **avvia uno stream SSE** (Server-Sent Events) che rimane aperto. La sessione è legata a quello stream.

2.  **Secondo POST** (tool call): la risposta al tool **non arriva nell'HTTP response** — arriva sullo stream SSE della prima connessione. Se lo stream SSE è stato chiuso (o non è mai stato consumato), il server perde la sessione.

3.  **Connessioni zombie**: Ogni POST di inizializzazione che non viene properamente chiusa lascia una connessione SSE aperta. Dopo N connessione, il server satura e non accetta piu nuove richieste.

```
┌─────────┐                              ┌──────────┐
│ Client  │  1. POST con initialize      │  Server  │
│         │ ──────────────────────────→  │          │
│         │    Header: mcp-session-id    │          │
│         │    + inizio stream SSE (aperto!)        │
│         │ ←──────────────────────────  │          │
│         │                              │          │
│         │  2. POST con tool/call       │          │
│         │ ──────────────────────────→  │          │
│         │    Risposta → va sullo SSE!  │          │
│         │    (ma la connessione SSE e`    │          │
│         │     gia` chiusa → session    │          │
│         │     persa → Missing ID)      │          │
└─────────┘                              └──────────┘
```

### Codice Interessato

**`backend/app/main.py`** — Il mount MCP (linee 91-94, 377-394):

```python
# Creazione delle app ASGI streamable (modulo, prima del lifespan)
_orchestrator_app = orchestrator_mcp.streamable_http_app()

# Lifespan: task group CONDIVISO tra worker e orchestrator
async with anyio.create_task_group() as _mcp_tg:
    _sm._task_group = _mcp_tg       # worker MCP
    _osm._task_group = _mcp_tg      # orchestrator MCP (STESSO!)
```

**`backend/app/mcp/orchestrator_server.py`** — Trasporto Streamable HTTP (linea 83):

```python
orchestrator_mcp = FastMCP("Manager AI Orchestrator", streamable_http_path="/")
```

**Problemi identificate:**
1.  Le sessioni Streamable HTTP richiedono SSE persistente — senza, la sessione muore dopo un tool call
2.  Il task group e` condiviso tra worker e orchestrator — sessioni zombie bloccano entrambi
3.  Il client non consuma lo stream SSE, quindi la sessione non viene mantenuta
4.  Manca un cleanup delle sessioni stale lato server

---

## Soluzione

### Opzione A — Fix Backend (Consigliata)

Modificare il session manager dell'orchestrator per supportare **sessioni indipendenti dallo stream SSE** — dove la risposta del tool call viene inviata direttamente nell'HTTP response invece che sullo stream SSE.

**Cambiamenti necessari:**

#### 1. Disaccoppiare i task group

In `backend/app/main.py`, separare i task group del worker e dell'orchestrator:

```python
# Invece di task group condiviso:
async with anyio.create_task_group() as _worker_tg:
    _sm._task_group = _worker_tg
async with anyio.create_task_group() as _orch_tg:
    _osm._task_group = _orch_tg
```

#### 2. Session manager che risponde inline

Modificare il session manager di FastMCP per rispondere ai tool call direttamente nell'HTTP response POST invece di aspettare lo stream SSE. Questo richiede di sottoclassare `SessionManager` e override di `handle_message`:

```python
class InlineSessionManager(SessionManager):
    """Session manager che risponde inline invece che via SSE."""
    
    async def handle_message(self, message, send):
        # Processa il messaggio e invia la risposta direttamente
        # senza passare dallo stream SSE
        result = await self._process_message(message)
        await send({
            "type": "http.response.body",
            "body": json.dumps({"jsonrpc": "2.0", "result": result}).encode(),
        })
```

#### 3. Aggiungere cleanup sessioni stale

Nel lifespan, dopo lo yield, aggiungere:

```python
finally:
    # Cleanup forzato di tutte le sessioni stale
    for session_id in list(_osm._sessions.keys()):
        try:
            await _osm._sessions[session_id].close()
        except Exception:
            pass
    _osm._sessions.clear()
    _sm._task_group = None
    _osm._task_group = None
```

### Opzione B — Fix Client (per Hermes)

Mantenere la connessione SSE aperta lato client. Pattern corretto con `httpx`:

```python
import httpx
import json

client = httpx.Client()

# 1. POST initialize — mantieni connessione aperta per SSE
resp = client.post(
    "http://localhost:8001/mcp-orchestrator/",
    json={"jsonrpc":"2.0","id":"init","method":"initialize",
          "params":{"protocolVersion":"2024-11-05","capabilities":{},
                    "clientInfo":{"name":"hermes-agent","version":"1.0.0"}}},
    headers={"Accept": "application/json, text/event-stream"},
)
session_id = resp.headers["mcp-session-id"]

# 2. Leggi lo stream SSE in background (thread separato)
#    La risposta ai tool call arriva qui come event: message data: {...}

# 3. POST tool call — stessa sessione, risposta via SSE
resp2 = client.post(
    "http://localhost:8001/mcp-orchestrator/",
    json={"jsonrpc":"2.0","id":"call1","method":"tools/call",
          "params":{"name":"queue_list","arguments":{}}},
    headers={"mcp-session-id": session_id},
)
# La risposta arriva sullo stream SSE della connessione #1
```

### Opzione C — Workaround Rapido

Creatare una nuova sessione per ogni tool call, ma con cleanup forzato:

```python
import http.client
import time

def mcp_call(tool, args):
    """Crea sessione, fa un tool call, chiude tutto."""
    conn = http.client.HTTPConnection("localhost", 8001, timeout=10)
    
    # Init
    body = json.dumps({...initialize...})
    conn.request("POST", "/mcp-orchestrator/", body=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    resp = conn.getresponse()
    session_id = resp.getheader("mcp-session-id")
    resp.read()  # consuma stream SSE
    conn.close()
    
    time.sleep(0.5)  # lascia tempo al server di rilasciare
    
    # Tool call con nuova connessione
    conn2 = http.client.HTTPConnection("localhost", 8001, timeout=10)
    body2 = json.dumps({...tools/call...})
    conn2.request("POST", "/mcp-orchestrator/", body=body2, headers={
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    })
    resp2 = conn2.getresponse()
    result = resp2.read().decode()
    conn2.close()
    return result
```

**Nota:** Il workaround funziona per 1-2 chiamate, ma dopo N cicli il server si blocca comunque perche' le sessioni SSE non vengono pulite dal server stesso. E` necessaria l'**Opzione A** per una soluzione stabile.

---

## File Interessati

| File | Linee | Ruolo |
|------|-------|-------|
| `backend/app/main.py` | 91-94 | Creazione `streamable_http_app()` per orchestrator |
| `backend/app/main.py` | 119-130 | Lazy-init del session manager orchestrator |
| `backend/app/main.py` | 372-394 | Lifespan: task group condiviso + cleanup |
| `backend/app/main.py` | 469-470 | Mount delle due app MCP (`/mcp` e `/mcp-orchestrator`) |
| `backend/app/mcp/orchestrator_server.py` | 83 | Creazione `FastMCP` con `streamable_http_path="/"` |
| `backend/app/mcp/server.py` | — | Worker MCP (stesso pattern, montato su `/mcp`) |
| `backend/app/mcp/shared_tools.py` | — | Implementazioni tool condivise tra worker e orchestrator |
