# Smartphone QR Code Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Show on Smartphone" button to the sidebar that displays a QR code pointing to the app's local network URL so the user can open it on their phone.

**Architecture:** A new backend endpoint `/api/network-info` detects the PC's LAN IP using a UDP socket trick and returns it. The frontend fetches this IP, combines it with its own port (`window.location.port`), and renders a QR code in a dialog. The backend binding changes from `127.0.0.1` to `0.0.0.0` so the phone can actually reach it.

**Tech Stack:** Python `socket` (stdlib), FastAPI, `react-qr-code` (new npm dep), React, TanStack Query

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `start.py:129` | Change `--host 127.0.0.1` → `--host 0.0.0.0` |
| Create | `backend/app/routers/network.py` | GET `/api/network-info` → `{ local_ip }` |
| Modify | `backend/app/main.py` | Include network router |
| Create | `backend/tests/test_routers_network.py` | Test network-info endpoint |
| Create | `frontend/src/shared/components/smartphone-qr-dialog.tsx` | Dialog with QR code |
| Modify | `frontend/src/shared/components/app-sidebar.tsx` | Add "Show on Smartphone" button in footer |

---

### Task 1: Fix backend binding in start.py

**Files:**
- Modify: `start.py:129`

- [ ] **Step 1: Change host binding**

In `start.py`, find the uvicorn Popen call (around line 124-133) and change the host argument:

```python
# Before:
"--host", "127.0.0.1",

# After:
"--host", "0.0.0.0",
```

Also update the print statement at line 118 to show actual network access info:

```python
# Before:
print("  Frontend: http://localhost:4173")
print(f"  Backend:  http://localhost:{backend_port}")

# After:
print("  Frontend: http://localhost:4173  (also accessible on LAN)")
print(f"  Backend:  http://localhost:{backend_port}  (also accessible on LAN)")
```

- [ ] **Step 2: Verify the change is correct**

Run: `grep -n "127.0.0.1" start.py`
Expected: no output (the line should be gone)

- [ ] **Step 3: Commit**

```bash
git add start.py
git commit -m "fix: bind backend to 0.0.0.0 to allow LAN access"
```

---

### Task 2: Backend network-info endpoint

**Files:**
- Create: `backend/app/routers/network.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_network.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routers_network.py`:

```python
import re

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_network_info_returns_local_ip(client):
    response = await client.get("/api/network-info")
    assert response.status_code == 200
    data = response.json()
    assert "local_ip" in data
    assert IP_RE.match(data["local_ip"]), f"Expected IP, got: {data['local_ip']!r}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_routers_network.py -v
```
Expected: FAIL with 404 or import error (router not yet registered)

- [ ] **Step 3: Create the router**

Create `backend/app/routers/network.py`:

```python
import socket

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["network"])


def _get_local_ip() -> str:
    """Return the LAN IP of this machine using a UDP socket trick."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


@router.get("/network-info")
async def get_network_info():
    return {"local_ip": _get_local_ip()}
```

- [ ] **Step 4: Register router in main.py**

In `backend/app/main.py`, add the import with the other router imports:

```python
from app.routers import (
    activity, events, files, issue_relations, issues, library,
    network,  # add this
    project_settings, project_skills, project_templates, project_variables,
    projects, settings as settings_router, tasks, terminals, terminal_commands
)
```

Then add the include after the existing `app.include_router` calls (before `app.mount("/mcp", mcp_app)`):

```python
app.include_router(network.router)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_routers_network.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/network.py backend/app/main.py backend/tests/test_routers_network.py
git commit -m "feat: add /api/network-info endpoint returning LAN IP"
```

---

### Task 3: Frontend QR code dialog

**Files:**
- Modify: `frontend/package.json` (install dep)
- Create: `frontend/src/shared/components/smartphone-qr-dialog.tsx`
- Modify: `frontend/src/shared/components/app-sidebar.tsx`

- [ ] **Step 1: Install react-qr-code**

```bash
cd frontend && npm install react-qr-code --legacy-peer-deps
```

Expected: `react-qr-code` appears in `package.json` dependencies.

- [ ] **Step 2: Create the dialog component**

Create `frontend/src/shared/components/smartphone-qr-dialog.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import QRCode from "react-qr-code";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";

interface SmartphoneQrDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

async function fetchNetworkInfo(): Promise<{ local_ip: string }> {
  const res = await fetch("/api/network-info");
  if (!res.ok) throw new Error("Failed to fetch network info");
  return res.json();
}

export function SmartphoneQrDialog({ open, onOpenChange }: SmartphoneQrDialogProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["network-info"],
    queryFn: fetchNetworkInfo,
    enabled: open,
    staleTime: 30_000,
  });

  const url = data
    ? `http://${data.local_ip}:${window.location.port || "4173"}`
    : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Open on Smartphone</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4 py-4">
          {isLoading && (
            <p className="text-sm text-muted-foreground">Detecting network address...</p>
          )}
          {isError && (
            <p className="text-sm text-destructive">Could not detect local IP address.</p>
          )}
          {url && (
            <>
              <div className="bg-white p-4 rounded-lg">
                <QRCode value={url} size={200} />
              </div>
              <code className="text-xs text-muted-foreground break-all">{url}</code>
              <p className="text-xs text-muted-foreground text-center">
                Make sure your phone is on the same Wi-Fi network.
              </p>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 3: Add button to sidebar footer**

In `frontend/src/shared/components/app-sidebar.tsx`:

Add `Smartphone` to the lucide-react import at the top:

```tsx
import {
  Activity,
  BookOpen,
  CircleDot,
  Download,
  FileText,
  FolderSync,
  Key,
  LayoutDashboard,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Plug,
  Settings,
  Smartphone,        // add this
  SquareTerminal,
  Terminal,
} from "lucide-react";
```

Add the import for the new dialog near the other dialog imports:

```tsx
import { SmartphoneQrDialog } from "@/shared/components/smartphone-qr-dialog";
```

Add state for the dialog inside the `AppSidebar` function (with the other `useState` calls):

```tsx
const [smartphoneQrOpen, setSmartphoneQrOpen] = useState(false);
```

Replace the `<SidebarFooter>` block with:

```tsx
<SidebarFooter>
  <SidebarMenu>
    <SidebarMenuItem>
      <SidebarMenuButton size="sm" onClick={() => setSmartphoneQrOpen(true)}>
        <Smartphone className="h-4 w-4" />
        <span className="text-xs">Show on Smartphone</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  </SidebarMenu>
</SidebarFooter>
```

Add the dialog render at the end of the return statement, alongside the other dialogs (before the final `</>`):

```tsx
<SmartphoneQrDialog
  open={smartphoneQrOpen}
  onOpenChange={setSmartphoneQrOpen}
/>
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/shared/components/smartphone-qr-dialog.tsx frontend/src/shared/components/app-sidebar.tsx
git commit -m "feat: add Show on Smartphone button with QR code dialog"
```

---

## Self-Review

**Spec coverage:**
- Backend binds to 0.0.0.0 → Task 1 ✓
- Backend endpoint for local IP → Task 2 ✓
- QR code dialog → Task 3 ✓
- Button in sidebar → Task 3 ✓
- Test for endpoint → Task 2 ✓

**Placeholders:** None — all code blocks are complete and runnable.

**Type consistency:**
- `fetchNetworkInfo` returns `{ local_ip: string }` → used as `data.local_ip` in the component ✓
- `SmartphoneQrDialogProps` has `open` and `onOpenChange` → matches usage in sidebar ✓
- `network.router` imported from `app.routers.network` → matches file created in Task 2 ✓
