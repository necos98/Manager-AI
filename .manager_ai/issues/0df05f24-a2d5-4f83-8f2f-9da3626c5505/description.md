Arricchire le notifiche Telegram inviate da NotificationService via `hermes chat -q`.

**Stato attuale:** la notifica dice solo "Issue {name} completata" — mancano informazioni fondamentali.

**Requisiti:**
La notifica deve includere:
1. ✅ **Nome del progetto** (es. "Manager AI")
2. ✅ **Nome dell'issue**
3. ✅ **Descrizione** (primi 120 caratteri)
4. ✅ **Recap** (se presente, primi 120 caratteri)

**Modifiche necessarie:**

1. **`backend/app/mcp/shared_tools.py`** — aggiungere `project_name`, `description`, `recap` agli eventi:
   - `force_finish_issue`: aggiungere ProjectService lookup per ottenere `project_name`, aggiungere campi all'evento `issue_status_changed`
   - `complete_issue`: stessa cosa
   - `ask_user_question`: aggiungere `project_name` all'evento `question_asked` (spostare ProjectService lookup prima dell'emit)

2. **`backend/app/services/notification_service.py`** — aggiornare i metodi di notifica:
   - `_notify_issue_finished()`: formattare messaggio con progetto, issue, descrizione e recap
   - `_notify_question_asked()`: formattare messaggio con progetto, issue e domanda

**Formato notifica issue completata:**
```
✅ Issue completata — Nome Progetto
📌 Nome dell'Issue
📝 Descrizione breve...
💬 Recap: riepilogo...
```

**Formato notifica domanda:**
```
❓ Domanda in attesa — Nome Progetto
📌 Nome dell'Issue
💬 Testo della domanda...
```

**Nota:** alcune modifiche sono già state parzialmente applicate ai file, ma potrebbero non essere state caricate correttamente. Verificare lo stato attuale dei file e applicare/riapplicare le modifiche se necessario.