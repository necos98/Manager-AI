from __future__ import annotations

from app.hooks.executor import ClaudeCodeExecutor
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.project_setting_service import ProjectSettingService
from app.services.prompt_template_service import PromptTemplateService
from app.services.settings_service import SettingsService
from app.services.skill_library_service import SkillLibraryService


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
            legacy_prompt = await svc.get(context.project_id, "auto_workflow_prompt", default="")
            timeout_str = await svc.get(context.project_id, "auto_workflow_timeout", default="600")
            paused = await SettingsService(session).get("work_queue_paused")

        if paused == "true":
            return HookResult(success=True, output="work queue is paused")

        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 600

        project_path = context.metadata.get("project_path", "")

        variables = {
            "issue_description": context.metadata.get("issue_description", ""),
            "project_name": context.metadata.get("project_name", ""),
            "project_description": context.metadata.get("project_description", ""),
            "tech_stack": context.metadata.get("tech_stack", ""),
            "skills_context": SkillLibraryService(None).get_skills_context(project_path),
        }

        # Legacy override takes priority over DB templates for backwards compatibility
        if legacy_prompt:
            prompt = legacy_prompt
            for key, value in variables.items():
                prompt = prompt.replace(f"{{{{{key}}}}}", value)
        else:
            async with async_session() as session:
                prompt = await PromptTemplateService(session).resolve(
                    "workflow", context.project_id, variables
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
