---
id: f7cefeb4-dd1e-425a-8bdf-ce3e214dbd63
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: EventProvider uses raw query keys not feature key factories for cross-cutting invalidation
parent_id: null
created_at: '2026-06-07T08:24:41.066853'
updated_at: '2026-06-07T08:24:41.066853'
links: []
---
The frontend EventProvider (`event-context.tsx`) is framework-level infrastructure, not a feature module. When invalidating React Query caches in response to WebSocket events, use raw query key arrays like `["agents"]` and `["pipelines"]` rather than importing `agentKeys` / `pipelineKeys` from feature hooks files.

This avoids coupling the infrastructure layer to feature internals. React Query's default fuzzy matching (`exact: false`) means `["agents"]` already matches both `["agents"]` (list) and `["agents", "<id>"]` (detail) — no loss of coverage.

Existing examples in the codebase: pipeline-run events use `["pipeline-runs", data.project_id]` directly (line 310), terminal events use `["terminals"]` (line 316), memory events use `["projects", data.project_id, "memories"]` (line 327).

**Why:** Separation of concerns — infrastructure layer shouldn't depend on feature-specific key factories. Also avoids potential circular imports since `event-context.tsx` is a shared module imported by features.

**How to apply:** In EventProvider handlers for agent/pipeline WS events, use `["agents"]` and `["pipelines"]` directly. Do NOT import `agentKeys` or `pipelineKeys`.