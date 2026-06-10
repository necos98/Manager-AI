## Piano di implementazione

### Task 1: Aggiungere funzione `_kill_existing_backend(port)` in start.py

Inserire dopo `_ensure_app_icon()` (o prima di `main()`) una nuova funzione che:

1. Costruisce il comando `netstat -ano` e cerca la porta specifica
2. Esegue con `subprocess.run(capture_output=True, text=True)`
3. Fa il parsing dell'output con regex per estrarre i PID in stato LISTENING
4. Per ogni PID trovato:
   - Logga: `"Trovato backend già in esecuzione su PID <X>, terminazione..."`
   - Esegue `taskkill /F /PID <pid>`
   - Se fallisce, logga warning ma continua
5. Se nessun PID trovato: logga info che è tutto pulito
6. Usa `subprocess.run(capture_output=True, text=True)` con `check=False` per non sollevare eccezioni

### Task 2: Chiamare `_kill_existing_backend()` in `main()`

In `main()`, dopo `backend_port = int(os.environ.get("BACKEND_PORT", 8000))` e prima di `check_prerequisites()`, aggiungere la chiamata.

### Task 3: Test sintattico e verifica

- Verificare sintassi Python
- Testare la logica di parsing di `netstat -ano` con output simulato
- Assicurarsi che start.py importi ancora correttamente
