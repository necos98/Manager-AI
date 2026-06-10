---
id: e4cdfe90-ef5c-4dbf-adbf-21936a871ac0
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: ask_user_question test completato — tutti i casi funzionanti
parent_id: null
created_at: '2026-06-09T17:03:07.949818+00:00'
updated_at: '2026-06-09T21:46:08.384608+00:00'
links: []
---
Test manuale di ask_user_question completato con successo il 2026-06-09. Tre scenari verificati: (1) con options=[Python,TypeScript,Go,Rust] → answer=Python, selected_option=Python; (2) senza options → answer=manager ai, selected_option=null; (3) timeout con timeout_seconds=5 → timed_out=true.

Test notifica Telegram completato con successo il 2026-06-09 (issue 5c4bc9e6). ask_user_question invocato con domanda di test e options=[Python,TypeScript,Go,Rust]. Risposta ricevuta: "ricevuta" (risposta libera). Timeout 300s non scaduto. La notifica Telegram per le domande FUNZIONA — l'utente ha ricevuto la domanda su Telegram e ha potuto rispondere.

Il flusso: MCP tool crea question + asyncio.Event, blocca in attesa, risposta via Telegram o REST API/UI risolve l'evento e il tool restituisce il risultato. TelegramNotifier (TelegramService) invia la notifica quando Telegram è configurato. NotificationService salta l'invio se TelegramService.is_configured() è True. FK issue_id è stata rimossa dalla tabella questions (migrazione ea6dc15a673c) perché le issues sono file-backed.