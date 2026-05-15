## Problem

Due plugin nel catalog MCP (`memory` e `filesystem`) sono ridondanti e non servono al progetto Manager AI.

- **Memory** (`@modelcontextprotocol/server-memory`): knowledge graph memory esterno. Manager AI ha gia un sistema di memory integrato (tools `memory_create`, `memory_delete`, `memory_update`, `memory_search`, `memory_link`, `memory_unlink`) project-scoped e integrato nel workflow.
- **Filesystem** (`@modelcontextprotocol/server-filesystem`): accesso file system esterno. Claude Code ha gia accesso nativo al filesystem (tools Read, Write, Edit, Glob, Grep, Bash).

Nessuno dei due e abilitato a livello progetto (nessun `plugins.yaml`). Appaiono solo nella UI come "disponibili", generando confusione.

## Soluzione

Rimuovere le directory `backend/plugins/memory/` e `backend/plugins/filesystem/` dal catalog.

## Cosa NON toccare

- `backend/plugins/mysql/` — plugin utile con feature reale
- Sistema memory built-in di Manager AI
- Codice PluginManager/CatalogLoader — gia gestisce catalog vuoti

## Impatto

Nessuno. I plugin non erano abilitati, nessun `plugins.yaml` da aggiornare, nessuna dipendenza runtime.
