---
id: 0ffdbba5-178a-4de4-94ad-8ab39ffc18c2
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: 'Spec review: AC "zero behavior change" claims must account for intentional error strategy changes'
parent_id: null
created_at: '2026-06-05T12:21:55.026867'
updated_at: '2026-06-05T12:21:55.026867'
links: []
---
During spec review for lifespan decomposition, AC #6 claimed "zero behavior change" but the spec intentionally changed project loading from continue-on-error to fail-fast. Future specs should either: (a) explicitly list accepted deviations from "no behavior change" when error strategies shift, or (b) phrase AC to scope "zero behavior change" to individual operation internals rather than overall flow. The mix error strategy (user-approved) introduced this gap — reviewers should always cross-check AC against the actual error handling changes.