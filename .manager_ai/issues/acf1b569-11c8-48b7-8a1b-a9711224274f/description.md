Evitare processi backend duplicati all'avvio di Manager AI

Attualmente quando si avvia Manager AI (start.py), se il backend è già in esecuzione per un lancio multiplo o un crash, viene avviato un secondo processo sulla stessa porta 8001 → conflitti, crash, "si bagga".

Modificare start.py per:
1. All'avvio, verificare se esiste già un processo backend (uvicorn su porta 8001)
2. Se trovato, killarlo con taskkill /F /PID prima di avviare il nuovo backend
3. Loggare: "Trovato backend già in esecuzione su PID X, terminazione..."

Identificazione processo:
- Usare netstat -ano per trovare il PID sulla porta 8001
- Oppure wmic/tasklist per cercare processi Python con uvicorn

Casi da gestire:
- Nessun processo → avvio normale
- Backend trovato → kill + nuovo avvio
- Altri processi Python → non toccare
- Fallimento kill → log warning e continua

File: start.py nella root del repository