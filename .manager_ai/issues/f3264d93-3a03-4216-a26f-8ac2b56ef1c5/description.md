Agenti e pipeline non visibili nel frontend nonostante l'auto-seed backend funzioni. La gestione pipeline è fragile — manca feedback visivo, error handling, e la UI non riflette lo stato reale.

Da verificare e irrobustire:

1. **Visibilità agenti**: Il GET /api/projects/{id}/agents chiama ensure_default_agents ma nel frontend gli agenti non compaiono. Possibile mismatch API → frontend o problema di caricamento.

2. **Visibilità pipeline**: Stesso problema — ensure_default_pipeline esiste ma la UI non mostra pipeline esistenti.

3. **Robustezza pipeline**:
   - Error handling in start_pipeline (timeout, agent non trovato)
   - Retry su step fallito
   - Stato pipeline più granulare
   - Logging migliore
   - Possibilità di skippare step non critici da UI

4. **API consistency**: Verificare che tutte le route backend (agents, pipelines, pipeline_runs) siano registrate in main.py e che il prefisso corrisponda a quello che il frontend chiama.