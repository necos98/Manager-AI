# Aggiungere un plugin al catalogo

Un plugin di catalogo è una cartella in `backend/plugins/` con un file `plugin.yaml`. Nessun codice Python richiesto — solo YAML dichiarativo.

## Struttura

```
backend/plugins/
├── filesystem/
│   └── plugin.yaml
├── memory/
│   └── plugin.yaml
└── mysql/
    └── plugin.yaml
```

Il nome della cartella diventa la **key** del plugin (es. `mysql`).

## Formato plugin.yaml

```yaml
name: "MySQL Database"         # Nome visualizzato
description: "Esegue query SQL su database MySQL"
transport: stdio               # stdio | http
command: "uvx"                 # Obbligatorio per stdio
args:                          # Obbligatorio per stdio
  - "mcp-server-mysql"
access_level: read_only        # read_only | read_write | admin
timeout: 30                    # Timeout in secondi (default: 30)
options:                       # Opzioni configurabili dall'utente
  - key: MYSQL_HOST
    label: "Host"
    type: string               # string | secret | number | boolean | select
    required: true
    placeholder: "localhost"
  - key: MYSQL_PORT
    label: "Porta"
    type: string
    required: false
    default: "3306"
  - key: MYSQL_USER
    label: "Username"
    type: string
    required: true
  - key: MYSQL_PASSWORD
    label: "Password"
    type: secret               # Campo password (mascherato in UI)
    required: true
```

### Campi del manifest

| Campo | Tipo | Obbligatorio | Descrizione |
|-------|------|-------------|------------|
| `name` | string | Sì | Nome visualizzato nella UI |
| `description` | string | No | Descrizione (mostrata nella card e nella modale) |
| `transport` | string | No (default: `stdio`) | `stdio` per processo locale, `http` per remoto |
| `command` | string | Solo stdio | Comando eseguibile |
| `args` | list | Solo stdio | Argomenti del comando |
| `url` | string | Solo http | URL dell'endpoint SSE |
| `access_level` | string | No (default: `read_only`) | `read_only`, `read_write`, `admin` |
| `timeout` | int | No (default: `30`) | Timeout in secondi per chiamata tool |
| `options` | list | No | Opzioni configurabili dall'utente (vedi sotto) |

### Tipi di option

| Tipo | UI | Esempio |
|------|----|--------|
| `string` | Input text | Hostname, nome database |
| `secret` | Input password (mascherato) | Password, API key |
| `number` | Input number | Porta, timeout |
| `boolean` | Checkbox / toggle | Flag abilita/disabilita feature |
| `select` | Dropdown | Ambiente (dev/staging/prod) |

### Option con choices (select)

```yaml
options:
  - key: LOG_LEVEL
    label: "Livello di log"
    type: select
    required: false
    default: "info"
    choices:
      - value: "debug"
        label: "Debug"
      - value: "info"
        label: "Info"
      - value: "warn"
        label: "Warning"
```

### Plugin HTTP

```yaml
name: "Slack Notifications"
description: "Invia notifiche su canali Slack"
transport: http
url: "https://mcp-slack.internal/sse"
access_level: read_write
options:
  - key: SLACK_TOKEN
    label: "Bot Token"
    type: secret
    required: true
```

### Plugin senza opzioni

Se il plugin non ha opzioni configurabili, `options` può essere vuoto o omesso. L'utente vedrà solo il toggle enable/disable.

```yaml
name: "Memory"
description: "Knowledge graph per contesto persistente"
transport: stdio
command: "npx"
args:
  - "-y"
  - "@modelcontextprotocol/server-memory"
access_level: read_write
```

## Come vengono usate le options

Quando l'utente configura e abilita il plugin, i valori delle options vengono **iniettati come variabili d'ambiente** nel processo del plugin MCP.

Esempio: se l'utente configura `MYSQL_HOST=10.0.1.5` e `MYSQL_USER=admin`, il processo plugin riceve:

```
MYSQL_HOST=10.0.1.5
MYSQL_USER=admin
MYSQL_PASSWORD=secret123
```

Il server MCP deve leggere queste variabili d'ambiente per connettersi al servizio.

## Validazione

All'avvio, `CatalogLoader` valida ogni `plugin.yaml`:

- Se `transport: stdio`, `command` è obbligatorio
- Se `transport: http`, `url` è obbligatorio
- Le `options` devono avere `key` e `label` validi
- I `choices` devono avere `value` e `label`
- Manifest invalidi → warning nel log, plugin saltato (non blocca l'avvio)
- Chiavi duplicate → errore all'avvio

## Plugin d'esempio

Guarda i plugin già presenti nella cartella `backend/plugins/`:
- `filesystem/plugin.yaml` — server filesystem MCP con opzione `ALLOWED_DIR`
- `memory/plugin.yaml` — server memory MCP (nessuna opzione)
