## Files

- **Modify**: `backend/app/mcp/server.py:1110`

## Plan

### Task 1: Fix case mismatch in get_active_agent status comparison

- [ ] Change `"running"` to `"RUNNING"` on line 1110 of `backend/app/mcp/server.py`
- [ ] Verify no other lowercase `"running"` status comparisons exist in `server.py`
- [ ] Run backend tests: `cd backend && python -m pytest tests/ -x -q`
