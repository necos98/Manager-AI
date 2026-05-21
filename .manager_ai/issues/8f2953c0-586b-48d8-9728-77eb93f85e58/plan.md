# Pipeline Manual Start — Implementation Plan

**Goal:** Remove pipeline auto-start from MCP `accept_issue` so pipeline only starts when user clicks "Start Pipeline" button.

**Architecture:** Single-file backend change. Remove the try/except block in `accept_issue` MCP tool that calls `OrchestratorService.start_pipeline()`. The manual REST endpoint (`POST /{issue_id}/start-pipeline`) and frontend "Start Pipeline" button already work. Update the test that asserts auto-start behavior.

**Tech Stack:** Python FastAPI + pytest

## Task Breakdown

### Task 1: Update test to expect no auto-start
Update `test_mcp_tools.py` — change `test_accept_issue_auto_starts_pipeline` to verify pipeline does NOT auto-start on accept.

### Task 2: Remove auto-start from MCP accept_issue
Remove lines 297-314 from `backend/app/mcp/server.py` (the try/except block calling `orchestrator.start_pipeline`). Return directly after event emission.

### Task 3: Run tests to verify
Run MCP test suite, confirm all tests pass.