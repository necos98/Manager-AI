## Problem
The Global section of the project sidebar (`project-sidebar.tsx`) has two identical "Agents" navigation entries — one between Terminals and Questions, and a duplicate between Questions and Pipelines.

## Solution
Remove the duplicate Agents entry (the second one, currently between Questions and Pipelines). The first entry (between Terminals and Questions) stays.

## Affected file
- `frontend/src/shared/components/project-sidebar.tsx`: Remove lines 182-192 (the duplicate SidebarMenuItem block)

## Verification
- Sidebar renders exactly one Agents entry
- Agents link navigates to `/agents` correctly
- All other sidebar entries (Terminals, Questions, Pipelines) are unaffected