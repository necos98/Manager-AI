## Evitare processi backend duplicati all'avvio di Manager AI

### Problema
Quando si avvia `start.py` mentre il backend è già in esecuzione (lancio multiplo, crash non pulito, riavvio), viene creato un secondo processo uvicorn sulla stessa porta (8001). Il nuovo processo non riesce a bindare la porta → crash silenzioso o conflitto. L'utente vede l'app "ballare" senza capire perché.

### Requisiti

1. **Prima di avviare il backend**, verificare se esiste già un processo in ascolto sulla porta configurata (`BACKEND_PORT`, di default 8001)
2. **Se trovato**, terminarlo con `taskkill /F /PID <pid>` prima di avviare il nuovo backend
3. **Loggare** l'azione: `"Trovato backend già in esecuzione su PID <X>, terminazione..."` in caso di kill, o `"Nessun backend precedente trovato sulla porta <X>"` se tutto è pulito
4. **Fallimento kill** → log warning (`"Impossibile terminare il processo PID <X>: <errore>"`) e continua comunque (meglio provare e fallire che non provare affatto)
5. **Non toccare** altri processi Python — identificare solo il processo che occupa la porta specifica

### Strategia di rilevamento

Usare `netstat -ano` (Windows nativo, nessuna dipendenza) per trovare il PID in ascolto sulla porta TCP:
```
netstat -ano | findstr :8001
```
Output tipico:
```
TCP    0.0.0.0:8001    0.0.0.0:LISTENING    12345
```
Il PID è l'ultimo campo. Usare `taskkill /F /PID 12345` per terminare.

### Casi da gestire

- **Nessun processo trovato** → avvio normale, log info
- **Processo trovato, kill OK** → log, poi avvio normale
- **Processo trovato, kill fallisce** (es. accesso negato) → log warning, continua
- **Più processi sulla stessa porta** (raro, ma possibile in error states) → killarli tutti
- **Sistema non Windows** (fallback per Linux/macOS) → non implementato in questa issue, ma strutturare il codice in modo che sia facile estendere

### Impatto

- Solo `start.py` viene modificato
- Nessuna modifica al backend, frontend, database o API
- La modifica è lineare e sicura: una nuova funzione + una chiamata in `main()`

### Non in scope

- Rilevamento per Linux/macOS (usare `lsof -i :<port>` e `kill`)
- Riavvio automatico del backend se muore in esecuzione
- Health check periodici
