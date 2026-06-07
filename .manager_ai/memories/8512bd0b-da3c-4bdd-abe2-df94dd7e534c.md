---
id: 8512bd0b-da3c-4bdd-abe2-df94dd7e534c
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: $issueId.tsx refactoring — layout mode approach
parent_id: null
created_at: '2026-06-07T14:28:28.760789'
updated_at: '2026-06-07T14:28:28.760789'
links: []
---
Spec for refactoring `$issueId.tsx` (324 lines, 1 component) extracts 3 components (TerminalActionBar, PendingQuestionsSection, TerminalDialogs) + 1 hook (useTerminalLayout). Core architectural decision: compute layout mode as an enum ('issue-only', 'issue-pipeline', 'split-with-tabs', 'single-terminal') instead of 10-branch nested conditionals. Single ErrorBoundary at root. Callbacks wrapped in useCallback. No behavior changes. Spec written by SpecWriter agent in pipeline, reviewed by SpecReviewer next.