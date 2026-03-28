"""EnrichProjectContext hook: updates project context after a issue is completed."""

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook


@hook(event=HookEvent.ISSUE_COMPLETED)
class EnrichProjectContext(BaseHook):
    name = "enrich_project_context"
    description = "Arricchisce il contesto del progetto dopo il completamento di una issue"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        issue_name = context.metadata.get("issue_name", "")
        recap = context.metadata.get("recap", "")
        project_name = context.metadata.get("project_name", "")
        project_path = context.metadata.get("project_path", "")
        project_description = context.metadata.get("project_description", "")
        tech_stack = context.metadata.get("tech_stack", "")

        prompt = f"""La issue "{issue_name}" è stata appena completata nel progetto "{project_name}".

Recap della issue:
{recap}

Contesto attuale del progetto:
{project_description}
{tech_stack}

Il tuo compito:
1. Analizza il recap della issue appena completata
2. Determina se ci sono informazioni rilevanti che dovrebbero essere aggiunte al contesto del progetto (descrizione, tech stack)
3. Se sì, aggiorna il contesto usando i tool MCP disponibili (update_project_context)
4. Se non ci sono informazioni rilevanti da aggiungere, non fare nulla

Aggiorna SOLO se la issue ha introdotto cambiamenti strutturali significativi
(nuove tecnologie, nuovi pattern architetturali, nuove integrazioni).
Non aggiungere dettagli specifici di singole issue."""

        async with async_session() as session:
            from app.services.mcp_tool_description_service import McpToolDescriptionService
            tool_guidance = await McpToolDescriptionService(session).build_tool_guidance(
                context.project_id
            )

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={"MANAGER_AI_PROJECT_ID": context.project_id},
            tool_guidance=tool_guidance,
        )

        return HookResult(
            success=result.success,
            output=result.output,
            error=result.error,
        )
