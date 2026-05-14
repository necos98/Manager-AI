# MCP Plugin System

Manager AI supporta plugin MCP (Model Context Protocol) per estendere le capacità dell'LLM con tool esterni. Un plugin è un server MCP standard che viene connesso al singolo endpoint `/mcp` di Manager AI — i suoi tool appaiono automaticamente nel contesto di Claude Code con prefisso `{plugin}__`.

## Architettura

```
Claude Code
    │
    ▼
┌─────────────────────────────────────────────┐
│  Manager AI  /mcp (single endpoint)         │
│                                              │
│  ┌─ Built-in tools (issue, memory, ...)  ─┐ │
│  │  ┌─ PluginProxy (mysql) ────────────┐  │ │
│  │  │  mysql__list_tables               │  │ │
│  │  │  mysql__query                     │  │ │
│  │  └──────────────┬────────────────────┘  │ │
│  └─────────────────┼───────────────────────┘ │
│                    │                         │
│  ┌─────────────────▼─────────────────────┐   │
│  │  PluginManager                        │   │
│  │  - Legge .manager_ai/plugins.yaml     │   │
│  │  - Spawna/connette plugin             │   │
│  │  - Registra proxy tool su FastMCP     │   │
│  └─────────────────┬─────────────────────┘   │
└────────────────────┼─────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  MCP Server (mysql) │
          │  via stdio o HTTP   │
          └─────────────────────┘
```

## Come funziona

1. **Configurazione**: Plugin definiti in `.manager_ai/plugins.yaml` per-progetto
2. **Avvio**: Allo startup, `PluginManager` spawna i processi plugin via stdio o si connette via HTTP/SSE
3. **Handshake MCP**: Esegue `initialize` e `tools/list` per scoprire i tool del plugin
4. **Proxy**: Per ogni tool scoperto, registra una funzione proxy su FastMCP con nome `{plugin}__{tool}`
5. **Invocazione**: Quando Claude Code chiama `mysql__query(...)`, la richiesta è forwardata al plugin MCP
6. **Watchdog**: Modifiche a `plugins.yaml` vengono rilevate dal filesystem watcher e i plugin vengono ricaricati

## Livelli di accesso

| Livello | Significato | Enforcement |
|---------|------------|-------------|
| `read_only` | Solo SELECT / lettura | Descritto all'LLM; enforcement a livello credenziali DB |
| `read_write` | INSERT, UPDATE, DELETE | Descritto all'LLM |
| `admin` | DDL, gestione schema | Descritto all'LLM |

Il tag viene iniettato nella descrizione del tool: `[mysql plugin — read_only]`.

## File del sistema

| File | Ruolo |
|------|-------|
| `.manager_ai/plugins.yaml` | Configurazione plugin (source of truth) |
| `app/mcp/plugin_config.py` | Modelli Pydantic, load/save YAML |
| `app/mcp/plugin_client.py` | Client MCP (stdio + HTTP) |
| `app/mcp/plugin_proxy.py` | Registrazione proxy tool su FastMCP |
| `app/mcp/plugin_manager.py` | Orchestratore lifecycle |
| `app/routers/plugins.py` | REST API per frontend |
| `frontend/.../plugins-panel.tsx` | UI gestione plugin |

## Link

- [Creare un plugin MCP](./creating-a-plugin.md)
- [Configurazione plugin](./configuration.md)
