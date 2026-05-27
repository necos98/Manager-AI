# Specification: Frontend UI for Agent & Pipeline System

## Overview

Build the complete frontend UI for the agent orchestration pipeline system. Backend routers, services, models, schemas are already implemented. Frontend API layer (`api.ts`) and hooks (`hooks.ts`) for agents, pipelines, and pipeline-runs are already written. Shared types in `shared/types/index.ts` are complete and match backend enum values exactly.

Missing: UI components, route pages, sidebar navigation, and issue page integration.

## Architecture

Follow the existing feature pattern established by terminals, memories, and activity features:

```
frontend/src/
  features/
    agents/
      components/
        AgentsTab.tsx          -- Agent list table + CRUD dialogs
    pipelines/
      components/
        PipelinesTab.tsx       -- Pipeline list cards + step builder
    pipeline-runs/
      components/
        PipelineRunButton.tsx  -- Pipeline selector + start button
        PipelineProgress.tsx   -- Step status list + readOnly terminal
        AgentChat.tsx          -- Agent message thread (issue tab)
  routes/
    projects/$projectId/
      agents.tsx               -- /projects/$projectId/agents
      pipelines.tsx            -- /projects/$projectId/pipelines
```

## Components

### AgentsTab
- **Renders**: Data table with columns: Name, Model, Allowed Tools (count badge)
- **Row actions**: Edit (opens dialog), Delete (confirm dialog, calls `useDeleteAgent`)
- **Header action**: "Create Agent" button opens create dialog
- **Create/Edit dialog**: Form with Name (text, required), System Prompt (textarea, required), Model (text, optional, default null), Allowed Tools (tag-style input, optional)
- **States**: Loading skeleton, empty state ("No agents. Seed defaults or create one."), error state
- **Seed button**: Calls `useSeedAgents` to populate default agents

### PipelinesTab
- **Renders**: Card list, one card per pipeline
- **Card shows**: Pipeline name (inline editable), step summary as "AgentName1 → AgentName2 → AgentName3"
- **Expand/card detail**: Step builder UI — ordered list of steps, each step = Agent dropdown selector + Terminal Command text input. Remove step button on each. Add Step button at bottom. Reorder via up/down buttons.
- **Actions**: Create pipeline (card with name input), Delete (confirm dialog)
- **States**: Loading skeleton, empty state ("No pipelines. Seed defaults or create one."), error state
- **Seed button**: Calls `useSeedPipeline`

### PipelineRunButton
- **Renders inside IssueActions**: Dropdown (Select pipeline...) + "Run" button
- **Pipeline list**: Fetched via `usePipelines(projectId)`
- **On run**: Calls `useStartPipelineRun` with `{ pipeline_id, issue_id }`. Disables button while running. Shows running pipeline status.
- **States**: No pipelines loaded (disabled), run in progress (disabled + spinner), error (toast already handled by hooks)

### PipelineProgress
- **Renders**: In terminal panel area of issue page, shared/alternating with terminal panel. When an active pipeline run exists for current issue, shows progress.
- **Step list**: Each step shows agent name + status badge (PENDING=gray, RUNNING=blue, COMPLETED=green, FAILED=red)
- **Active step highlighted**: Bold + pulsing indicator
- **Step output**: Click a step to see its terminal output. Uses `TerminalPanel` with `readOnly={true}`. Terminal ID comes from WebSocket `agent_terminal_created` event or from step run data.
- **Cancel button**: Calls `useCancelPipelineRun`
- **Real-time updates**: WebSocket subscriber listens for `agent_step_started`, `agent_step_completed`, `agent_step_failed`, `pipeline_completed` events and invalidates `pipelineRunKeys`
- **States**: No active run (hidden), run running (live progress), run completed (summary view, steps all green + duration), run failed (summary view, failed step highlighted)

