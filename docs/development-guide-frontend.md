# Development Guide — Frontend

**Part:** frontend
**Generated:** 2026-06-07

## Prerequisites

- Node.js (version matching `package.json` engines or latest LTS)
- npm

## Setup

```bash
cd frontend
npm install
npm run dev        # Dev server on :5173, proxies /api → backend :8000
```

## Build

```bash
cd frontend
npm run build      # Vite production build
npm run preview    # Preview production build
```

## Linting

```bash
cd frontend
npm run lint       # ESLint flat config (eslint.config.js)
```

## Type Checking

```bash
cd frontend
npx tsc --noEmit   # TypeScript strict mode check
```

## Architecture Notes

- **Routing:** File-based via TanStack Router in `src/routes/`
- **API Client:** Custom fetch wrapper in `src/shared/api/client.ts`
- **State Mgmt:** TanStack Query for server state + EventProvider (WebSocket) for real-time
- **UI:** Tailwind CSS 4 (CSS-first, no tailwind.config.js) + Radix UI primitives
- **Imports:** Use `@/` alias mapped to `./src/`, never relative cross-feature imports
- **Components:** Named function exports, no `export default`

## Key Conventions

- Query key factory: `featureKeys.all`, `featureKeys.detail(id)`, `featureKeys.tasks`
- Mutation error handler: `onMutationError` with sonner toast
- React 19: ref passes as prop (no `forwardRef`)
