---
id: be6d8d33-1678-4df0-989a-9aaceeaa0fcf
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: Pipeline start race condition fix — create_task before commit
parent_id: null
created_at: '2026-06-05T11:47:49.127039'
updated_at: '2026-06-05T11:47:49.127039'
links: []
---
Fixed two-part race condition in pipeline_run_service.py: (1) Swapped create_task before commit in start() so crash between them rolls back the transaction instead of leaving a stuck RUNNING run. (2) Added retry loop (50×100ms) in _execute() to handle the timing window where _execute runs before commit finishes. Single file change. This replaces the old pattern (commit before create_task) that caused the bug.