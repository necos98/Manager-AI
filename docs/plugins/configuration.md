# Usare e configurare i plugin

I plugin si configurano per-progetto dalla UI di Manager AI. Non serve scrivere YAML a mano.

## Interfaccia

1. Vai al progetto in Manager AI
2. Nel menu del progetto, clicca **MCP Plugins**
3. La pagina mostra tre sezioni:

### Plugin abilitati

In cima alla pagina, i plugin attualmente attivi mostrano:
- Nome e livello di accesso (badge colorato)
- Stato connessione: pallino verde + "N tools" oppure rosso + "stopped"
- Icona trasporto: terminale (stdio) o globo (http)
- Pulsante **Configure** (icona ingranaggio) per modificare la configurazione
- Toggle on/off per disabilitare rapidamente

### Plugin disponibili (catalogo)

Griglia di card con tutti i plugin nel catalogo non ancora abilitati:
- Nome, descrizione, livello di accesso
- Numero di opzioni configurabili
- Pulsante **Configure** per aprire la modale di configurazione

### Plugin legacy

Se esistono plugin creati prima del sistema a catalogo (versione 1), appaiono in una sezione separata in sola lettura. Possono solo essere disabilitati o eliminati — non modificati.

## Configurare un plugin

1. Clicca **Configure** su un plugin nella griglia
2. Si apre la modale con:
   - Nome, descrizione e livello di accesso del plugin
   - **Toggle Enable/Disable** per abilitare o disabilitare il plugin
   - **Campi di configurazione** generati automaticamente dal manifest:
     - `string` → campo testo
     - `secret` → campo password (mascherato)
     - `number` → campo numerico
     - `boolean` → toggle Yes/No
     - `select` → dropdown con le choices definite
   - I campi obbligatori sono contrassegnati con `*` rosso
3. Compila i campi richiesti
4. Clicca **Save**

Il plugin viene avviato immediatamente (se enabled). I valori configurati vengono iniettati come variabili d'ambiente nel processo del plugin.

### Plugin senza opzioni

Se un plugin non ha opzioni configurabili, la modale mostra solo il toggle enable/disable e un messaggio "This plugin has no configurable options."

## Formato plugins.yaml (v2)

La configurazione viene salvata automaticamente in `.manager_ai/plugins.yaml`:

```yaml
schema_version: 2
plugins:
  mysql:
    enabled: true
    config:
      MYSQL_HOST: "10.0.1.5"
      MYSQL_PORT: "3306"
      MYSQL_USER: "admin"
      MYSQL_PASSWORD: ""
```

Solo due campi per plugin: `enabled` (bool) e `config` (dict chiave-valore). Tutto il resto (comando, transport, access_level) viene dal catalogo.

### Migrazione da v1

Se hai un `plugins.yaml` in formato v1 (con `command`, `transport`, `env`, etc.), viene automaticamente migrato al formato v2 al primo avvio:

- `enabled` → `enabled` (invariato)
- `env` → `config` (le variabili d'ambiente diventano config)
- `name`, `command`, `transport`, `access_level`, `timeout` → **ignorati** (ora vengono dal catalogo)

I plugin v1 senza corrispondenza nel catalogo appaiono come **legacy** nella UI.

## Ricaricamento automatico

Le modifiche a `plugins.yaml` vengono rilevate dal filesystem watcher:

- **Plugin abilitato** → avviato
- **Plugin disabilitato** → fermato
- Il ricaricamento avviene entro ~500ms

## Sicurezza: credenziali

**Non mettere password in chiaro nelle option.** Per i campi di tipo `secret`:

- La UI li maschera con un input password
- Usa il vault crittografato di Manager AI per credenziali sensibili
- Le option `secret` vanno usate per valori sensibili che il plugin riceve come env var

Il campo `access_level` è **dichiarativo**: viene iniettato nella descrizione del tool visibile all'LLM, ma l'enforcement reale è a livello credenziali.

## Troubleshooting

**Il plugin non appare nel catalogo**
- Verifica che esista `backend/plugins/<key>/plugin.yaml`
- Controlla i log del backend per errori di validazione del manifest
- Il file YAML potrebbe essere malformattato

**Il plugin non si avvia**
- Controlla che il comando nel manifest esista nel PATH
- Verifica che tutte le option `required` siano state compilate
- Guarda i log del backend per errori di connessione

**Il plugin crasha dopo l'avvio**
- Controlla lo stderr del processo (loggato dal backend)
- Dopo 3 retry falliti in 60 secondi, il plugin va in cooldown per 5 minuti

**I tool non appaiono in Claude Code**
- Verifica che il plugin sia `enabled: true`
- Controlla lo stato nella UI: deve mostrare "N tools" in verde
- Verifica il log: cerca `Registered proxy tool: nomeplugin__nometool`
