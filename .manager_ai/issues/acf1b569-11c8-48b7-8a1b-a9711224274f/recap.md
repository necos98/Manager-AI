## Recap: Evitare processi backend duplicati all'avvio

### Cosa è stato fatto
Aggiunte due funzioni in `start.py`:

1. **`_get_pids_on_port(port)`** — usa `netstat -ano` per trovare i PID dei processi in ascolto (LISTENING) su una porta specifica. Gestisce: netstat non trovato, output vuoto, più PID sulla stessa porta.

2. **`_kill_existing_backend(port)`** — chiama `_get_pids_on_port()` e per ogni PID trovato esegue `taskkill /F /PID`. Non solleva mai eccezioni: logga warning se taskkill fallisce o non è disponibile.

3. **Chiamata in `main()`** — `_kill_existing_backend(backend_port)` viene chiamato subito dopo aver letto la porta, prima di `check_prerequisites()`.

### Test effettuati
7 test su logica di parsing (simulando output netstat) e gestione errori:
- Output vuoto → nessun PID
- Porta con 2 PID → trovati entrambi
- Porta diversa → nessun match
- netstat mancante → graceful fallback
- taskkill successo → log ok
- taskkill fallimento → log warning, continua
- Nessun backend → log info

### Comportamento
All'avvio di `start.py`:
```
[ok] Nessun backend precedente trovato sulla porta 8001
```
Oppure, se c'è un backend zombie:
```
[...] Trovato backend già in esecuzione su PID 12345, terminazione...
[ok] Processo PID 12345 terminato con successo
```
