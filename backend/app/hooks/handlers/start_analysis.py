"""StartAnalysis hook: spawns Claude Code to write spec, plan, and tasks for a new issue."""

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook


@hook(event=HookEvent.ISSUE_ANALYSIS_STARTED)
class StartAnalysis(BaseHook):
    name = "start_analysis"
    description = "Avvia Claude Code per scrivere spec, piano e task della issue"

    async def execute(self, context: HookContext) -> HookResult:
        issue_description = context.metadata.get("issue_description", "")
        project_name = context.metadata.get("project_name", "")
        project_path = context.metadata.get("project_path", "")
        project_description = context.metadata.get("project_description", "")
        tech_stack = context.metadata.get("tech_stack", "")

        prompt = f"""Sei il project manager di "{project_name}".

È stata creata una nuova issue con questa descrizione:
{issue_description}

Contesto del progetto:
{project_description}
Tech stack: {tech_stack}

Il tuo compito:
1. Usa `create_issue_spec` per scrivere una specifica tecnica dettagliata basata sulla descrizione
2. Usa `create_issue_plan` per scrivere un piano di implementazione step-by-step
3. Usa `create_plan_tasks` per creare i task atomici del piano (usa replace=true)
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
        )

        return HookResult(
            success=result.success,
            output=result.output,
            error=result.error,
        )
