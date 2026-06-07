## Plan: Remove lifecycle state transitions from 4 agent intents

No code changes. Only MCP `update_agent` calls to clean intent strings. DEFAULT_AGENTS in agent_service.py already clean — no code file changes needed.

### Task 1: Clean PlanWriter intent — remove `accept_issue`

**Agent:** PlanWriter (id: `4cf084f1-93ca-4d52-a024-a9ee9e2cc650`)

Remove: `", then call accept_issue to move the issue to Accepted so downstream agents can begin implementation."` from end of intent.

### Task 2: Clean Closer intent — remove `complete_issue`

**Agent:** Closer (id: `a8313dda-2d4a-4ba5-a0a2-1d737ff3768e`)

Remove step 5 entirely: `"5. **Close the issue**: Call complete_issue with the recap to mark the issue as Finished."`
Update opening line to remove lifecycle reference.

### Task 3: Clean Tester intent — remove `complete_issue`

**Agent:** Tester (id: `babd9554-883b-41b0-bc83-9f925956fc7a`)

Remove `"then call complete_issue to mark the issue as Finished."` from step 5.
Update opening line to remove lifecycle reference.

### Task 4: Clean CodeReviewer intent — remove `complete_issue` reference

**Agent:** CodeReviewer (id: `20327f22-a024-43a9-812b-2ce9e4f539bc`)

Remove: `"Do NOT call complete_issue unless you are the final pipeline step — if Tester or Closer runs after you, let them finish."`
