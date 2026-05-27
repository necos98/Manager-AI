REST API + frontend UI for managing agent and pipeline definitions.

**Backend:**
- **AgentService** with CRUD: create, update, delete, list (by project_id), get
- **AgentRouter** at `/api/projects/{project_id}/agents` with standard REST endpoints
- **PipelineService** with CRUD: create, update, delete, list, get
- **PipelineRouter** at `/api/projects/{project_id}/pipelines` with standard REST endpoints
- Pydantic schemas for all request/response models

**Frontend:**
- **Agent editor** page/component: list agents, create/edit form (name, system_prompt, model dropdown, allowed_tools multi-select)
- **Pipeline editor** page/component: list pipelines, create/edit form (name, drag-and-drop reorder of steps, add/remove steps, select agent per step, configure terminal_command per step)

**Edge cases:**
- Prevent deleting agent still referenced by pipeline steps
- Prevent deleting pipeline currently running
- Agent name unique per project
- Terminal command supports `$ISSUE_ID`, `$PIPELINE_RUN_ID`, `$STEP_ID` variable resolution