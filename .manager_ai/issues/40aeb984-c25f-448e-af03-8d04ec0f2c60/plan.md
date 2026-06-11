## Workflow Validation Implementation Plan

**Goal:** Cycle test issue through all states (New → Reasoning → Planned → Accepted → Finished) to validate the MCP tools and state machine.

**Architecture:** Zero code changes. Pure MCP tool orchestration.

**Tech Stack:** Manager AI MCP tools (create_issue_spec, create_issue_plan, create_plan_tasks, accept_issue, complete_issue)

---

### Task 1: Complete Workflow Cycle

- [ ] **Write spec** [DONE]
- [ ] **Write plan** [DONE]
- [ ] **Create atomic tasks**
- [ ] **Accept plan** (auto-accept per run-issue rules)
- [ ] **Complete issue** with recap
