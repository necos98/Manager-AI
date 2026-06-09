# Piano d'Implementazione — Opzione A: Zero Tool Overlap tra MCP

> **Data:** 2026-06-09
> **Riferimento:** `analysis/dual-mcp-tool-overlap-analysis.md`
> **File coinvolti:** `backend/app/mcp/server.py`, `orchestrator_server.py`, `shared_tools.py`, `default_settings.json`, plus skill `.md` files

---

## Indice delle Fasi

| # | Fase | File | Impatto |
|---|------|------|---------|
| 1 | Rimuovere tool amministrativi dal Worker | `server.py` | -20 tool |
| 2 | Prefissare tool di frontiera nel Worker | `server.py` | ~8 rename |
| 3 | Correggere duplicato `list_plugins` nel Worker | `server.py` | Unire 2 definizioni |
| 4 | Rimuovere `finished_pipeline_step` dall'Orchestrator | `orchestrator_server.py` | -1 tool |
| 5 | Aggiungere `memory_search` all'Orchestrator | `shared_tools.py`, `orchestrator_server.py`, `default_settings.json` | +1 tool |
| 6 | Spostare `enable_plugin`/`disable_plugin` nell'Orchestrator | `server.py`, `orchestrator_server.py`, `shared_tools.py` | 2 tool moved |
| 7 | Aggiornare skill Hermes e documentazione | 7 file `.md` | Nomi tool aggiornati |
| 8 | Verifica e test | — | Smoke test MCP |

---

## Fase 1 — Rimuovere 20 Tool Amministrativi dal Worker

**File:** `backend/app/mcp/server.py`

Rimuovere TUTTE le definizioni di tool e le relative funzioni helper.

### 1.1 Rimuovere Agent CRUD (5 tool)

Blocchi da rimuovere:

| Tool | Righe da rimuovere | Descrizione |
|------|-------------------|-------------|
| `create_agent` | Righe 332-343 | Funzione + decoratore @mcp.tool |
| `list_agents` | Righe 346-353 | Funzione + decoratore |
| `get_agent` | Righe 356-361 | Funzione + decoratore |
| `update_agent` | Righe 364-388 | Funzione + decoratore |
| `delete_agent` | Righe 382-388 | Funzione + decoratore |

**Dettaglio sostituzioni:**

```
# create_agent (righe 331-343)
@mcp.tool(description=_desc["tool.create_agent.description"])
@mcp_tool_wrapper
async def create_agent(session, name: str, intent: str = "", ...)

# list_agents (righe 346-353)
@mcp.tool(description=_desc["tool.list_agents.description"])
async def list_agents() -> dict:

# get_agent (righe 356-361)  
@mcp.tool(description=_desc["tool.get_agent.description"])
@mcp_tool_wrapper
async def get_agent(session, agent_id: str) -> dict:

# update_agent (righe 364-388)
@mcp.tool(description=_desc["tool.update_agent.description"])
@mcp_tool_wrapper
async def update_agent(session, agent_id: str, ...)

# delete_agent (righe 382-388)
@mcp.tool(description=_desc["tool.delete_agent.description"])
@mcp_tool_wrapper
async def delete_agent(session, agent_id: str) -> dict:
```

### 1.2 Rimuovere Pipeline CRUD (8 tool)

| Tool | Righe | Note |
|------|-------|------|
| `create_pipeline` | ~394-407 | Locale con PipelineService |
| `list_pipelines` | ~410-417 | Locale |
| `get_pipeline` | ~420-425 | Locale |
| `update_pipeline` | ~428-435 | Locale |
| `delete_pipeline` | ~438-444 | Locale |
| `add_step` | ~447-454 | Locale |
| `remove_step` | ~457-466 | Locale |
| `reorder_steps` | ~469-476 | Locale |

### 1.3 Rimuovere Pipeline Event Rules (3 tool)

| Tool | Righe | Note |
|------|-------|------|
| `add_pipeline_event_rule` | ~482-508 | Locale |
| `remove_pipeline_event_rule` | ~511-520 | Locale |
| `list_pipeline_event_rules` | ~523-540 | Locale |

