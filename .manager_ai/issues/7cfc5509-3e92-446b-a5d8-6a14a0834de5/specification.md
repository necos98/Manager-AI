# Pipeline DB Schema & Models — Specification

## Overview

Create 6 SQLAlchemy models and an Alembic migration to support the agent pipeline orchestration system. These tables store agent definitions, pipeline configurations, execution history, and inter-agent chat messages.

## Tables

### 1. Agent (`agents`)

Reusable agent definition. One agent can be used across multiple pipelines and pipeline steps.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | PK, UUID |
| `project_id` | String(36) | FK → projects.id, NOT NULL, indexed |
| `name` | String(255) | NOT NULL |
| `system_prompt` | Text | NOT NULL |
| `model` | String(50) | nullable (e.g. "opus", "sonnet", "haiku") |
| `allowed_tools` | JSON | nullable, list of MCP tool names |
| `created_at` | DateTime | server_default=now() |
| `updated_at` | DateTime | server_default=now(), onupdate=now() |

UniqueConstraint: `(project_id, name)` — agent names scoped per project.

### 2. Pipeline (`pipelines`)

Ordered sequence of steps that execute when a pipeline is triggered on an issue.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | PK, UUID |
| `project_id` | String(36) | FK → projects.id, NOT NULL, indexed |
| `name` | String(255) | NOT NULL |
| `created_at` | DateTime | server_default=now() |
| `updated_at` | DateTime | server_default=now(), onupdate=now() |

Relationship: `steps` → PipelineStep (cascade delete-orphan, ordered by `order_index`).

### 3. PipelineStep (`pipeline_steps`)

Individual step within a pipeline, linking an agent to a terminal command.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | PK, UUID |
| `pipeline_id` | String(36) | FK → pipelines.id, CASCADE, NOT NULL |
| `agent_id` | String(36) | FK → agents.id, NOT NULL |
| `order_index` | Integer | NOT NULL |
| `terminal_command` | Text | NOT NULL (e.g. `claude "/run-pipeline-step $STEP_ID" --dangerously-skip-permissions`) |
| `created_at` | DateTime | server_default=now() |
| `updated_at` | DateTime | server_default=now(), onupdate=now() |

UniqueConstraint: `(pipeline_id, order_index)`.

### 4. PipelineRun (`pipeline_runs`)

Tracks a single pipeline execution triggered on an issue.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | PK, UUID |
| `pipeline_id` | String(36) | FK → pipelines.id, NOT NULL, indexed |
| `issue_id` | String(255) | NOT NULL (string, no FK — may reference external issues) |
| `status` | Enum(PipelineRunStatus) | NOT NULL, default RUNNING |
| `current_step_index` | Integer | NOT NULL, default 0 |
| `started_at` | DateTime | nullable |
| `finished_at` | DateTime | nullable |
| `created_at` | DateTime | server_default=now() |

Enum `PipelineRunStatus`: RUNNING, COMPLETED, FAILED.

### 5. PipelineStepRun (`pipeline_step_runs`)

Individual step execution record within a pipeline run.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | PK, UUID |
| `pipeline_run_id` | String(36) | FK → pipeline_runs.id, CASCADE, NOT NULL, indexed |
| `pipeline_step_id` | String(36) | FK → pipeline_steps.id, NOT NULL |
| `terminal_id` | Integer | FK → terminal_commands.id, nullable, SET NULL on delete |
| `status` | Enum(PipelineStepRunStatus) | NOT NULL, default PENDING |
| `started_at` | DateTime | nullable |
| `finished_at` | DateTime | nullable |

Enum `PipelineStepRunStatus`: PENDING, RUNNING, COMPLETED, FAILED.

### 6. PipelineMessage (`pipeline_messages`)

Inter-agent chat messages scoped to a pipeline run.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | PK, UUID |
| `pipeline_run_id` | String(36) | FK → pipeline_runs.id, CASCADE, NOT NULL, indexed |
| `sender_agent_name` | String(255) | NOT NULL |
| `content` | Text | NOT NULL (markdown) |
| `created_at` | DateTime | server_default=now() |

## Relationships

```
Project 1→N Agent        (cascade delete)
Project 1→N Pipeline     (cascade delete)
Pipeline 1→N PipelineStep (cascade delete-orphan, ordered by order_index)
Agent 1→N PipelineStep    (no cascade — deleting an agent should not delete step history)
PipelineRun N→1 Pipeline  (no cascade — keep run history when pipeline deleted)
PipelineRun N→1 Issue     (logical only, no FK)
PipelineRun 1→N PipelineStepRun (cascade delete-orphan)
PipelineStep 1→N PipelineStepRun (no cascade)
PipelineStepRun N→1 TerminalCommand (SET NULL on delete)
PipelineRun 1→N PipelineMessage (cascade delete-orphan)
```

## Migration

Single Alembic migration creating all 6 tables with indexes, constraints, and FKs. Enums are SQLAlchemy Enum types stored as strings in SQLite.

## Testing

Unit test that:
1. Creates all 6 tables (verified by querying SQLAlchemy inspector)
2. Inserts a minimal pipeline with agent → step → run → step_run → message chain
3. Verifies FK constraints: cascade deletes propagate correctly (pipeline → steps, pipeline_run → step_runs, pipeline_run → messages)
4. Verifies UniqueConstraints (duplicate agent name in same project raises IntegrityError)
