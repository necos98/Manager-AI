# Pipeline Full-Lifecycle — Implementation Plan

> **Goal:** Add SpecWriter agent, make pipeline startable from any issue state, and add Start Pipeline button in UI.

> **Architecture:** Extend OrchestratorService with intelligent step-skipping based on issue state. Add 5th default agent (SpecWriter). Update default pipeline to 5 steps. Add frontend button with duplicate-prevention via pipeline status check.

---

## Task 1: Add SpecWriter to default agents + update default pipeline

**Files:**
- Modify: `backend/app/services/orchestrator_service.py`

Add SpecWriter to `DEFAULT_AGENTS`:

```python
{
    "name": "SpecWriter",
    "role_key": "spec_writer",
    "system_prompt": (
        "You are a Technical Specification Writer. Your job is to analyze issue requirements "
        "and produce a clear, detailed specification and implementation plan.\n\n"
        "## Workflow\n"
        "1. Read the issue description carefully\n"
        "2. Call `create_issue_spec` to write the specification (moves issue NEW → REASONING)\n"
        "3. Call `create_issue_plan` to write the implementation plan (moves REASONING → PLANNED)\n"
        "4. Call `create_plan_tasks` to break the plan into atomic tasks\n"
        "5. Call `send_agent_message` with type='decision' summarizing key architectural choices\n"
        "6. Call `complete_agent_step` with a summary of what you produced\n\n"
        "## Guidelines\n"
        "- Specs should be detailed, covering architecture, data flow, edge cases\n"
        "- Plans should be actionable with specific files, functions, and patterns\n"
        "- Tasks should be atomic (1-2 files each) and ordered by dependency\n"
        "- Communicate decisions to the next agents via send_agent_message"
    ),
},
```

Update role_order in `ensure_default_pipeline()`:

```python
role_order = ["spec_writer", "architect", "developer", "reviewer", "qa"]
```

---

## Task 2: Enable start_pipeline from any issue state

**Files:**
- Modify: `backend/app/services/orchestrator_service.py`
- Modify: `backend/app/mcp/server.py` (if needed)

Add `_get_starting_step_index()` method to OrchestratorService:

```python
def _get_starting_step_index(self, issue: Issue, steps: list[dict]) -> int:
    """Determine which step to start from based on issue state.
    
    - NEW: start from spec_writer (index 0)
    - REASONING: skip spec_writer, start from architect
    - PLANNED/ACCEPTED: skip spec_writer + architect, start from developer
    - If issue already has spec but state is still NEW, start from spec_writer
      (SpecWriter will see spec exists and move to plan)
    """
    role_order = ["spec_writer", "architect", "developer", "reviewer", "qa"]
    
    if issue.status in ("Planned", "Accepted"):
        return 2  # start from developer
    elif issue.status == "Reasoning":
        return 1  # start from architect
    else:  # NEW or anything else
        return 0  # start from spec_writer
```

Modify `start_pipeline()`:
- Remove check that requires issue_id (keep it but don't enforce status)
- Call `_get_starting_step_index` and only create AgentStepRuns for steps >= start_index
- Only set pipeline status RUNNING if there are steps to execute

Modify `_build_prompt()`:
- Pass the `starting_step_index` context so each agent knows what's expected
- For SpecWriter: include instructions about current issue state

Remove MCP tool restriction in server.py for start_pipeline (remove any `issue.status == ACCEPTED` check).

---

## Task 3: Prevent duplicate pipeline runs

**Files:**
- Modify: `backend/app/services/orchestrator_service.py`

Add check in `start_pipeline()`:

```python
# Check for existing running pipeline
existing = await self.session.execute(
    select(PipelineRun).where(
        PipelineRun.issue_id == issue_id,
        PipelineRun.status == PipelineRunStatus.RUNNING,
    )
)
if existing.scalar_one_or_none() is not None:
    logger.info("Pipeline already running for issue %s", issue_id)
    return None  # Or raise a specific error
```

Return appropriate message so frontend can show "Pipeline already running".

---

## Task 4: Add Start Pipeline button to frontend

**Files:**
- Modify: `frontend/src/features/issues/components/issue-actions.tsx`
- Modify/Create: `frontend/src/features/agents/hooks.ts` (add `useStartPipeline`)
- Modify/Create: `frontend/src/features/agents/api.ts` (add `startPipeline` function)

Add API function in `api.ts`:

```typescript
export async function startPipeline(projectId: string, issueId: string) {
  const res = await api.post(`/projects/${projectId}/issues/${issueId}/start-pipeline`);
  return res.data;
}
```

Add hook in `hooks.ts`:

```typescript
export function useStartPipeline(projectId: string, issueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => startPipeline(projectId, issueId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "issues", issueId, "pipeline-runs"] });
    },
  });
}
```

Add button in `issue-actions.tsx`:

```tsx
import { GitBranch } from "lucide-react";
import { useStartPipeline, usePipelineRunsForIssue } from "@/features/agents/hooks";

// Inside IssueActions component:
const startPipeline = useStartPipeline(projectId, issue.id);
const { data: pipelineRuns } = usePipelineRunsForIssue(projectId, issue.id);
const hasRunningPipeline = (pipelineRuns?.runs ?? []).some(r => r.status === "running");

const handleStartPipeline = () => {
  startPipeline.mutate();
};

// Button (visible for non-terminal states):
{!isTerminalState && (
  <Button
    size="sm"
    variant="outline"
    onClick={handleStartPipeline}
    disabled={isPending || startPipeline.isPending || hasRunningPipeline}
    aria-label="Start agent pipeline"
  >
    <GitBranch className="size-4 mr-1" />
    {startPipeline.isPending ? "Starting..." : hasRunningPipeline ? "Pipeline Running" : "Start Pipeline"}
  </Button>
)}
```

Also update backend router to add endpoint if not already present:
`POST /api/projects/{project_id}/issues/{issue_id}/start-pipeline`

---

## Task 5: Clean up orphaned migration file

**Files:**
- Delete or fix: `backend/alembic/versions/6fbb705de97e_add_agents_and_pipelines.py`

The old migration has empty `upgrade()`. Since a new correct migration was already created (`3ed109d6a415`), delete the orphaned broken one to avoid confusion.

---

## Task 6: Testing

**File:** Modify `backend/tests/test_orchestrator.py`

New/updated tests:
1. `test_ensure_default_agents_creates_5` — verify SpecWriter exists
2. `test_default_pipeline_has_5_steps` — verify correct role order
3. `test_start_pipeline_from_new_state` — issue NEW, verify step_run for spec_writer created
4. `test_start_pipeline_from_reasoning_state` — issue REASONING, verify spec_writer skipped
5. `test_start_pipeline_from_planned_state` — issue PLANNED, verify first 2 roles skipped
6. `test_start_pipeline_duplicate_prevented` — second start returns error while one running
7. `test_spec_writer_system_prompt` — verify prompt includes create_issue_spec/plan instructions

Run: `cd backend && python -m pytest tests/test_orchestrator.py -v`
