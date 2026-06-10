Aggiunto toggle UI per auto-processo coda:

**Backend:** Nuovo endpoint `POST /api/queue/auto-process` in `backend/app/routers/queue.py` — usa `SettingsService.set()` + `issue_queue_service_ref.set_enabled()` (stessa logica dell'MCP `queue_set_auto_process`).

**Frontend:**
- Creato componente `Switch` shadcn in `shared/components/ui/switch.tsx` usando radix-ui
- Aggiunto `auto_process_enabled` al tipo `QueueStatus` in `features/queue/api.ts`
- Aggiunta API `setAutoProcess()` e mutation hook `useSetAutoProcess()` con invalidation di `queueKeys.status`
- Inserito Switch toggle nell'header della Queue page, accanto al badge Paused, che mostra "Auto-process" con label verde se attivo

Il toggle aggiorna lo stato in tempo reale via la mutation di TanStack Query che invalida la status query (refetch ogni 10s).