## Aggiungere toggle UI per auto-processo coda

### Obiettivo
Aggiungere toggle UI nella pagina Queue per attivare/disattivare `queue_auto_process`, completando il gap tra backend (logica già presente) e frontend.

### Backend — Nuovo endpoint REST
- `POST /api/queue/auto-process` in `backend/app/routers/queue.py`
- Body: `{ "enabled": bool }`
- Usa `SettingsService.set("queue_auto_process", "true"/"false")` + chiama `issue_queue_service_ref.set_enabled(enabled)` per aggiornare stato in-memory (stessa logica dell'MCP tool `queue_set_auto_process`)
- Response: `{ "enabled": bool }`

### Frontend — Nuovo Switch shadcn
- Creare `Switch` component in `shared/components/ui/switch.tsx` usando `import { Switch as SwitchPrimitive } from "radix-ui"` + stile shadcn new-york
- Aggiungere `setAutoProcess(enabled: boolean)` API in `features/queue/api.ts`
- Aggiungere `useSetAutoProcess()` mutation hook in `features/queue/hooks.ts` con invalidation di `queueKeys.status`
- Inserire Switch nell'header della Queue page (`frontend/src/routes/queue.tsx`), accanto al badge "Paused", leggendo `statusData?.auto_process_enabled`

### WebSocket real-time
- L'`useEffect` esistente già invalida `queueKeys.status` su `issue_status_changed` — copre già l'aggiornamento dello stato. Nessun evento WebSocket aggiuntivo necessario.

### Test
- Test manuale: toggle on → verifica `auto_process_enabled: true` in status, toggle off → `false`
