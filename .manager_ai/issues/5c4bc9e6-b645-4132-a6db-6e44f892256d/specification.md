## Test Notifica Domanda su Telegram

### Obiettivo
Verificare che quando viene invocato `ask_user_question` su un'issue, la domanda venga notificata via Telegram e l'utente possa rispondere.

### Scenario di Test
1. Invocare `ask_user_question` MCP tool sull'issue corrente
2. Verificare che una notifica Telegram arrivi con formato ❓ + nome progetto + nome issue + domanda
3. L'utente risponde (tramite Telegram o UI Manager AI)
4. Verificare che la risposta venga catturata correttamente dal tool

### Criteri di Successo
- La domanda appare su Telegram come notifica
- L'utente può rispondere
- Il tool riceve la risposta e la restituisce