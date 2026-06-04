---
id: 6e686d6b-bfc8-4bfa-b3bb-ea148f0956aa
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: 'Pipeline step rejection: while-loop driven by current_step_index'
parent_id: null
created_at: '2026-06-04T10:13:48.923135'
updated_at: '2026-06-04T10:13:48.923135'
links: []
---
_execute() refactored from for-loop to while-loop: `while run.current_step_index < len(steps) and run.status != FAILED`. After each step completes, session.refresh(run) picks up any current_step_index changes from concurrent reject_step() calls. The loop naturally regresses when reject_step sets the index backward.