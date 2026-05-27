# Implementation Plan: Frontend UI for Agent & Pipeline System

## Files Map

**Create:**
- `frontend/src/features/agents/components/AgentsTab.tsx` — Agent list table + CRUD dialogs
- `frontend/src/features/pipelines/components/PipelinesTab.tsx` — Pipeline cards + step builder
- `frontend/src/features/pipeline-runs/components/PipelineRunButton.tsx` — Pipeline selector + start
- `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx` — Step progress + terminal output
- `frontend/src/features/pipeline-runs/components/AgentChat.tsx` — Agent message thread
- `frontend/src/routes/projects/$projectId/agents.tsx` — Route page for /agents
- `frontend/src/routes/projects/$projectId/pipelines.tsx` — Route page for /pipelines

**Modify:**
- `frontend/src/shared/components/app-sidebar.tsx` — Add Agents + Pipelines nav links
- `frontend/src/features/issues/components/issue-actions.tsx` — Add PipelineRunButton
- `frontend/src/features/issues/components/issue-detail.tsx` — Add AgentChat tab
- `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` — Add PipelineProgress in right panel
- `frontend/src/shared/context/event-context.tsx` — Add pipeline event WS handlers

---

## Plan

### Task 1: AgentsTab Component

**Files:** Create `frontend/src/features/agents/components/AgentsTab.tsx`

Build a data table listing all agents for current project. Uses `useAgents` hook for query, `useCreateAgent`, `useUpdateAgent`, `useDeleteAgent`, `useSeedAgents` for mutations.

- Table columns: Name, Model, Allowed Tools (count badge)
- Row actions: Edit (opens dialog pre-filled with agent data), Delete (confirm dialog then calls delete mutation)
- Header: "Create Agent" button opens create dialog
- Dialog form: Name (Input, required), System Prompt (Textarea, required), Model (Input, optional), Allowed Tools (tag-style input, comma-separated, optional)
- Dialog validation: Name required (min 1 char), System Prompt required (min 1 char)
- Seed defaults button in empty state or header
- States: Loading (Skeleton rows), Empty ("No agents configured"), Error (failed to load message)

### Task 2: PipelinesTab Component

**Files:** Create `frontend/src/features/pipelines/components/PipelinesTab.tsx`

Build a card-based pipeline manager. Uses `usePipelines`, `useAgents` hooks for data, all pipeline/step mutations from hooks.

- Card list: each card shows pipeline name (inline editable via `useUpdatePipeline`) + step summary "Agent1 → Agent2 → ..."
- Click card to expand step builder panel
- Step builder: ordered list of steps, each step = Agent selector (dropdown from `useAgents` data) + Terminal Command (Input). Up/Down buttons for reorder. Remove step button.
- Add Step button at bottom
- Create pipeline: "New Pipeline" card at top, fill name and confirm
- Delete pipeline: trash icon on card, confirm dialog
- Seed defaults button
- States: Loading, Empty, Error

### Task 3: PipelineRunButton + IssueActions Integration

**Files:**
- Create `frontend/src/features/pipeline-runs/components/PipelineRunButton.tsx`
- Modify `frontend/src/features/issues/components/issue-actions.tsx`

PipelineRunButton renders a compact Select dropdown (pipeline picker) + Run button. Uses `usePipelines(projectId)` to list pipelines, `useStartPipelineRun` to start.

Add `<PipelineRunButton projectId={projectId} issueId={issue.id} />` to IssueActions button row, after "Run Issue" button.

- Dropdown: "Select pipeline..." placeholder, each option = pipeline name + step count
- Run button: Play icon, disabled if no pipeline selected or run in progress
- After start: button shows spinner, invalidates pipeline run queries
- Edge case: no agents → disabled + tooltip "Create an agent first"
- Edge case: no pipelines → disabled + tooltip "No pipelines configured"
- Edge case: run already active → disabled + "Pipeline already running"

### Task 4: PipelineProgress + Issue Page Integration

**Files:**
- Create `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx`
- Modify `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`

