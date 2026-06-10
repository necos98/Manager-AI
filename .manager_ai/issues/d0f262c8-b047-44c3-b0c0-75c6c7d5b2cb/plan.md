# Piano: Rimuovere fallback Hermes CLI da NotificationService

## Task 1: NotificationService — rimuovere Hermes CLI e semplificare
Modificare `backend/app/services/notification_service.py`:
1. Rimuovere import `HermesProvider` (riga 15)
2. Rimuovere metodo `_run_hermes_command()` (righe 168-204) — l'intero metodo statico
3. Rimuovere `await self._run_hermes_command(hermes_message)` da `_notify_issue_finished` (riga 131)
4. Rimuovere `await self._run_hermes_command(hermes_message)` da `_notify_question_asked` (riga 166)
5. Semplificare il formato di log: rimuovere il campo `| Comando: %(command)s` da `_NOTIFICATION_LOG_FORMAT` e `"command": hermes_cmd` dagli `extra`
6. Rimuovere la variabile `hermes_cmd` in entrambi i metodi _notify_*
7. Aggiornare docstring della classe e del modulo

## Task 2: HermesProvider — rimuovere build_notification_command
Modificare `backend/app/providers/hermes_provider.py`:
1. Rimuovere il metodo `build_notification_command()` (righe 63-71)
2. Aggiornare la docstring della classe se menziona notification

## Verifica
- Import test: `python -c "from app.services.notification_service import NotificationService"`
- Import test: `python -c "from app.providers.hermes_provider import HermesProvider; h = HermesProvider(); assert not hasattr(h, 'build_notification_command')"`
- Syntax check: `python -c "import ast; ast.parse(open('backend/app/services/notification_service.py').read()); ast.parse(open('backend/app/providers/hermes_provider.py').read())"`
