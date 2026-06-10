## Piano di Implementazione — Issue Queue Globale UI

### Architettura
Backend: nuovo router `backend/app/routers/queue.py` con 3 endpoint REST globali (GET /api/queue, GET /api/queue/running, GET /api/queue/status).
Frontend: nuova pagina `/queue` con due sezioni (In esecuzione + In coda), React Query hooks, registrazione route TanStack, voce nella sidebar Global.

### Ordine di implementazione
1. Backend — nuovo router queue.py (3 endpoint globali)
2. Backend — registrazione router in main.py
3. Frontend — API hooks (features/queue/api.ts + hooks.ts)
4. Frontend — route page (routes/queue.tsx)
5. Frontend — registrazione route in routeTree.gen.ts
6. Frontend — navigazione sidebar (project-sidebar.tsx)
7. Verifica
