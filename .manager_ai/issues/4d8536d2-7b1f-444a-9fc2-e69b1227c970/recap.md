## Recap

Implemented project linking with directional relationships across full stack:

**Backend:**
- `project_links` table: source_project_id → target_project_id with free-text description, unique constraint on pair, CASCADE deletes
- CRUD REST API at `/api/projects/{project_id}/links`
- Validation: no self-links, description required, duplicate pair rejected

**Frontend:**
- Types, API functions, React Query hooks
- "Linked Projects" section in ProjectSettingsDialog with direction indicators, add/edit/delete UI

**MCP:**
- `get_project_links` tool exposes links to Claude Code
- `CLAUDE.md` updated with Project Links section — instructs to check links before cross-project changes

**Key design decision:** Directional links. A→B ≠ B→A. Each direction has own description. User can see both incoming and outgoing links in the settings dialog. For incoming links, only view/delete is allowed (edit restricted to the source project owner).