### 1.4 Rimuovere Pipeline Run — Avvio e Stato (2 tool)

| Tool | Righe | Note |
|------|-------|------|
| `run_pipeline` | ~546-564 | Locale |
| `get_pipeline_run_status` | ~567-574 | Locale |

### 1.5 Rimuovere/Spostare Plugin enable/disable (2 tool)

Questi vengono SPOSTATI nell'orchestrator (Fase 6). Per ora rimuoverli dal worker.

| Tool | Righe | Note |
|------|-------|------|
| `enable_plugin` | ~300-313 | Locale |
| `disable_plugin` | ~316-326 | Locale |

### 1.6 Pulire import inutilizzati

Dopo la rimozione, questi import potrebbero non servire più:

```python
from app.services.agent_service import AgentService       # ← se non più usato
from app.services.pipeline_service import PipelineService    # ← se non più usato
from app.mcp.helpers import mcp_tool_wrapper                 # ← se non più usato
```

Verificare se `mcp_tool_wrapper`, `AgentService`, `PipelineService` sono usati
da altri tool rimasti. Se le uniche occorrenze erano nei tool rimossi, rimuovere
anche gli import.

---

## Fase 2 — Prefissare 8 Tool di Frontiera nel Worker

**File:** `backend/app/mcp/server.py`

Rinominare le funzioni e i nomi dei tool MCP per evitare overlap con l'orchestrator.

### 2.1 Mappa delle rinomine

| Nome attuale | Nuovo nome (worker) | Descrizione da aggiornare? |
|--------------|---------------------|---------------------------|
| `get_issue_details` | `worker_get_issue_details` | Sì, aggiornare descrizione |
| `get_issue_status` | `worker_get_issue_status` | Sì |
| `set_issue_name` | `worker_set_issue_name` | Sì |
| `get_project_context` | `worker_get_project_context` | Sì |
| `get_active_agent` | `worker_get_active_agent` | Sì |
| `get_active_pipeline_run` | `worker_get_active_pipeline_run` | Sì |
| `send_agent_message` | `worker_send_agent_message` | Sì |
| `get_pipeline_messages` | `worker_get_pipeline_messages` | Sì |

### 2.2 Cosa cambiare per ogni tool

1. Il **nome della funzione Python**: `async def get_issue_details(...)` → `async def worker_get_issue_details(...)`
2. Il **nome nel decoratore**: `@mcp.tool(...)` — FastMCP usa il nome della funzione Python come nome del tool. Quindi rinominando la funzione, si rinominerà automaticamente il tool.
3. La **descrizione** (opzionale): aggiungere "(Worker)" alla fine per chiarezza.

**Esempio di modifica:**

```python
# PRIMA
@mcp.tool(description=_desc["tool.get_issue_details.description"])
async def get_issue_details(project_id: str, issue_id: str) -> dict:

# DOPO
@mcp.tool(description=_desc["tool.worker_get_issue_details.description"] or 
          "Worker: get all details of a specific issue...")
async def worker_get_issue_details(project_id: str, issue_id: str) -> dict:
```

**NOTA:** Aggiungere nuove chiavi in `default_settings.json` per le descrizioni
prefissate (es. `tool.worker_get_issue_details.description`), oppure inlineare
la descrizione nel decoratore.

---

## Fase 3 — Correggere Duplicato `list_plugins`

**File:** `backend/app/mcp/server.py`

Attualmente `list_plugins` è definito DUE VOLTE:

1. **Definizione locale** (righe ~238-270): implementazione inline che usa `ProjectService` + `plugin_manager`
2. **Definizione shared_tools** (righe ~682-685): wrapper che chiama `_list_plugins` da shared_tools

### Azione

1. **Rimuovere** la definizione locale (righe 238-270, `list_plugins` con `ProjectService`)
2. **Tenere** la definizione da shared_tools (righe 682-685)
3. Assicurarsi che `list_plugins` sia ancora importato in cima al file:
   ```python
   from app.mcp.shared_tools import (
       ...
       list_plugins as _list_plugins,
       ...
   )
   ```
