In `_run_step()`, se l'agente esce dal PTY senza chiamare `finished_pipeline_step`, la pipeline avanza comunque — il `pty_task` vince la gara, viene loggato un warning, ma il passo è considerato completato (se `pty_died_naturally=True`).

Questo fallback è utile come safety net (agente crasha, network issue, etc.), ma può mascherare agenti che:
- Non seguono il flusso documentato
- Si dimenticano di chiamare `finished_pipeline_step`
- Escono prematuramente senza completare il lavoro

Possibili soluzioni:
- Rendere `finished_pipeline_step` obbligatorio: se PTY muore senza evento, step = FAILED
- Distinguere PTY death "pulita" (exit code 0 dopo aver chiamato finished_pipeline_step) da PTY death "sporca" (exit code != 0 o senza chiamata)
- Aggiungere un grace period: dopo che il PTY muore, aspettare N secondi per un eventuale finished_pipeline_step ritardato