PipelineProgress shows live pipeline run status. Fetches active run via `usePipelineRuns(projectId, issueId)`. Listens to WebSocket events for real-time updates via `useEvents().subscribe()`.

- Step list: each step = agent_name + PipelineStepRunStatus badge (PENDING=gray muted, RUNNING=blue with pulse animation, COMPLETED=green with check, FAILED=red with X)
- Current step highlighted with bold text and animated pulse dot
- Click step to expand: shows TerminalPanel with `readOnly={true}` connected to that step's terminal
- Step terminal ID tracked via WS `agent_terminal_created` event (maps step_id → terminal_id)
- Cancel button: calls `useCancelPipelineRun`
- Completed state: all steps green, show total duration (finished_at - started_at)
- Failed state: failed step highlighted red, error message if available

In `$issueId.tsx`: when pipelineRuns has an active RUNNING run, show PipelineProgress in a collapsible panel between action bar and content. Or replace terminal panel when no terminal is open.

### Task 5: AgentChat Component + IssueDetail Tab

**Files:**
- Create `frontend/src/features/pipeline-runs/components/AgentChat.tsx`
- Modify `frontend/src/features/issues/components/issue-detail.tsx`

AgentChat renders as a tab in IssueDetail. Shows when `usePipelineRuns(projectId, issueId)` returns at least one run.

- Run selector dropdown: choose which pipeline run's messages to view (default to most recent)
- Message list: scrollable, each message = sender agent name (bold, color-coded per agent) + timestamp (relative: "2m ago") + content rendered as markdown via `MarkdownViewer`
- Input: Textarea + Send button. Sends via `useSendPipelineMessage`
- Auto-refresh: `refetchInterval: 3000` on `usePipelineMessages` while selected run status === RUNNING
- States: No runs (tab hidden), Loading messages, Empty ("No messages yet"), Populated

In `issue-detail.tsx`: add tab definition for "Agent Chat" with availability based on `usePipelineRuns` data. Pass `projectId`, `issueId` as props.

### Task 6: Route Pages + Sidebar Navigation

**Files:**
- Create `frontend/src/routes/projects/$projectId/agents.tsx`
- Create `frontend/src/routes/projects/$projectId/pipelines.tsx`
- Modify `frontend/src/shared/components/app-sidebar.tsx`

Route pages are thin wrappers:
```tsx
// agents.tsx
import { createFileRoute } from "@tanstack/react-router";
import { AgentsTab } from "@/features/agents/components/AgentsTab";

export const Route = createFileRoute("/projects/$projectId/agents")({
  component: AgentsPage,
});

function AgentsPage() {
  const { projectId } = Route.useParams();
  return <AgentsTab projectId={projectId} />;
}
```

Same pattern for pipelines route.

Sidebar: add two items to `projectNav` array:
```tsx
{ label: "Agents", to: "/projects/$projectId/agents", params: { projectId }, icon: Bot },
{ label: "Pipelines", to: "/projects/$projectId/pipelines", params: { projectId }, icon: Workflow },
```

### Task 7: WebSocket Event Handlers

**Files:** Modify `frontend/src/shared/context/event-context.tsx`

Add handler cases in the `ws.onmessage` callback and `buildToastContent` function for pipeline-related events:

- `agent_step_started` — silent update, invalidate `pipelineRunKeys.all`
- `agent_step_completed` — silent update, invalidate `pipelineRunKeys.all`
- `agent_step_failed` — toast error with agent name, invalidate `pipelineRunKeys.all`
- `pipeline_completed` — toast success "Pipeline completed", invalidate `pipelineRunKeys.all`
- `agent_terminal_created` — silent update, invalidate `pipelineRunKeys.all`

For `buildToastContent`:
- `agent_step_failed` → variant "error", title "Step Failed", message with agent_name
- `pipeline_completed` → variant "success", title "Pipeline Completed"
- `agent_step_started`, `agent_step_completed`, `agent_terminal_created` → silent (no toast)
