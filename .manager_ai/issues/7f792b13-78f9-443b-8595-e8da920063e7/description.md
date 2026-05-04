Add Playwright MCP to the health panel with one-click install via terminal PTY. Mirror the existing Manager AI MCP pattern: health check reads .mcp.json / ~/.claude.json for "Playwright" entry, install spawns terminal and runs `claude mcp add Playwright -- npx -y @playwright/mcp --browser chromium`. Not headless — user wants to see the browser.

Changes:
- Backend: `_check_playwright_mcp` helper, `playwright_mcp` in health response, `POST /{id}/install-playwright-mcp` endpoint
- Frontend: ProjectHealth type update, API function, React Query hook, fourth StatusRow in health-panel.tsx