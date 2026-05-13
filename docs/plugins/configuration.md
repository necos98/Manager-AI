# Configurare un plugin MCP

I plugin si configurano per-progetto. La source of truth è il file `.manager_ai/plugins.yaml` nella root del progetto.

## Via Frontend (UI)

1. Vai al progetto in Manager AI
2. Nel menu "More" (⋮) del progetto, clicca **MCP Plugins**
3. Clicca **Add Plugin**
4. Compila i campi:

| Campo | Descrizione | Esempio |
|-------|------------|--------|
| Key | ID univoco del plugin nel progetto | `mysql` |
| Display Name | Nome mostrato nell'UI | `MySQL (produzione)` |
| Transport | `stdio` per processo locale, `http` per remoto | `stdio` |
| Command | (solo stdio) Comando da eseguire | `uvx mcp-server-mysql` |
| URL | (solo http) URL dell'endpoint SSE | `https://mcp.internal/sse` |
| Access Level | Vincolo dichiarativo per l'LLM | `read_only` |

5. Clicca **Save**. Il plugin viene avviato immediatamente.

### Gestione plugin

- **Toggle on/off**: Abilita o disabilita il plugin senza rimuovere la configurazione
- **Delete**: Rimuove il plugin e ferma il processo
- **Stato**: Verde = connesso (con conteggio tool). Rosso = fermo o errore.

## Via YAML (manuale)

Edita `.manager_ai/plugins.yaml` direttamente:

### Plugin stdio (database MySQL read-only)

```yaml
schema_version: 1
plugins:
  mysql:
    name: "MySQL (produzione)"
    enabled: true
    transport: stdio
    command: "uvx"
    args:
      - "mcp-server-mysql"
    env:
      MYSQL_HOST: "10.0.1.5"
      MYSQL_PORT: "3306"
      MYSQL_DATABASE: "analytics"
    access_level: read_only
    timeout: 30
```

### Plugin HTTP (remoto)

```yaml
schema_version: 1
plugins:
  slack:
    name: "Slack notifications"
    enabled: false
    transport: http
    url: "https://mcp-slack.internal/sse"
    access_level: read_write
    timeout: 30
```

### Campi YAML

| Campo | Tipo | Obbligatorio | Default | Descrizione |
|-------|------|-------------|---------|------------|
| `name` | string | No | `key` | Nome visualizzato |
| `enabled` | bool | No | `true` | Plugin attivo all'avvio |
| `transport` | string | No | `stdio` | `stdio` o `http` |
| `command` | string | Solo stdio | `""` | Comando eseguibile |
| `args` | list | No | `[]` | Argomenti del comando |
| `url` | string | Solo http | `""` | URL endpoint SSE |
| `env` | dict | No | `{}` | Variabili d'ambiente |
| `access_level` | string | No | `read_only` | `read_only`, `read_write`, `admin` |
| `timeout` | int | No | `30` | Timeout in secondi per chiamata tool |

## Sicurezza: credenziali

**Non mettere password nel YAML.** Usa il vault crittografato di Manager AI:

```yaml
# plugins.yaml — SOLO riferimento a variabili d'ambiente
env:
  MYSQL_HOST: "${MYSQL_HOST}"
  MYSQL_USER: "${MYSQL_USER}"
  MYSQL_PASSWORD: "${MYSQL_PASSWORD}"
```

Le credenziali vere si salvano via MCP tool `set_credential` o via UI Project Settings → Credentials. Il vault usa crittografia Fernet.

## Access Level e sicurezza reale

Il campo `access_level` è **dichiarativo**: viene iniettato nella descrizione del tool visibile all'LLM per fargli capire i vincoli. Ma NON è un enforcement.

Per un plugin MySQL read-only, la sicurezza reale si ottiene con:
1. **Utente DB limitato**: Il DBA crea un utente con solo `SELECT` grant
2. **Credenziali nel vault**: La password di quell'utente è nel vault crittografato
3. **Variabili d'ambiente**: Il plugin riceve solo le credenziali dell'utente limitato

## Ricaricare la configurazione

Le modifiche a `plugins.yaml` vengono rilevate automaticamente dal filesystem watcher:
- **Plugin aggiunto**: spawnato e connesso
- **Plugin rimosso**: fermato e disconnesso
- **Plugin modificato** (command, args, url): riavviato con la nuova configurazione
- **enabled cambiato**: avviato o fermato

Il ricaricamento avviene entro ~500ms dal salvataggio del file (debounce del watcher).

## Troubleshooting

**Il plugin non si avvia**
- Controlla che il comando esista nel PATH (`which uvx` o simile)
- Verifica il log del backend per errori di connessione
- Prova ad avviare il comando manualmente nel terminale

**Il plugin crasha dopo l'avvio**
- Controlla lo stderr del processo (loggato dal backend)
- Verifica che le variabili d'ambiente siano corrette
- Dopo 3 retry falliti in 60 secondi, il plugin va in cooldown per 5 minuti

**I tool non appaiono in Claude Code**
- Verifica che il plugin sia `enabled: true`
- Controlla lo stato nella UI: deve mostrare "X tools" in verde
- Verifica il log: cerca `Registered proxy tool: nomeplugin__nometool`
