Controllare gli items disponibili per interagire con la pipeline.

Ho fatto eseguire una pipeline e l'agente era in grossa difficoltà su cosa fare, ha provato più volte a chiamare dei tools ma senza successo, non c'è una direzione concreta da seguire.

Il flusso dovrebbe essere:
- starto manualmente la pipeline
- terminale si apre con "/run-pipeline"
- claude code dalle info del comando run-pipeline capisce il flusso da seguire: 1) fetchare lo step attivo della pipeline 2) se nessun step attivo allora deve attivare il primo 3) chiama il tool run_pipeline_step 4) legge le informazioni dello step dell'agente, e legge intent agente 5) segue alla lettera l'intent dell'agente 6) esegue il task 7) finisce il task e dichiara finished_pipeline_step 8) il terminale si chiude da solo e automaticamente si apre un nuovo terminale e tutto il ciclo si ripete

Tutto chiaro? Ti chiedo di analizzare profondamente l'implementazione della pipeline e di verificare che il flusso sia questo e soprattutto sia coerente, l'agente non deve avere nessun dubbio su come e cosa fare per proseguire nella pipeline