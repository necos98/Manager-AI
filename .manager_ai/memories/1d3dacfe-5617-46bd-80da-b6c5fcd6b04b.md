---
id: 1d3dacfe-5617-46bd-80da-b6c5fcd6b04b
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: Two directory trees for same repo
parent_id: null
created_at: '2026-06-03T13:36:21.560083'
updated_at: '2026-06-03T13:36:21.560083'
links: []
---
Two separate git clones exist: `manager-ai\Manager-AI\` (used by Python sys.path for imports) and `manager-ai-mod\Manager-AI\` (the session working directory). Edits to .py files in one directory don't affect the other. Always edit BOTH or fix sys.path. The `.pyc` bytecode cache at each tree's __pycache__ is independent.