---
id: c47b4dbd-852a-4ed5-8efc-cdb5ab900a5b
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: Batch export design decisions
parent_id: null
created_at: '2026-06-05T07:43:28.064566'
updated_at: '2026-06-05T07:43:28.064566'
links: []
---
Selective export uses POST batch endpoints (not GET) with JSON body `{ agent_ids: [...] }`. Non-existent IDs in batch request are silently skipped. Save-As dialog via `showSaveFilePicker` (File System Access API) with `downloadBlob()` fallback for non-Chromium browsers. `downloadBlob` was duplicated in agents/hooks.ts and pipelines/hooks.ts — extracted to shared utility `frontend/src/shared/utils/download.ts`. Single-item export buttons remain unchanged for backward compatibility. See issue ddf8d899 for full spec.