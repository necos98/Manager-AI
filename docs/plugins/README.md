# MCP Plugin System

Manager AI supporta plugin MCP (Model Context Protocol) per estendere le capacità dell'LLM con tool esterni. I plugin sono predefiniti dagli sviluppatori in un **catalogo built-in** — l'utente finale deve solo configurarli e abilitarli.

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
│  │  CatalogLoader  ──►  PluginManager    │   │
│  │  backend/plugins/*/plugin.yaml        │   │
│  │  + .manager_ai/plugins.yaml (v2)      │   │
│  └─────────────────┬─────────────────────┘   │
└────────────────────┼─────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  MCP Server esterno │
          │  via stdio o HTTP   │
          └─────────────────────┘
```

## Due livelli

| Livello | Chi lo gestisce | File | Contenuto |
|---------|----------------|------|-----------|
| **Catalogo** | Sviluppatori | `backend/plugins/<key>/plugin.yaml` | Nome, descrizione, transport, command, options schema |
| **Configurazione** | Utente finale | `.manager_ai/plugins.yaml` (v2) | `enabled` + valori delle options configurate |

## Come funziona

1. **Catalogo**: Gli sviluppatori aggiungono plugin alla cartella `backend/plugins/`. Ogni plugin è una sottocartella con un `plugin.yaml`.
2. **Avvio**: Allo startup, `CatalogLoader` scansiona `backend/plugins/*/plugin.yaml` e carica tutti i manifest nel catalogo.
3. **Configurazione**: L'utente apre la pagina Plugins nel progetto, vede la lista dei plugin disponibili, clicca **Configure**, riempie i campi richiesti dal plugin, abilita.
4. **Merge**: `CatalogLoader.build_runtime_config()` unisce la definizione del catalogo (command, transport) con la configurazione utente (valori dei campi) → `PluginConfig`.
5. **Esecuzione**: `PluginManager` riceve il `PluginConfig` e spawna il processo plugin. I valori configurati dall'utente vengono iniettati come variabili d'ambiente.
6. **Proxy**: I tool del plugin appaiono con prefisso `{plugin}__` nel singolo endpoint `/mcp`.

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
| `backend/plugins/<key>/plugin.yaml` | Manifest del plugin nel catalogo (source of truth per il dev) |
| `.manager_ai/plugins.yaml` | Configurazione utente per-progetto: `enabled` + `config` |
| `app/mcp/catalog.py` | CatalogLoader: carica i manifest, fornisce `build_runtime_config()` |
| `app/mcp/plugin_config.py` | Modelli Pydantic v2: `ProjectPluginConfig`, v1→v2 migration |
| `app/mcp/plugin_client.py` | Client MCP (stdio + HTTP) |
| `app/mcp/plugin_proxy.py` | Registrazione proxy tool su FastMCP |
| `app/mcp/plugin_manager.py` | Orchestratore lifecycle (invariato, riceve PluginConfig) |
| `app/routers/plugins.py` | REST API + endpoint catalogo `GET /api/plugins/catalog` |
| `frontend/.../plugins-panel.tsx` | UI: catalogo, ConfigModal, lista enabled, legacy |

## Link

- [Aggiungere un plugin al catalogo](./adding-a-catalog-plugin.md) — per sviluppatori
- [Usare e configurare plugin](./configuration.md) — per utenti finali
