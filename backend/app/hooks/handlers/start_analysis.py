from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.prompt_template_service import PromptTemplateService
from app.services.skill_library_service import SkillLibraryService


@hook(event=HookEvent.ISSUE_ANALYSIS_STARTED)
class StartAnalysis(BaseHook):
    name = "start_analysis"
    description = "Avvia Claude Code per scrivere spec, piano e task della issue"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session

        project_path = context.metadata.get("project_path", "")

        variables = {
            "issue_description": context.metadata.get("issue_description", ""),
            "project_name": context.metadata.get("project_name", ""),
            "project_description": context.metadata.get("project_description", ""),
            "tech_stack": context.metadata.get("tech_stack", ""),
            "skills_context": SkillLibraryService(None).get_skills_context(project_path),
        }

        async with async_session() as session:
            prompt = await PromptTemplateService(session).resolve(
                "workflow", context.project_id, variables
            )

        async with async_session() as session:
            from app.services.mcp_tool_description_service import McpToolDescriptionService
            tool_guidance = await McpToolDescriptionService(session).build_tool_guidance(
                context.project_id
            )

        executor = ClaudeCodeExecutor()
        result = await executor.run(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": context.project_id,
                "MANAGER_AI_ISSUE_ID": context.issue_id,
            },
            tool_guidance=tool_guidance,
        )
        return HookResult(success=result.success, output=result.output, error=result.error)
