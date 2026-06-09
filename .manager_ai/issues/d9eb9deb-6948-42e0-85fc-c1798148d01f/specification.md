## Specifica: Test integrazione ask_user_question

### Obiettivo
Scrivere test di integrazione per la funzione `ask_user_question` (MCP tool) che verifichino il ciclo completo: creazione domanda → attesa risposta → risposta via REST API → recezione corretta della risposta.

### Contesto
Attualmente esistono test unitari per `ask_user_question` in `backend/tests/test_mcp_tools.py` che usano mock per `question_store.wait()` e `async_session`. Manca un test che eserciti il flusso reale:
1. Chiamata a `ask_user_question` (che blocca in attesa di risposta via `asyncio.Event`)
2. Risposta inviata via `POST /api/questions/{id}/answer`
3. Verifica che la risposta venga recepita correttamente

### Casi da testare
1. **Con opzioni**: `ask_user_question` con `options=["sì", "no"]` → risposta con selected_option
2. **Senza opzioni**: `ask_user_question` senza options → risposta testuale libera
3. **Timeout**: chiamata senza risposta → verifica `timed_out=True`
4. **API questions**: verifica che `GET /api/questions`, `GET /api/questions/pending`, `GET /api/questions/count` funzionino correttamente dopo una domanda e dopo la risposta

### Strategia di test
I test MCP tool sono in `backend/tests/test_mcp_tools.py` e usano `mcp_server` (istanza FastMCP) con chiamate dirette ai tool. Per testare il flusso bloccante di `ask_user_question`, useremo `asyncio.create_task` per lanciare la chiamata in background e `httpx.AsyncClient` (o il test client FastAPI) per rispondere via REST, poi fare assert sul risultato.

### Approccio tecnico
- Usare `asyncio.create_task()` per chiamare `mcp_server.ask_user_question(...)` in background
- `await asyncio.sleep(0.1)` per dare tempo al task di creare la domanda e iniziare ad aspettare
- Usare il `TestClient` (o direttamente la sessione DB + question_service) per rispondere via `answer_question`
- `await task` per ottenere il risultato della domanda
- Verificare answer, selected_option, timed_out

### File da modificare
- `backend/tests/test_mcp_tools.py` — aggiungere nuovi test di integrazione
