# MySQL Read-Only MCP Plugin

## Obiettivo

Aggiungere al catalogo plugin di Manager AI un plugin MCP per database MySQL in **sola lettura**.

## Cosa serve

Aggiungere il manifest `backend/plugins/mysql/plugin.yaml` al catalogo built-in.

**Nessun codice** — il plugin è puramente dichiarativo. Il server MCP esiste già: `mcp-server-mysql` su PyPI (v0.1.4, Python >=3.12). Manager AI fa da proxy: spawna il processo, inietta le env vars configurate dall'utente, registra i tool con prefisso `mysql__`.

## Package

- **Nome:** [`mcp-server-mysql`](https://pypi.org/project/mcp-server-mysql/)
- **Versione:** 0.1.4
- **Runtime:** Python >=3.12
- **Comando:** `uvx mcp-server-mysql`
- **Env vars:** `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

## Manifest

```yaml
name: "MySQL Database"
description: "Read-only SQL queries and schema inspection on MySQL databases"
transport: stdio
command: "uvx"
args:
  - "mcp-server-mysql"
access_level: read_only
timeout: 30
options:
  - key: MYSQL_HOST
    label: "Host"
    type: string
    required: true
    placeholder: "localhost"
  - key: MYSQL_PORT
    label: "Port"
    type: string
    required: false
    default: "3306"
  - key: MYSQL_USER
    label: "Username"
    type: string
    required: true
  - key: MYSQL_PASSWORD
    label: "Password"
    type: secret
    required: true
  - key: MYSQL_DATABASE
    label: "Database"
    type: string
    required: true
    placeholder: "my_database"
```

## Decisioni

1. **`uvx` come comando** — il package è Python (PyPI), non Node. `uvx` è il runner standard per package Python.
2. **`read_only` come access_level** — requisito esplicito dell'issue ("SOLA lettura"). L'LLM viene informato tramite descrizione tool, enforcement reale a livello credenziali DB.
3. **`MYSQL_DATABASE` obbligatorio** — migliore UX rispetto a lasciarlo vuoto e fallire alla prima query.
4. **5 opzioni totali** — coprono tutti i parametri di connessione standard. `MYSQL_PORT` ha default `3306`, tutte le altre sono required.

## Impatto

- **Nessuna modifica al codice esistente.** Solo un nuovo file YAML.
- `CatalogLoader` lo rileva automaticamente allo startup.
- Il plugin appare nella UI in "Disponibili" finché l'utente non lo configura e abilita.