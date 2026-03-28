---
name: react-19
category: tech
description: React 19 patterns, hooks, TypeScript conventions
built_in: true
---
# React 19 Conventions

## Components
- Functional components only, no class components
- TypeScript interfaces for all props, never `any`
- Co-locate component, types, and hooks in feature folders

## State & Data
- TanStack Query for server state (never fetch in useEffect)
- `useState` only for pure UI state (modals, toggles)
- Avoid prop drilling beyond 2 levels — use context or query cache

## Hooks
- Custom hooks prefixed `use`, return typed objects not arrays
- No business logic in components — extract to custom hooks

## Styling
- Tailwind CSS utility classes
- Shadcn/ui components as base
- `cn()` for conditional class merging

## Performance
- `useMemo`/`useCallback` only when profiling shows a problem
- Lazy load routes with `React.lazy`
