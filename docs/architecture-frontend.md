# Architecture — Frontend

**Part:** frontend
**Project Type:** React/TypeScript (Web)
**Generated:** 2026-06-07

## Executive Summary

React 19 SPA with TypeScript 6, Vite 5 build tool, TanStack Router for file-based routing, TanStack Query for server state, Tailwind CSS 4 for styling, and Radix UI primitives. Communicates with backend via REST API and WebSocket.

## Technology Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Language | TypeScript | 6.0.2 (strict) |
| UI | React | 19.2.4 |
| Build | Vite | 5.4.0 |
| Routing | TanStack Router | 1.168.7 |
| Server State | TanStack Query | 5.95.2 |
| CSS | Tailwind CSS | 4.2.1 |
| UI Kit | Radix UI | 1.4.3 |
| Icons | lucide-react | 1.7.0 |

## Architecture Pattern: Feature-based

```
src/
├── features/{name}/    # Colocated feature modules
│   ├── components/     # Feature-specific components
│   ├── hooks.ts        # Feature-specific hooks
│   └── api.ts          # API functions (optional)
├── routes/             # File-based router
├── shared/
│   ├── api/            # HTTP client
│   ├── components/     # Shared + UI primitives
│   ├── context/        # EventProvider
│   ├── hooks/          # Global hooks
│   ├── lib/            # Utilities
│   ├── types/          # TypeScript types
│   └── utils/          # Helpers
```

### Key Principles

1. **Feature colocation:** Each feature in `src/features/{name}/` owns its components, hooks, and API calls
2. **No cross-feature relative imports:** Use `@/features/{name}/...` alias
3. **Shared code:** Common components, UI primitives, hooks in `src/shared/`
4. **Named exports:** `export function Component` not `export default`

## State Management

### Server State (TanStack Query)
- Query key factory pattern: `featureKeys.all`, `featureKeys.detail(id)`
- Automatic caching, background refetch, optimistic updates
- Cache invalidation on mutation success

### Real-time State (EventProvider)
- WebSocket connection to `/api/events/ws`
- Live updates for issues, terminals, pipeline runs
- Context-based API in `src/shared/context/event-context.tsx`

### UI State
- Local component state for form inputs, dialogs
- Theme via next-themes (dark/light mode)

## Routing

File-based routing via TanStack Router plugin:
```
src/routes/
├── __root.tsx          # Root layout
├── index.tsx           # Home page
├── projects/
│   ├── $projectId/
│   │   ├── route.tsx
│   │   ├── issues/
│   │   │   ├── $issueId/
│   │   │   │   └── route.tsx
│   │   │   └── route.tsx
│   │   ├── terminals/
│   │   │   └── route.tsx
│   │   └── settings/
│   │       └── route.tsx
```

## UI Component Architecture

```
Radix UI Primitive
  → Tailwind CSS styling
  → cn() merge (clsx + tailwind-merge)
  → Named export component
```

18 UI primitives in `src/shared/components/ui/` (Button, Dialog, Select, etc.)

## Data Flow

```
User Action → Component → API call (client.ts)
  → REST/WS request → Backend → DB
  → Response → Component update
  → Event dispatched (WS)
  → EventProvider → Other components refresh (Query invalidation)
```

## Integration

- **REST:** Fetch wrapper → Vite proxy → Backend `/api/*`
- **WebSocket:** EventProvider ↔ Backend `/api/events/ws`
- **Terminal:** Xterm.js ↔ Backend `/api/terminals/{id}/ws`

## Development

See development-guide-frontend.md for setup and commands.
