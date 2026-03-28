"""AutoStartImplementation hook: when an issue is accepted and auto_implementation_enabled
   is true for the project, spawns Claude Code to implement the plan task by task."""
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService


@hook(event=HookEvent.ISSUE_ACCEPTED)
class AutoStartImplementation(BaseHook):
    name = "auto_start_implementation"
    description = "Avvia automaticamente l'implementazione quando una issue viene accettata"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            enabled = await svc.get(context.project_id, "auto_implementation_enabled", default="false")
            if enabled != "true":
                return HookResult(success=True, output="auto_implementation disabled for this project")
            timeout_str = await svc.get(context.project_id, "auto_implementation_timeout", default="900")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 900

        issue_name = context.metadata.get("issue_name", "")
        project_name = context.metadata.get("project_name", "")
        project_path = context.metadata.get("project_path", "")
        project_description = context.metadata.get("project_description", "")
        tech_stack = context.metadata.get("tech_stack", "")
        specification = context.metadata.get("specification", "")
        plan = context.metadata.get("plan", "")

        prompt = f"""Sei il developer assegnato all'issue "{issue_name}" nel progetto "{project_name}".

Contesto del progetto:
{project_description}
Tech stack: {tech_stack}

Specifica dell'issue:
{specification}

Piano di implementazione:
{plan}

Il tuo compito è implementare il piano passo per passo:
1. Usa `get_plan_tasks` per ottenere la lista dei task
2. Per ogni task, in ordine:
   a. Usa `update_task_status` per marcarlo "In Progress"
   b. Implementa il task nel codice del progetto
   c. Usa `update_task_status` per marcarlo "Completed"
3. Quando tutti i task sono completati, usa `complete_issue` con un recap dettagliato

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Lavora metodicamente. Non saltare task."""

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": context.project_id,
                "MANAGER_AI_ISSUE_ID": context.issue_id,
            },
            timeout=timeout,
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
