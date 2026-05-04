# Add Playwright MCP to Health Panel

## Goal

Add a fourth health check row for Playwright MCP with one-click install via terminal PTY, mirroring the existing Manager AI MCP pattern exactly.

## Design

### Backend

**`_check_playwright_mcp(project)` helper** — reads `.mcp.json` then `~/.claude.json` for a `"Playwright"` entry in `mcpServers`. Returns `{"installed": bool, "location": str|None}`. Same logic as `_check_mcp` but keying on `"Playwright"`.

**Health response** — add `playwright_mcp` field alongside existing `manager_json`, `claude_resources`, `mcp`.

**`POST /{project_id}/install-playwright-mcp`** — spawns terminal via `terminal_service.create()`, writes idempotent command (remove then add):
- Windows: `claude mcp remove Playwright 2>nul & claude mcp add Playwright -- npx -y @playwright/mcp --browser chromium`
- WSL: same pattern as `install-mcp` (path translation + bash export)

Returns `TerminalResponse`.

### Frontend

**`ProjectHealth` type** — add `playwright_mcp: { installed: boolean; location: string | null }`.

**API** — `installPlaywrightMcp(projectId): Promise<Terminal>` posts to `/projects/{id}/install-playwright-mcp`.

**Hook** — `useInstallPlaywrightMcp(projectId)` mutation hook, same pattern as `useInstallMcp`.

**`health-panel.tsx`**:
- Fourth `StatusRow` for Playwright MCP with install/reinstall button
- Install button reuses installMcp pattern: spawns terminal, navigates to `/terminals`
- Reinstall button when already installed
- `allInstalled` includes `playwright_mcp.installed`
- `handleInstallAll` includes Playwright install step (after MCP, before terminal navigation)

## Install Command

```
claude mcp add Playwright -- npx -y @playwright/mcp --browser chromium
```

Not headless — user wants to see the browser.