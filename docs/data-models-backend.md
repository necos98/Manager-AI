# Data Models — Backend

**Part:** backend
**Project Type:** Python/FastAPI
**Generated:** 2026-06-07
**Total Tables:** 24

## Entity-Relationship Overview

```
Project ──┬── Issue ──┬── Task
           │           ├── IssueFeedback
           │           └── IssueRelation
           ├── ProjectFile
           ├── ProjectLink
           ├── ProjectSetting (kv)
           ├── ProjectSkill
           ├── ProjectVariable
           ├── ProjectCredential
           ├── Pipeline ──┬── PipelineStep ──┬── PipelineEventRule
           │              └── PipelineStepRun
           ├── PipelineRun ──┬── PipelineStepRun
           │                 └── PipelineMessage
           ├── Memory ──┬── MemoryLink
           └── ActivityLog
```

## Core Tables

### projects
| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK, UUID default |
| name | String(255) | NOT NULL |
| path | String(500) | NOT NULL |
| description | Text | Default: "" |
| tech_stack | Text | Default: "" |
| shell | String(500) | Nullable |
| wsl_distro | String(100) | Nullable |
| url | String(2000) | Nullable |
| created_at | DateTime | server_default=now() |
| updated_at | DateTime | server_default=now(), onupdate |
| archived_at | DateTime | Nullable |
| favorited_at | DateTime | Nullable |

**Relationships:** issues, files

### issues
| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK, UUID default |
| project_id | String(36) | FK → projects.id, NOT NULL |
| name | String(255) | Nullable |
| description | Text | NOT NULL |
| status | Enum(IssueStatus) | Default: "New" |
| priority | Integer | Default: 3 |
| category | String(50) | Nullable. Allowed: Bug, Feature, Improvement, Documentation, Refactor, Security, Performance, UI/UX |
| plan | Text | Nullable |
| specification | Text | Nullable |
| recap | Text | Nullable |
| created_at | DateTime | server_default=now() |
| updated_at | DateTime | server_default=now(), onupdate |
| finished_at | DateTime | Nullable |

**Statuses:** New → Reasoning → Planned → Accepted/Declined → Finished/Canceled
**Relationships:** project, tasks (cascade delete), feedback (cascade delete)

### tasks
| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK, UUID default |
| issue_id | String(36) | FK → issues.id, NOT NULL |
| name | String(255) | NOT NULL |
| description | Text | Default: "" |
| status | String(50) | Default: "pending" |
| order | Integer | Default: 0 |
| assigned_agent | String(255) | Nullable |
| result | Text | Nullable |
| created_at | DateTime | server_default=now() |
| updated_at | DateTime | server_default=now(), onupdate |

## Support Tables

### issue_feedback
| Column | Notes |
|--------|-------|
| id, issue_id (FK), author, content, type (approve/reject/revise), created_at | Per-issue feedback |

### issue_relations
| Column | Notes |
|--------|-------|
| id, source_issue_id (FK), target_issue_id (FK), relation_type (Enum: RELATED/DUPLICATE/BLOCKS/DEPENDS_ON) | Links issues together |

### project_files
| Column | Notes |
|--------|-------|
| id, project_id (FK), filename, filepath, filetype, size, extracted_text, checksum, created_at | File attachments with text extraction |

### project_links
| Column | Notes |
|--------|-------|
| id, project_id (FK), url, title, created_at | External project links |

### project_variables
| Column | Notes |
|--------|-------|
| id, project_id (FK), key, value, is_secret, created_at | Templated variables resolved at runtime |

### project_skills
| Column | Notes |
|--------|-------|
| id, project_id (FK), skill_name, config (JSON), created_at | Per-project skill overrides |

### project_credentials
| Column | Notes |
|--------|-------|
| id, project_id (FK), role, value (encrypted), created_at | Encrypted API keys/credentials |

### credential_presets
| Column | Notes |
|--------|-------|
| id, name, role, value (encrypted), category, created_at | Reusable credential templates |

## Pipeline Tables

### pipelines
| Column | Notes |
|--------|-------|
| id, name, description, is_template, created_at, updated_at | Pipeline definitions |

### pipeline_steps
| Column | Notes |
|--------|-------|
| id, pipeline_id (FK), order, name, agent_type, prompt_template, created_at | Steps within a pipeline |

### pipeline_event_rules
| Column | Notes |
|--------|-------|
| id, step_id (FK), event_type, condition, config (JSON), created_at | Event-triggered rules per step |

### pipeline_runs
| Column | Notes |
|--------|-------|
| id, pipeline_id (FK), project_id, status, triggered_by, created_at, completed_at | Pipeline execution instances |

### pipeline_step_runs
| Column | Notes |
|--------|-------|
| id, run_id (FK), step_id (FK), status, input, output, agent_id, started_at, completed_at | Per-step execution records |

### pipeline_messages
| Column | Notes |
|--------|-------|
| id, run_id (FK), role, content, step_id, created_at | Messages within a pipeline run |

### pipeline_logs
| Column | Notes |
|--------|-------|
| id, run_id (FK), level, message, created_at | Pipeline execution logs |

## Agent & Memory Tables

### agents
| Column | Notes |
|--------|-------|
| id, name, role, system_prompt, model, temperature, max_tokens, is_default, created_at, updated_at | AI agent configurations |

### memories
| Column | Notes |
|--------|-------|
| id, project_id (FK), name, description, content, type, metadata (JSON), embedding_id, created_at, updated_at | Project-scoped memories with optional vector embeddings |

### memory_links
| Column | Notes |
|--------|-------|
| id, source_id (FK), target_id (FK), created_at | Bidirectional memory links |

## Other Tables

### settings
| Column | Notes |
|--------|-------|
| key (PK), value, created_at, updated_at | Global app settings (kv store) |

### questions
| Column | Notes |
|--------|-------|
| id, project_id (FK), title, question, answer, status, created_at, answered_at | Agent questions awaiting human answers |

### prompt_templates
| Column | Notes |
|--------|-------|
| id, type (PK), content, created_at, updated_at | Reusable prompt templates per project |

### terminal_commands
| Column | Notes |
|--------|-------|
| id, project_id (FK), label, command, cwd, order, created_at, updated_at | Saved terminal command templates |

### activity_logs
| Column | Notes |
|--------|-------|
| id, project_id (FK), action, entity_type, entity_id, details (JSON), created_at | Project activity audit trail |

## Database Technology

- **Engine:** SQLite (via aiosqlite async driver)
- **ORM:** SQLAlchemy 2.0+ async (`Mapped` annotations, `mapped_column`)
- **Migrations:** Alembic 1.15.2
- **Vector Store:** LanceDB (separate from SQLite, not in SQLAlchemy schema)
- **Constraints:** Single-process writes only (`uvicorn --workers 1`). No Postgres/Redis.
