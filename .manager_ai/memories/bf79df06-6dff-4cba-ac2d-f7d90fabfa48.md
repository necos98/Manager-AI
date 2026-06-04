---
id: bf79df06-6dff-4cba-ac2d-f7d90fabfa48
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: Export/import uses two-phase conflict resolution pattern
parent_id: null
created_at: '2026-06-04T19:15:44.122489'
updated_at: '2026-06-04T19:15:44.122489'
links: []
---
The export/import feature uses a two-phase import: first pass detects conflicts and returns them without committing (auto-rollback), second pass (after user selects overwrites) commits everything. This avoids partial imports and allows the conflict modal to work without server-side sessions. Export files use a self-contained JSON format with version header and pipelines embed full agent data inline so files work across instances.