### AgentChat
- **Renders**: As a NEW TAB on the issue detail page (alongside Description, Specification, Plan, Tasks, Relations, Recap)
- **Tab availability**: Only visible when the issue has at least one pipeline run (active or completed)
- **Run selector**: Dropdown at top of tab to select which pipeline run's messages to view
- **Message display**: Scrollable list, each message = sender name (bold) + timestamp + content (markdown via MarkdownViewer)
- **Input**: Text input + Send button at bottom. Sends via `useSendPipelineMessage`. User types as a human observer joining the agent conversation.
- **Auto-refresh**: Poll every 3s via `refetchInterval` on `usePipelineMessages` while selected run is active
- **States**: No runs available (tab hidden), no messages (empty state), loading, populated

## Routes

### `/projects/$projectId/agents`
- File: `routes/projects/$projectId/agents.tsx`
- Renders `AgentsTab` with projectId from route params
- Page title: "Agents — {Project Name}"

### `/projects/$projectId/pipelines`
- File: `routes/projects/$projectId/pipelines.tsx`
- Renders `PipelinesTab` with projectId from route params
- Page title: "Pipelines — {Project Name}"

### Sidebar Navigation
- Add two items to `projectNav` in `AppSidebar`:
  - "Agents" — icon: Bot (from lucide-react) — to: `/projects/$projectId/agents`
  - "Pipelines" — icon: Workflow (from lucide-react) — to: `/projects/$projectId/pipelines`

## Issue Page Integration

### PipelineRunButton in IssueActions
- Add `PipelineRunButton` as child of `IssueActions` component
- Pass `projectId` and `issueId` as props

### PipelineProgress in Issue Detail Page
- In `$issueId.tsx`, PipelineProgress shares the right panel area with the terminal
- Logic: If active pipeline run exists → show PipelineProgress toggle. Terminal can still be opened separately.
- `PipelineProgress` receives `projectId`, `issueId`, and the active `runId` as props

### AgentChat Tab in Issue Detail
- New tab "Agent Chat" added to `IssueDetail` component's tab list
- Available when issue has pipeline runs (check via `usePipelineRuns(projectId, issueId)`)
- Tab content renders `AgentChat` component with `projectId`, `issueId`
- When no pipeline run is selected, shows run selector or prompt to start a run

## Data Flow

- **Queries**: Already built in feature hooks.ts. Components import and use them.
- **Mutations**: All CRUD in hooks.ts with React Query cache invalidation
- **WebSocket events**: Add event handlers in `event-context.tsx` for `agent_step_started`, `agent_step_completed`, `agent_step_failed`, `pipeline_completed`, `agent_terminal_created` — invalidate `pipelineRunKeys.all(projectId)`. PipelineProgress component also listens via `useEvents().subscribe()` for live updates without full query refetch.
- **Terminal output**: Step terminal IDs tracked in component state. PipelineProgress renders `TerminalPanel` with `readOnly={true}` and `terminalId` from the step run.

## Enum Values (from memory)

- `PipelineRunStatus`: RUNNING | COMPLETED | FAILED (UPPERCASE, no PENDING, no CANCELLED)
- `PipelineStepRunStatus`: PENDING | RUNNING | COMPLETED | FAILED (UPPERCASE)
- Frontend types in `shared/types/index.ts` match these exactly

## Error & Edge Cases

- **No agents**: Disable pipeline run if no agents exist. Show "Create an agent first" message.
- **No pipelines**: PipelineRunButton disabled. "No pipelines configured" tooltip.
- **Run already active**: Disable "Run" button. Show "A pipeline is already running" with link to view.
- **Delete agent used in pipeline**: Backend should handle this. Frontend: invalidate both agent and pipeline queries on agent delete.
- **Terminal output not available**: Show "Output not available" placeholder for steps that haven't started or whose terminal wasn't created.
- **Page not found**: If projectId is invalid, show error state from `useProject` hook.

## Testing Notes

- Manual verification: Navigate to /agents, /pipelines, create/edit/delete agents and pipelines
- Issue page: Start a pipeline run, observe progress, cancel, observe messages
- WebSocket events verified via browser DevTools Network WS tab
- Component states checked: loading, empty, error, populated
