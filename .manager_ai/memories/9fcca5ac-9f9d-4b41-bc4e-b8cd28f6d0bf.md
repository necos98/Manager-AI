---
id: 9fcca5ac-9f9d-4b41-bc4e-b8cd28f6d0bf
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: 'Create from here: router-level relation creation pattern'
parent_id: null
created_at: '2026-06-04T10:09:18.779448'
updated_at: '2026-06-04T10:09:18.779448'
links: []
---
The "Create issue from here" feature adds source_issue_id to IssueCreate schema and handles relation creation in the router layer (not IssueService). Pattern: after IssueService.create() succeeds, if source_issue_id is set, instantiate IssueRelationService and call add_relation(new_id, source_id, RELATED) — all before db.commit(). This avoids coupling issue_service with relation_service and follows the existing pattern (e.g., complete_issue fires hooks after service call in the router). Relation normalization (sorted IDs for RELATED) is handled by IssueRelationService.add_relation() internally.