4. Verificare che anche `get_plugin_config_tool` sia importato (dovrebbe già esserlo)

### Nota

L'import `list_plugins as _list_plugins` è già presente (riga 66 nella sezione Plugin).
La definizione locale a riga 238 **sovrascrive** l'import nel namespace del modulo.
Rimuovendo la definizione locale, le righe 682-685 diventeranno l'unica definizione.

---

## Fase 4 — Rimuovere `finished_pipeline_step` dall'Orchestrator

**File:** `backend/app/mcp/orchestrator_server.py`

### Identificazione

```python
# Righe ~312-326 in orchestrator_server.py
@orchestrator_mcp.tool(description=_desc["tool.finished_pipeline_step.description"])
async def finished_pipeline_step(
    issue_id: str,
    summary: str,
    rejected: bool = False,
    rejection_reason: str | None = None,
    target_step_index: int | None = None,
) -> dict:
    async with async_session() as session:
        return await _finished_pipeline_step(
            session, issue_id, summary,
            rejected=rejected,
            rejection_reason=rejection_reason,
            target_step_index=target_step_index,
        )
```

### Azione

1. Rimuovere l'intero blocco (decoratore + funzione)
2. **Rimuovere** l'import corrispondente in cima al file:
   ```python
   from app.mcp.shared_tools import (
       ...
       finished_pipeline_step as _finished_pipeline_step,  # ← da rimuovere
       ...
   )
   ```

**Motivazione:** `finished_pipeline_step` è chiamato dal worker per segnalare
completamento step. L'orchestrator non deve mai chiamarlo — la pipeline avanza
in automatico.

---

## Fase 5 — Aggiungere `memory_search` all'Orchestrator

### 5.1 Implementazione in shared_tools

**File:** `backend/app/mcp/shared_tools.py`

`MemoryService.search()` esiste già (riga 218 di `memory_service.py`).
Aggiungere la funzione wrapper in `shared_tools.py`:

```python
async def memory_search(
    session: AsyncSession,
    project_id: str,
    query: str,
    limit: int = 20,
) -> dict:
    """Search across a project's memory titles and descriptions."""
    svc = MemoryService(session)
    try:
        results = await svc.search(project_id=project_id, query=query, limit=limit)
        return {
            "results": [
                {
                    "id": r["memory"].id,
                    "title": r["memory"].title,
                    "snippet": r["snippet"],
                    "rank": r["rank"],
                    "created_at": r["memory"].created_at,
                }
                for r in results
            ],
            "count": len(results),
        }
    except AppError as e:
        return {"error": e.message}
```

Posizionare dopo `memory_unlink` (dopo riga ~700 circa).

### 5.2 Registrare in orchestrator_server.py

**File:** `backend/app/mcp/orchestrator_server.py`

Aggiungere l'import:
```python
from app.mcp.shared_tools import (
    ...
    memory_search as _memory_search,
    ...
)
```

Aggiungere il tool:
```python
@orchestrator_mcp.tool(
    description="Full-text search across a project's memory titles "
                "and descriptions. Returns matches with snippet and rank."
)
async def memory_search(project_id: str, query: str, limit: int = 20) -> dict:
    async with async_session() as session:
        return await _memory_search(session, project_id, query, limit)
```

### 5.3 Aggiungere descrizione in default_settings.json

**File:** `backend/app/mcp/default_settings.json`

La chiave `tool.memory_search.description` esiste già (riga 42).
Se si preferisce mantenere l'approccio `_desc[...]`, aggiungere:

```json
"tool.memory_search.description": "Full-text search across a project's memory titles and descriptions (SQLite FTS5). Returns matches with snippet and rank."
```

---

## Fase 6 — Spostare `enable_plugin`/`disable_plugin` nell'Orchestrator

### 6.1 Verificare esistenza in shared_tools

Già esistono in shared_tools:
- `enable_plugin_tool(session, project_id, plugin_name)` (riga 816)
- `disable_plugin_tool(session, project_id, plugin_name)` (riga 830)

### 6.2 Registrare in orchestrator_server.py

**File:** `backend/app/mcp/orchestrator_server.py`

