Se uno step viene dichiarato FAILED la pipeline viene totalmente killata ed interrotta, lasciando il terminale spawnato orfano. Questo chiaramente non deve assolutamente accadere.

Modificare il behaviour nel seguente modo:
- aggiungere alla dichiarazione della pipeline, degli eventi (creare un sistema solito ed espandibile NON monolitico), ad esempio quando uno step dell'agente X rejecta, l'utente può scegliere, all'interno della configurazione della pipeline a quale step far ritornare la pipeline.
Esempio: agente 4 dice che lo step è rejectato => agente 4 chiude il suo lavoro => sistema controlla cosa succede se agente 4 rejecta=> vede che se agente 4 rejecta allora ritorna ad agente 2 => sistema imposta agente corrente 2 => pipeline riprendere da agente 2 => agente 2 legge la chat (system prompt di /run-pipeline) e nota che agente 4 ha contestato qualcosa => pipeline continua a scorrere naturalmente.


Tutto chiaro?