## Riepilogo

Rimossi due plugin MCP ridondanti dal catalog:

- **`backend/plugins/memory/`** — `@modelcontextprotocol/server-memory`. Knowledge graph memory esterno, ridondante perche Manager AI ha il suo sistema memory integrato (tools `memory_*` project-scoped).
- **`backend/plugins/filesystem/`** — `@modelcontextprotocol/server-filesystem`. Accesso file system esterno, ridondante perche Claude Code ha accesso nativo al filesystem.

Nessun `plugins.yaml` da aggiornare (i plugin non erano abilitati). CatalogLoader gestisce directory mancanti nativamente. Zero impatto runtime.

Plugin MySQL (`backend/plugins/mysql/`) preservato: ha feature reale (accesso MySQL read-only) che Claude Code non offre nativamente.
