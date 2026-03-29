import os
import platform
import tempfile

from app.hooks.registry import BaseHook, HookContext, HookEvent, HookResult, hook
from app.services.prompt_template_service import PromptTemplateService
from app.services.skill_library_service import SkillLibraryService


@hook(event=HookEvent.ISSUE_ANALYSIS_STARTED)
class StartAnalysis(BaseHook):
    name = "start_analysis"
    description = "Start Claude Code to write spec, plan and tasks for the issue"

    async def execute(self, context: HookContext) -> HookResult:
        from app.database import async_session
        from app.services.event_service import event_service
        from app.services.terminal_service import terminal_service

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

        full_prompt = (tool_guidance + "\n\n" + prompt) if tool_guidance else prompt

        # Write prompt to a temp file so we can redirect it into the PTY shell
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(full_prompt)
            prompt_file = f.name

        # Create a terminal session tied to this issue
        terminal = terminal_service.create(
            issue_id=context.issue_id,
            project_id=context.project_id,
            project_path=project_path,
        )
        terminal_id = terminal["id"]
        pty = terminal_service.get_pty(terminal_id)

        # Inject required env vars
        is_windows = platform.system() == "Windows"
        set_cmd = "set" if is_windows else "export"
        env_vars = {
            "MANAGER_AI_PROJECT_ID": context.project_id,
            "MANAGER_AI_ISSUE_ID": context.issue_id,
            "MANAGER_AI_BASE_URL": os.environ.get("MANAGER_AI_BASE_URL", "http://localhost:8000"),
        }
        env_line = " && ".join(f'{set_cmd} {k}={v}' for k, v in env_vars.items())
        pty.write(env_line + "\r\n")

        # Run claude with the prompt piped from the temp file
        prompt_file_escaped = prompt_file.replace("\\", "\\\\") if not is_windows else prompt_file
        cmd = f'claude --allowedTools mcp__ManagerAi__* < "{prompt_file_escaped}"\r\n'
        pty.write(cmd)

        # Notify frontend so it refreshes the terminal list
        await event_service.emit({
            "type": "terminal_created",
            "terminal_id": terminal_id,
            "issue_id": context.issue_id,
            "project_id": context.project_id,
            "issue_name": context.metadata.get("issue_name", ""),
        })

        return HookResult(success=True, output=terminal_id)
