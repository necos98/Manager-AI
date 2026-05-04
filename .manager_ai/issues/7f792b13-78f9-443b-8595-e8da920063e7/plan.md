# Implementation Plan: Add Playwright MCP to Health Panel

## Files

| Action | Path |
|--------|------|
| Modify | `backend/app/routers/projects.py` |
| Modify | `frontend/src/features/projects/api.ts` |
| Modify | `frontend/src/features/projects/hooks.ts` |
| Modify | `frontend/src/features/projects/components/health-panel.tsx` |

---

## Task 1: Backend — `_check_playwright_mcp` helper + health endpoint update

**File:** `backend/app/routers/projects.py`

### Step 1: Add `_check_playwright_mcp` helper (after `_check_mcp`, around line 79)

```python
def _check_playwright_mcp(project) -> dict:
    project_mcp = os.path.join(project.path, ".mcp.json")
    if os.path.isfile(project_mcp):
        try:
            with open(project_mcp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "Playwright" in (data.get("mcpServers") or {}):
                return {"installed": True, "location": project_mcp}
        except Exception:
            pass

    home_cfg = os.path.join(os.path.expanduser("~"), ".claude.json")
    if os.path.isfile(home_cfg):
        try:
            with open(home_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "Playwright" in (data.get("mcpServers") or {}):
                return {"installed": True, "location": home_cfg}
            norm = os.path.normpath(project.path).lower()
            for key, val in (data.get("projects") or {}).items():
                if os.path.normpath(key).lower() == norm and "Playwright" in (val.get("mcpServers") or {}):
                    return {"installed": True, "location": home_cfg}
        except Exception:
            pass
    return {"installed": False, "location": None}
```

### Step 2: Add `playwright_mcp` to health response (line 210-214)

Change:
```python
    return {
        "manager_json": _check_manager_json(project),
        "claude_resources": _check_claude_resources(project),
        "mcp": _check_mcp(project),
    }
```

To:
```python
    return {
        "manager_json": _check_manager_json(project),
        "claude_resources": _check_claude_resources(project),
        "mcp": _check_mcp(project),
        "playwright_mcp": _check_playwright_mcp(project),
    }
```

---

## Task 2: Backend — `POST /{project_id}/install-playwright-mcp` endpoint

**File:** `backend/app/routers/projects.py`

Add after `install_mcp` endpoint (after line 266):

```python
@router.post("/{project_id}/install-playwright-mcp", response_model=TerminalResponse, status_code=201)
async def install_playwright_mcp(project_id: str, db: AsyncSession = Depends(get_db)):
    """Spawn a terminal and register the Playwright MCP server.

    Idempotent: runs `claude mcp remove Playwright` before `claude mcp add`
    so the caller can use this as both "install" and "reinstall".
    """
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if not os.path.isdir(project.path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project.path}")

    try:
        terminal = terminal_service.create(
            issue_id="",
            project_id=project_id,
            project_path=project.path,
            shell=project.shell,
            wsl_distro=project.wsl_distro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    is_wsl = is_wsl_shell(project.shell)

    try:
        pty = terminal_service.get_pty(terminal["id"])
        if is_wsl:
            cwd = win_to_wsl_path(project.path)
            pty.write(f"cd {shlex.quote(cwd)}\r\n")
            pty.write(
                "claude mcp remove Playwright 2>/dev/null; "
                "claude mcp add Playwright -- npx -y @playwright/mcp --browser chromium\r\n"
            )
        else:
            pty.write(
                "claude mcp remove Playwright 2>nul & "
                "claude mcp add Playwright -- npx -y @playwright/mcp --browser chromium\r\n"
            )
    except Exception:
        logger.warning("Failed to write install-playwright-mcp command for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)
```

---

## Task 3: Frontend — Type and API updates

**File:** `frontend/src/features/projects/api.ts`

### Step 1: Update `ProjectHealth` type

Add `playwright_mcp` field:
```typescript
export interface ProjectHealth {
  manager_json: { installed: boolean; path: string };
  claude_resources: { installed: boolean; path: string; missing: string[] };
  mcp: { installed: boolean; location: string | null };
  playwright_mcp: { installed: boolean; location: string | null };
}
```

### Step 2: Add `installPlaywrightMcp` API function (after `installMcp`)

```typescript
export function installPlaywrightMcp(projectId: string): Promise<Terminal> {
  return apiPost<Terminal>(`/projects/${projectId}/install-playwright-mcp`);
}
```

---

## Task 4: Frontend — React Query hook

**File:** `frontend/src/features/projects/hooks.ts`

Add after `useInstallMcp` (after line 78):

