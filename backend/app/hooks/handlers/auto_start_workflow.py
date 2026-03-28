"""AutoStartWorkflow hook: when an issue is created and auto_workflow_enabled is true for
   the project, spawns Claude Code to write spec, plan, and tasks automatically."""
from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService
from app.services.settings_service import SettingsService


@hook(event=HookEvent.ISSUE_CREATED)
class AutoStartWorkflow(BaseHook):
    name = "auto_start_workflow"
    description = "Avvia automaticamente spec+piano+task quando viene creata una issue"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        async with async_session() as session:
            svc = ProjectSettingService(session)
            enabled = await svc.get(context.project_id, "auto_workflow_enabled", default="false")
            if enabled != "true":
                return HookResult(success=True, output="auto_workflow disabled for this project")
            custom_prompt = await svc.get(context.project_id, "auto_workflow_prompt", default="")
            timeout_str = await svc.get(context.project_id, "auto_workflow_timeout", default="600")
            # Check global work queue pause
            paused = await SettingsService(session).get("work_queue_paused")
        if paused == "true":
            return HookResult(success=True, output="work queue is paused")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 600

        issue_description = context.metadata.get("issue_description", "")
        project_name = context.metadata.get("project_name", "")
        project_path = context.metadata.get("project_path", "")
        project_description = context.metadata.get("project_description", "")
        tech_stack = context.metadata.get("tech_stack", "")

        if custom_prompt:
            prompt = (
                custom_prompt
                .replace("{{issue_description}}", issue_description)
                .replace("{{project_name}}", project_name)
                .replace("{{project_description}}", project_description)
                .replace("{{tech_stack}}", tech_stack)
            )
        else:
            prompt = f"""Sei il project manager di "{project_name}".

È stata creata una nuova issue con questa descrizione:
{issue_description}

Contesto del progetto:
{project_description}
Tech stack: {tech_stack}

Il tuo compito:
1. Usa `create_issue_spec` per scrivere una specifica tecnica dettagliata
2. Usa `create_issue_plan` per scrivere un piano di implementazione step-by-step
3. Usa `create_plan_tasks` per creare i task atomici del piano
4. Usa `send_notification` per notificare l'utente che il piano è pronto per la review

L'issue_id è nel contesto MCP (env MANAGER_AI_ISSUE_ID).
Lavora in sequenza, non saltare passi."""

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
