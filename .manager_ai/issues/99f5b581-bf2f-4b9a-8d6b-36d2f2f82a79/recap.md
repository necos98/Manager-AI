## Riepilogo

Aggiunto plugin MySQL read-only al catalogo di Manager AI.

**File creato:** `backend/plugins/mysql/plugin.yaml`

**Dettagli:**
- Package: `mcp-server-mysql` (PyPI v0.1.4) via `uvx`
- Transport: stdio
- Access level: `read_only`
- 5 opzioni configurabili: `MYSQL_HOST`, `MYSQL_PORT` (default 3306), `MYSQL_USER`, `MYSQL_PASSWORD` (secret), `MYSQL_DATABASE`

**Nessun codice scritto** — il plugin è puramente dichiarativo. `CatalogLoader` lo rileva automaticamente allo startup. L'utente lo configura e abilita dalla UI di Manager AI.

Validato con successo contro il modello Pydantic `CatalogPlugin`.