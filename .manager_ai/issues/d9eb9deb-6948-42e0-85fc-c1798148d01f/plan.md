## Piano di implementazione: Test integrazione ask_user_question

### Strategia
Aggiungere 4 nuovi test di integrazione in `backend/tests/test_mcp_tools.py` che esercitano il ciclo reale di `ask_user_question`:
1. Creazione domanda con opzioni → risposta via QuestionService → verifica risposta
2. Creazione domanda senza opzioni → risposta via QuestionService → verifica risposta testuale
3. Timeout: domanda senza risposta → verifica timed_out
4. Verifica API questions REST (GET /api/questions, /pending, /count)

Pattern per aggirare la natura bloccante di ask_user_question:
- Usare `asyncio.create_task()` per lanciare la chiamata MCP in background
- `await asyncio.sleep(0.2)` per dare tempo alla domanda di essere creata
- Usare `question_store.get_all_pending()` per scoprire la question_id
- Chiamare `QuestionService(session).answer_question(id, answer, option)` per rispondere
- `await task` per ottenere il risultato e fare assert

Per il test timeout: timeout_seconds=1, non rispondere, catturare asyncio.TimeoutError dal task.

### Casi di test
1. **test_ask_user_question_with_options**: con options=["sì", "no"], rispondere "Sì, procedi" con selected_option="sì"
2. **test_ask_user_question_without_options**: senza options, rispondere "Testo libero di risposta"
3. **test_ask_user_question_timeout**: con timeout_seconds=1, non rispondere, verificare timed_out=True
4. **test_ask_user_question_rest_api**: usare httpx.AsyncClient per POST /api/questions/{id}/answer, verificare che l'API funzioni e che il MCP tool riceva la risposta

### File da modificare
- `backend/tests/test_mcp_tools.py` — aggiungere nuovi test
