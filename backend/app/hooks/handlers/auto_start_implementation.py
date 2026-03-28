from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService
from app.services.prompt_template_service import PromptTemplateService
from app.services.settings_service import SettingsService
from app.services.skill_library_service import SkillLibraryService


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
            paused = await SettingsService(session).get("work_queue_paused")

        if paused == "true":
            return HookResult(success=True, output="work queue is paused")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 900

        project_path = context.metadata.get("project_path", "")

        variables = {
            "issue_name": context.metadata.get("issue_name", ""),
            "project_name": context.metadata.get("project_name", ""),
            "project_description": context.metadata.get("project_description", ""),
            "tech_stack": context.metadata.get("tech_stack", ""),
            "issue_spec": context.metadata.get("specification", ""),
            "issue_plan": context.metadata.get("plan", ""),
            "skills_context": SkillLibraryService(None).get_skills_context(project_path),
        }

        async with async_session() as session:
            prompt = await PromptTemplateService(session).resolve(
                "implementation", context.project_id, variables
            )

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
