# Specification: Regenerate index YAML files on startup from directory files

## Problem

The `.manager_ai/` directory contains index YAML files (`issues.yaml`, `memories.yaml`, `files.yaml`) that aggregate metadata from individual files in subdirectories (`issues/<id>/`, `memories/<id>.md`, `files/<id>.txt`). These index files are tracked in git and can become corrupted during git operations (merge conflicts, partial pulls), causing the application to lose track of issues, memories, or files even though the individual source files are intact.

## Solution

1. **Regenerate index YAML files on every startup**: Before the filesystem watcher begins observing, call the existing `rebuild_*_index()` functions to regenerate all three index files from their respective directory contents.

2. **Add index YAML files to `.gitignore`**: Exclude `issues.yaml`, `memories.yaml`, and `files.yaml` from version control so they are no longer tracked by git. The individual files in subdirectories remain the single source of truth.

## Implementation

### File 1: `.manager_ai/.gitignore`
Add three entries:
- `issues.yaml`
- `memories.yaml`
- `files.yaml`

### File 2: `backend/app/services/manager_ai_watcher.py`
In `ManagerAiWatcher.start_project()`, before starting the observer, call:
- `issue_store.rebuild_issues_index(project_path)`
- `memory_store.rebuild_memories_index(project_path)`
- `file_store.rebuild_files_index(project_path)`

## Constraints

- The watcher's `_classify` method already correctly skips root-level index YAML files (only triggers rebuilds for files inside subdirectories, checked via `len(parts) > 1`). No changes needed to the classification logic.
- The existing `rebuild_*_index()` functions already handle missing/empty directories gracefully (they create empty index files with just `schema_version` and an empty list).
- No API or frontend changes required — the rebuild is transparent to consumers.

## Scope

- All three index files: `issues.yaml`, `memories.yaml`, `files.yaml`
- Startup rebuild only (runtime changes already handled by watcher)
- Git tracking removal via `.gitignore`
