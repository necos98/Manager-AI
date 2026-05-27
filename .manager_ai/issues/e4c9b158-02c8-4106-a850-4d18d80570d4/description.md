Frontend changes to support the pipeline system: multi-terminal per issue, pipeline management UI, pipeline progress view, and agent chat.

**1. Multi-terminal per issue:**
- Change terminal model: one issue can have multiple active terminals
- Terminal tabs per issue: each terminal shows agent name + step name as label
- "Start Pipeline" button on issue page (replaces or sits alongside "Run Issue")
- Pipeline selector dropdown (which pipeline to run)
- Opening a new terminal doesn't close existing ones

**2. Pipeline management UI:**
- New route: `/projects/$projectId/settings/pipelines`
- Pipeline list with create/edit/delete
- Pipeline editor: name, list of steps
- Step editor: select agent, configure terminal command
- Agent list with create/edit/delete
- Agent editor: name, system prompt (textarea), model (dropdown), allowed tools (checkboxes from available MCP tools)

**3. Pipeline execution view:**
- Pipeline progress bar on issue page when pipeline is running
- Shows all steps with status indicators (pending/running/completed/failed)
- Highlights current step
- Click on step → navigate to its terminal tab

**4. Agent chat viewer:**
- Read-only chat view showing messages from all agents in pipeline run
- Ordered chronologically, grouped by agent
- Update in real-time via WebSocket events

**Components to build:**
- `PipelineEditor` — pipeline CRUD form
- `AgentEditor` — agent CRUD form
- `PipelineProgress` — step status indicator
- `PipelineRunChat` — inter-agent message viewer
- `TerminalTabs` — multi-terminal switcher (refactor from single terminal)
- `PipelineSelector` — dropdown to pick pipeline before starting

**API endpoints to call (from Issues #2 and #4):**
- CRUD agents/pipelines
- Start pipeline
- Get pipeline run status
- Get pipeline messages