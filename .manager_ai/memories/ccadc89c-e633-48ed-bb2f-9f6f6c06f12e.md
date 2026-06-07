---
id: ccadc89c-e633-48ed-bb2f-9f6f6c06f12e
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: Reverse index issue_id→project_path in MemoryStoreCore
parent_id: null
created_at: '2026-06-05T11:28:31.394322'
updated_at: '2026-06-05T11:28:31.394322'
links: []
---
Added `_issue_to_project` dict to MemoryStoreCore mapping `issue_id → project_path` for O(1) lookup in IssueService.get_by_id(). Lifecycle hooks in init_project/upsert/delete/remove_project/reset keep the index consistent with source of truth. IssueService.get_by_id() uses the index first, then verifies project is not archived (via ProjectService.get_by_id + archived_at check), with fallback to full scan on miss or when project is deleted/archived. Key design decision: index maps to project_path (not project_id) because MemoryStoreCore._projects keys on project_path and load_issue() takes project_path. 3 files changed: memory_store_core.py, issue_store.py, issue_service.py.