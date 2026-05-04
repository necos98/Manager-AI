## What was implemented

Added Playwright MCP to the health panel as a 4th status check, mirroring the existing Manager AI MCP pattern.

### Backend (`backend/app/routers/projects.py`)
- Added `_check_playwright_mcp(project)` helper — reads `.mcp.json` and `~/.claude.json` for `"Playwright"` entry, returns `{installed, location}`
- Added `playwright_mcp` field to `GET /{id}/health` response
- Added `POST /{id}/install-playwright-mcp` endpoint — spawns terminal, writes idempotent `claude mcp add Playwright -- npx -y @playwright/mcp --browser chromium` command, supports WSL

### Frontend
- Updated `ProjectHealth` type with `playwright_mcp` field (`api.ts`)
- Added `installPlaywrightMcp()` API function (`api.ts`)
- Added `useInstallPlaywrightMcp()` React Query hook (`hooks.ts`)
- Added 4th `StatusRow` with install/reinstall button (`health-panel.tsx`)
- Updated `allInstalled` check and `handleInstallAll` flow to include Playwright MCP

### Install command
```
claude mcp add Playwright -- npx -y @playwright/mcp --browser chromium
```
Not headless — user sees the browser.