Aggiungere import:
```python
from app.mcp.shared_tools import (
    ...
    enable_plugin_tool as _enable_plugin_tool,
    disable_plugin_tool as _disable_plugin_tool,
    ...
)
```

Aggiungere tool:
```python
@orchestrator_mcp.tool(description=_desc["tool.enable_plugin.description"])
async def enable_plugin(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        return await _enable_plugin_tool(session, project_id, plugin_name)


@orchestrator_mcp.tool(description=_desc["tool.disable_plugin.description"])
async def disable_plugin(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        return await _disable_plugin_tool(session, project_id, plugin_name)
```

### 6.3 RIMUOVERE dal worker (già fatto in Fase 1.5)

Rimosse in Fase 1.5 — verificare che siano effettivamente cancellate da `server.py`.

---

## Fase 7 — Aggiornare Skill Hermes e Documentazione

### 7.1 `hermes_skills/manager-ai-orchestrator/SKILL.md`

Questo file è per Hermes (usa l'orchestrator MCP). I nomi tool dell'orchestrator
**NON cambiano** (rimangono `get_issue_details`, `set_issue_name`, ecc.).

**Nessuna modifica necessaria** per i tool — i nomi sono invariati nell'orchestrator.

### 7.2 `hermes_skills/manager-ai-issue-worker/SKILL.md`

Questo file è per il worker (Claude Code). I tool del worker vengono RINOMINATI
con prefisso `worker_`.

**Modifiche necessarie:**

| Riga attuale | Sostituire con |
|-------------|----------------|
| `get_active_agent(issue_id=...)` | `worker_get_active_agent(issue_id=...)` |
| `get_active_pipeline_run(issue_id=...)` | `worker_get_active_pipeline_run(issue_id=...)` |
| `get_pipeline_messages(run_id=...)` | `worker_get_pipeline_messages(run_id=...)` |
| `get_issue_details(project_id=..., issue_id=...)` | `worker_get_issue_details(project_id=..., issue_id=...)` |
| `set_issue_name` | `worker_set_issue_name` |
| `send_agent_message` | `worker_send_agent_message` |
| `finished_pipeline_step` | ✅ **invariato** (solo worker, nessun overlap) |

### 7.3 `hermes_skills/run-pipeline/SKILL.md`

**Modifiche necessarie** (stessa mappa del worker):

| Nome attuale | Nuovo nome |
|-------------|------------|
| `get_active_agent` | `worker_get_active_agent` |
| `get_active_pipeline_run` | `worker_get_active_pipeline_run` |
| `get_issue_details` | `worker_get_issue_details` |
| `get_pipeline_messages` | `worker_get_pipeline_messages` |
| `set_issue_name` | `worker_set_issue_name` |
| `finished_pipeline_step` | ✅ invariato |

### 7.4 `hermes_skills/run-issue/SKILL.md`

| Nome attuale | Nuovo nome |
|-------------|------------|
| `get_issue_details` | `worker_get_issue_details` |
| `set_issue_name` | `worker_set_issue_name` |
| `get_project_context` | `worker_get_project_context` |

### 7.5 `hermes_skills/ask-and-brainstorm/SKILL.md`

| Nome attuale | Nuovo nome |
|-------------|------------|
| `get_project_context` | `worker_get_project_context` |

### 7.6 `hermes_skills/AGENTS.md`

**Nessuna modifica necessaria** (è un file di contesto generale, non referenzia
tool specifici per nome).

### 7.7 `backend/app/routers/system.py`

Riga 54, messaggio all'utente:
```
"con ~39 tool worker per spawn auto-mode (run-issue, pipeline, ecc.)"
```
→ aggiornare il numero tool (saranno ~28 dopo la pulizia). Opzionale.

### 7.8 `backend/app/mcp/dual-mcp-architecture.md` (reference doc)

Il reference doc nella skill `manager-ai-orchestrator` è un file che descrive
l'architettura. Va aggiornato per riflettere lo stato finale dopo la
refatorizzazione (tool count aggiornato, niente più overlap).

---

## Fase 8 — Verifica e Test

### 8.1 Dopo ogni fase: syntax check

```bash
cd backend && python -c "from app.mcp.server import mcp; print(f'Worker OK: {len(list(mcp._tool_manager._tools))} tools')"
cd backend && python -c "from app.mcp.orchestrator_server import orchestrator_mcp; print(f'Orch OK: {len(list(orchestrator_mcp._tool_manager._tools))} tools')"
```

### 8.2 Verificare zero overlap

Script di verifica:

```python
from app.mcp.server import mcp as worker_mcp
from app.mcp.orchestrator_server import orchestrator_mcp as orch_mcp

worker_names = set(tool.name for tool in list(worker_mcp._tool_manager._tools))
orch_names = set(tool.name for tool in list(orch_mcp._tool_manager._tools))

overlap = worker_names & orch_names
print(f"Worker tools: {len(worker_names)}")
print(f"Orch tools:   {len(orch_names)}")
print(f"Overlap:      {len(overlap)}")
if overlap:
    print(f"Overlapping:  {overlap}")
else:
    print("✅ ZERO overlap — obiettivo raggiunto!")
```

### 8.3 Test funzionale: avviare il backend

```bash
cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 8.4 Verificare elenco tool MCP

```bash
# Worker MCP
curl -s http://localhost:8000/mcp/tools/list 2>/dev/null | python -c "import json,sys; d=json.load(sys.stdin); print(f'Worker: {len(d)} tools'); [print(f'  - {t[\"name\"]}') for t in d]"

# Orchestrator MCP
curl -s http://localhost:8000/mcp-orchestrator/tools/list 2>/dev/null | python -c "import json,sys; d=json.load(sys.stdin); print(f'Orch: {len(d)} tools'); [print(f'  - {t[\"name\"]}') for t in d]"
```

### 8.5 Verificare che non ci siano nomi collision

```bash
curl -s http://localhost:8000/mcp/tools/list | python -c "
import json,sys
worker = {t['name'] for t in json.load(sys.stdin)}
orch = {t['name'] for t in json.loads(open('/dev/stdin').read())} if False else {}
"
```

---

## Ordine di Esecuzione Consigliato

```
Fase 1  (Rimuovere 20 tool admin dal worker)     → ~15 min
   ↓
Fase 3  (list_plugins duplicato)                   → ~2 min (contiguo a Fase 1)
   ↓
Fase 6  (Spostare enable/disable plugin in orch)   → ~5 min
   ↓
Fase 4  (Rimuovere finished_pipeline_step da orch)  → ~3 min
   ↓
Fase 5  (Aggiungere memory_search all'orch)         → ~10 min
   ↓
Fase 2  (Prefissare 8 tool di frontiera)           → ~10 min
   ↓
Fase 7  (Aggiornare skill e documentazione)         → ~15 min
   ↓
Fase 8  (Verifica e test)                           → ~10 min
```

**Tempo stimato totale: ~70 minuti** (a cui aggiungere debug se necessario).

---

## Rischi e Note

1. **Compatibilità backward:** I tool rinominati (con prefisso `worker_`) romperanno
   qualsiasi script o skill che usa i vecchi nomi. Le skill Hermes vengono aggiornate
   in Fase 7, ma eventuali script esterni o workflow manuali dovranno essere aggiornati.

2. **Import non utilizzati:** Dopo Fase 1, verificare che non rimangano import
   di `AgentService`, `PipelineService`, `mcp_tool_wrapper` se nessun altro tool
   li usa. Il lint (`ruff` o `pylint`) li segnalerà.

3. **`mcp_tool_wrapper`:** Verificare se è usato da tool rimasti nel worker.
   Se non più usato, rimuovere l'import `from app.mcp.helpers import mcp_tool_wrapper`.

4. **`_serialize_agent` / `_serialize_pipeline`:** Queste funzioni helper locali
   in `server.py` potrebbero non servire più dopo la rimozione dei tool agent/pipeline.
   Verificare e rimuovere se inutilizzate.

5. **`ProjectService` import in server.py:** Verificare se ancora necessario
   (potrebbe servire per plugin tools rimasti).
