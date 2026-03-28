"""AutoCompletion hook: when all tasks are completed, notify user or auto-complete the issue
   depending on the project's auto_complete_mode setting (off/notify/auto)."""
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.event_service import event_service
from app.services.project_setting_service import ProjectSettingService


@hook(event=HookEvent.ALL_TASKS_COMPLETED)
class AutoCompletion(BaseHook):
    name = "auto_completion"
    description = "Notifica o completa automaticamente l'issue quando tutti i task sono completati"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            mode = await svc.get(context.project_id, "auto_complete_mode", default="off")

        if mode == "off":
            return HookResult(success=True, output="auto_complete_mode is off")

        issue_name = context.metadata.get("issue_name", "")
        project_path = context.metadata.get("project_path", "")

        if mode == "notify":
            await event_service.emit({
                "type": "notification",
                "project_id": context.project_id,
                "issue_id": context.issue_id,
                "title": "Tutti i task completati",
                "message": (
                    f'Issue "{issue_name}" ha tutti i task completati. '
                    "Puoi ora completare l'issue con un recap."
                ),
            })
            return HookResult(success=True, output="notification sent")

        if mode == "auto":
            prompt = f"""Tutti i task dell'issue "{issue_name}" sono stati completati.

Il tuo compito:
1. Usa `get_issue_details` per leggere il piano e i task completati
2. Usa `complete_issue` con un recap dettagliato che descrive cosa è stato implementato

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Il recap deve essere completo e basato sul piano effettivamente eseguito."""

            executor = ClaudeCodeExecutor()
            result = await executor.run(
                prompt=prompt,
                project_path=project_path,
                env_vars={
                    "MANAGER_AI_PROJECT_ID": context.project_id,
                    "MANAGER_AI_ISSUE_ID": context.issue_id,
                },
                timeout=120,
            )
            return HookResult(success=result.success, output=result.output, error=result.error)

        return HookResult(success=True, output=f"unknown mode: {mode}")
