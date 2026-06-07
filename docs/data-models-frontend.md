# Data Models — Frontend

**Part:** frontend
**Project Type:** React/TypeScript (Web)
**Generated:** 2026-06-07

## Type System

- **Language:** TypeScript 6.0.2 (strict mode with `noUncheckedIndexedAccess`)
- **Shared types:** `src/shared/types/`
- **Validation:** Runtime via server Pydantic schemas; frontend uses `zod`-style where needed

## Key Data Shapes

### Issue
```
id: string, projectId: string, name?: string, description: string,
status: IssueStatus, priority: number, category?: string,
plan?: string, specification?: string, recap?: string,
createdAt: Date, updatedAt: Date, finishedAt?: Date,
tasks?: Task[], feedback?: IssueFeedback[]
```

### Project
```
id: string, name: string, path: string, description: string,
techStack: string, shell?: string, wslDistro?: string, url?: string,
createdAt: Date, updatedAt: Date, archivedAt?: Date, favoritedAt?: Date
```

### Task
```
id: string, issueId: string, name: string, description: string,
status: string, order: number, assignedAgent?: string, result?: string,
createdAt: Date, updatedAt: Date
```

### Terminal / PipelineRun / Agent / File / Memory
— Shapes mirror backend SQLAlchemy models with camelCase conversion.

## State Management

| Layer | Mechanism | Scope |
|-------|-----------|-------|
| Server state | TanStack Query | API data caching + mutations |
| Real-time events | EventProvider (WebSocket) | Live updates across clients |
| UI state | React state / context | Local component state |
| Theme | next-themes | Dark/light mode |

## Cache Invalidation

React Query keys per feature using factory pattern:
```
issuesKeys.all      → invalidate on mutation
issuesKeys.detail() → refetch single issue
pipelinesKeys.all   → invalidate pipeline list
```