```typescript
export function useInstallPlaywrightMcp(projectId: string) {
  return useMutation({
    mutationFn: () => api.installPlaywrightMcp(projectId),
    onError: onMutationError,
  });
}
```

---

## Task 5: Frontend — Health panel UI updates

**File:** `frontend/src/features/projects/components/health-panel.tsx`

### Step 1: Import new hook (line 12)

Add `useInstallPlaywrightMcp` to the import:
```typescript
import {
  useProjectHealth,
  useInstallManagerJson,
  useInstallClaudeResources,
  useInstallMcp,
  useInstallPlaywrightMcp,
} from "@/features/projects/hooks";
```

### Step 2: Add hook and state in component (after line 53)

```typescript
const installPlaywrightMcp = useInstallPlaywrightMcp(projectId);
const [reinstallingPlaywright, setReinstallingPlaywright] = useState(false);
```

### Step 3: Add reinstall handler (after `handleReinstallMcp`)

```typescript
async function handleReinstallPlaywright() {
  if (reinstallingPlaywright) return;
  setReinstallingPlaywright(true);
  try {
    await installPlaywrightMcp.mutateAsync();
    toast.success("Terminal opened — Playwright MCP re-registration running");
    queryClient.invalidateQueries({ queryKey: terminalKeys.all });
    queryClient.invalidateQueries({ queryKey: terminalKeys.count });
    queryClient.invalidateQueries({ queryKey: ["projects", projectId, "health"] });
    navigate({ to: "/terminals" });
  } catch (e) {
    toast.error(e instanceof Error ? e.message : "Playwright MCP reinstall failed");
  } finally {
    setReinstallingPlaywright(false);
  }
}
```

### Step 4: Update `allInstalled` check

Change:
```typescript
const allInstalled =
  health.manager_json.installed && health.claude_resources.installed && health.mcp.installed;
```

To:
```typescript
const allInstalled =
  health.manager_json.installed && health.claude_resources.installed && health.mcp.installed && health.playwright_mcp.installed;
```

### Step 5: Update `handleInstallAll` (add Playwright step after MCP)

Add before the terminal navigation block inside the existing `if (!health.mcp.installed)` block, after it:
```typescript
if (!health.playwright_mcp.installed) {
  await installPlaywrightMcp.mutateAsync();
  toast.success("Terminal opened — Playwright MCP install running");
  queryClient.invalidateQueries({ queryKey: terminalKeys.all });
  queryClient.invalidateQueries({ queryKey: terminalKeys.count });
  queryClient.invalidateQueries({ queryKey: ["projects", projectId, "health"] });
  navigate({ to: "/terminals" });
  return;
}
```

Wait—if both MCP and Playwright need install, we'd navigate away after MCP. Better: install MCP first (it already navigates), then if only Playwright is missing, install it. Restructure the install-all flow:

```typescript
async function handleInstallAll() {
  if (!health || running) return;
  setRunning(true);
  try {
    if (!health.manager_json.installed) {
      await installManagerJson.mutateAsync();
    }
    await installClaudeResources.mutateAsync();
    if (!health.mcp.installed) {
      await installMcp.mutateAsync();
      toast.success("Terminal opened — run the MCP install command");
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
      navigate({ to: "/terminals" });
      return;
    }
    if (!health.playwright_mcp.installed) {
      await installPlaywrightMcp.mutateAsync();
      toast.success("Terminal opened — Playwright MCP install running");
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "health"] });
      navigate({ to: "/terminals" });
      return;
    }
    toast.success("Dependencies installed");
    queryClient.invalidateQueries({ queryKey: ["projects", projectId, "health"] });
  } catch (e) {
    toast.error(e instanceof Error ? e.message : "Install failed");
  } finally {
    setRunning(false);
  }
}
```

### Step 6: Add fourth StatusRow (before closing `</div>` of the status rows, after Claude Resources row)

```tsx
<StatusRow
  title="Playwright MCP"
  installed={health.playwright_mcp.installed}
  detail={health.playwright_mcp.location ?? undefined}
  action={
    <Button
      size="sm"
      variant="outline"
      onClick={handleReinstallPlaywright}
      disabled={reinstallingPlaywright || running}
    >
      {reinstallingPlaywright ? (
        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
      ) : (
        <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
      )}
      {reinstallingPlaywright
        ? "Reinstalling..."
        : health.playwright_mcp.installed
          ? "Reinstall"
          : "Install"}
    </Button>
  }
/>
```

---

## Execution Order

1. Task 1: Backend helper + health response
2. Task 2: Backend install endpoint
3. Task 3: Frontend types + API
4. Task 4: Frontend hook
5. Task 5: Frontend UI (status row, allInstalled, handleInstallAll)
6. Commit all changes