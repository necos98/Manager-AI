## Implementation Plan: Toggle UI per auto-processo coda

**Goal:** Aggiungere toggle UI nella pagina Queue per attivare/disattivare queue_auto_process.

**Architecture:** Nuovo endpoint REST POST /api/queue/auto-process che usa SettingsService + issue_queue_service_ref (stessa logica MCP). Switch shadcn/radix nel frontend. Nessuna modifica a modelli DB o WebSocket.

**Tech Stack:** Python/FastAPI backend, React/shadcn-ui/radix-ui frontend, TanStack Query per mutation.

---

### Task 1: Endpoint REST backend

**Files:**
- Modify: `backend/app/routers/queue.py` — aggiungere endpoint + schema

**Step 1: Aggiungere schema e import in queue.py**

```python
# Dopo QueueStatus, aggiungere:
class SetAutoProcessRequest(BaseModel):
    enabled: bool

# In cima al file, aggiungere import:
from app.services.issue_queue_service import issue_queue_service_ref
```

**Step 2: Aggiungere endpoint POST /api/queue/auto-process**

```python
@router.post("/auto-process", response_model=dict)
async def set_auto_process(
    body: SetAutoProcessRequest,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable automatic queue processing."""
    from app.services.settings_service import SettingsService
    svc = SettingsService(db)
    await svc.set("queue_auto_process", "true" if body.enabled else "false")
    await db.commit()

    if issue_queue_service_ref is not None:
        await issue_queue_service_ref.set_enabled(body.enabled)

    return {"enabled": body.enabled}
```

---

### Task 2: Switch shadcn UI component

**Files:**
- Create: `frontend/src/shared/components/ui/switch.tsx`

**Step 1: Creare componente Switch shadcn**

```tsx
import * as React from "react"
import { Switch as SwitchPrimitive } from "radix-ui"
import { cn } from "@/shared/lib/utils"

function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      className={cn(
        "peer inline-flex h-5 w-9 shrink-0 items-center rounded-full border-2 border-transparent",
        "shadow-xs transition-all outline-none",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "data-[state=checked]:bg-primary data-[state=unchecked]:bg-input",
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className={cn(
          "pointer-events-none block size-4 rounded-full bg-background shadow-lg ring-0 transition-transform",
          "data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0",
        )}
      />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
```

---

### Task 3: Frontend API + mutation hook

**Files:**
- Modify: `frontend/src/features/queue/api.ts` — aggiungere tipo + funzione
- Modify: `frontend/src/features/queue/hooks.ts` — aggiungere mutation hook
- Modify: `frontend/src/features/queue/api.ts` — aggiungere `auto_process_enabled` a QueueStatus

**Step 1: Aggiungere auto_process_enabled a QueueStatus in api.ts**

```typescript
export interface QueueStatus {
  queued_count: number;
  running_count: number;
  paused: boolean;
  auto_process_enabled: boolean;  // <-- aggiungere
}
```

**Step 2: Aggiungere setAutoProcess API in api.ts**

```typescript
export function setAutoProcess(enabled: boolean): Promise<{ enabled: boolean }> {
  return apiPost("/queue/auto-process", { enabled });
}
```

Serve import: `import { apiGet, apiPost } from "@/shared/api/client";` (cambia da `import { apiGet }`)

**Step 3: Aggiungere mutation hook in hooks.ts**

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export function useSetAutoProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => api.setAutoProcess(enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queueKeys.status });
    },
  });
}
```

---

### Task 4: Toggle nella Queue page

**Files:**
- Modify: `frontend/src/routes/queue.tsx`

**Step 1: Aggiungere import Switch e mutation hook**

```typescript
import { Switch } from "@/shared/components/ui/switch";
import { useSetAutoProcess } from "@/features/queue/hooks";
```

**Step 2: Aggiungere mutation call e toggle nell'header**

Dopo `const isPaused = statusData?.paused ?? false;` aggiungere:

```typescript
const isAutoProcessEnabled = statusData?.auto_process_enabled ?? false;
const setAutoProcess = useSetAutoProcess();
```

Nell'header, dopo il badge Paused, aggiungere:

```tsx
{/* Auto-process toggle */}
<label className="flex items-center gap-2 text-xs cursor-pointer">
  <Switch
    checked={isAutoProcessEnabled}
    onCheckedChange={(checked) => setAutoProcess.mutate(checked)}
    disabled={setAutoProcess.isPending}
  />
  <span className={isAutoProcessEnabled ? "text-emerald-500" : "text-muted-foreground"}>
    Auto-process
  </span>
</label>
```
