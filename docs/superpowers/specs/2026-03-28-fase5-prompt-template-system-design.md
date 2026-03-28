# Fase 5 — Prompt & Template System

Data: 2026-03-28

---

## Obiettivo

Rendere configurabili senza toccare codice: i prompt inviati a Claude, le skill/agent di progetto, e le descrizioni dei tool MCP. Tre layer indipendenti e componibili che insieme danno a Claude il contesto completo per lavorare su un progetto specifico.

---

## Architettura — Tre Layer

| Layer | Cosa controlla | Persistence |
|-------|---------------|-------------|
| Skills & Agents | Knowledge/context del progetto (framework, dominio) | Filesystem (library) + DB (associazioni) |
| Prompt Templates | Istruzioni per task specifici (spec, plan, recap…) | Filesystem (default) + DB (override) |
| MCP Tool Descriptions | Documentazione dei tool per Claude | JSON (default) + ProjectSettings (override) |

---

## 5.1 — Prompt Templates

### Struttura

I template di default vivono come file markdown in `claude_library/templates/`:

```
claude_library/
  templates/
    spec.md
    plan.md
    recap.md
    enrich.md
    workflow.md
    implementation.md
```

Gli override per-progetto sono salvati nella nuova tabella `prompt_templates` nel DB.

### Modello DB

```python
class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: int (PK)
    project_id: int | None  (FK → projects, nullable — null = globale)
    type: str               # "spec" | "plan" | "recap" | "enrich" | "workflow" | "implementation"
    content: str
    created_at: datetime
    updated_at: datetime
```

### Template Resolution Order

1. Override per-progetto nel DB (`project_id` + `type`)
2. Template globale da `claude_library/templates/<type>.md`
3. Fallback hardcoded inline (come oggi — per retrocompatibilità)

### Variabili disponibili

```
{{issue_description}}     Descrizione dell'issue
{{issue_spec}}            Specifica dell'issue (se presente)
{{issue_plan}}            Piano dell'issue (se presente)
{{project_name}}          Nome del progetto
{{project_description}}   Descrizione del progetto
{{tech_stack}}            Stack tecnologico del progetto
{{skills_context}}        Sommario delle skill attive del progetto
```

### PromptTemplateService

Unico punto di risoluzione per tutti i prompt. Tutti i hook handler smettono di costruire prompt inline.

```python
class PromptTemplateService:
    async def resolve(
        self,
        type: str,
        project_id: int,
        variables: dict[str, str]
    ) -> str:
        """Risolve il template nella priority order e sostituisce le variabili."""

    async def get_template(self, type: str, project_id: int) -> str:
        """Ritorna il contenuto raw del template (override o default)."""

    async def save_override(self, type: str, project_id: int, content: str) -> None:
        """Salva un override per-progetto."""

    async def delete_override(self, type: str, project_id: int) -> None:
        """Rimuove l'override, ripristina il default."""

    async def list_for_project(self, project_id: int) -> list[TemplateInfo]:
        """Lista tutti i tipi con flag is_overridden."""
```

`{{skills_context}}` viene risolto automaticamente dal service includendo un sommario delle skill attive del progetto (name + prima riga di descrizione).

---

## 5.2 — Skill & Agent Library

### Struttura Filesystem

```
claude_library/
  skills/
    laravel-12.md       ← built-in
    react-19.md         ← built-in
    django.md           ← built-in
    crm.md              ← built-in
    saas.md             ← built-in
    my-custom-skill.md  ← user-created
  agents/
    backend-architect.md ← built-in
    frontend-expert.md   ← built-in
```

Ogni file ha frontmatter YAML:

```yaml
---
name: laravel-12
category: tech        # tech | domain
description: Patterns, conventions, Eloquent, Pest for Laravel 12
built_in: true        # false per user-created
---
# Laravel 12 Conventions
...contenuto della skill...
```

L'utente può creare nuovi file dalla UI ma **non può eliminarli** dalla UI (solo fisicamente dal filesystem). Questa scelta è intenzionale: le skill sono assets da mantenere con cura, non da cancellare per sbaglio.

### Modello DB — Associazioni

```python
class ProjectSkill(Base):
    __tablename__ = "project_skills"

    id: int (PK)
    project_id: int  (FK → projects)
    name: str        # "laravel-12"
    type: str        # "skill" | "agent"
    assigned_at: datetime
```

### Comportamento all'assegnazione

Quando una skill viene assegnata a un progetto con `project_path`:

1. Crea record in `project_skills`
2. Copia `claude_library/skills/<name>.md` → `<project_path>/.claude/skills/<name>.md`
3. Aggiorna la sezione Manager AI nel `CLAUDE.md` del progetto (vedi sotto)

Quando viene rimossa:

1. Elimina record da `project_skills`
2. Elimina `<project_path>/.claude/skills/<name>.md`
3. Aggiorna CLAUDE.md

### CLAUDE.md — Sezione Manager AI

Manager AI gestisce una sezione delimitata nel `CLAUDE.md` del progetto target. Il contenuto fuori dai marker non viene mai modificato.

```markdown
<!-- MANAGER AI BEGIN -->
## Active Skills
- laravel-12: Patterns, conventions, Eloquent, Pest for Laravel 12
- crm: CRM domain patterns and integration conventions

## Active Agents
- backend-architect: Senior backend architect perspective

Use the Skill tool to invoke any of the above when relevant.
<!-- MANAGER AI END -->
```

Se il `CLAUDE.md` non esiste, viene creato. Se esiste senza la sezione, la sezione viene aggiunta in fondo.

### SkillLibraryService

```python
class SkillLibraryService:
    def list_available(self, type: str = "skill") -> list[SkillMeta]:
        """Legge claude_library/skills/ o agents/ dal filesystem."""

    async def list_assigned(self, project_id: int) -> list[SkillMeta]:
        """Legge da DB."""

    async def assign(self, project_id: int, name: str, type: str) -> None:
        """Crea record DB + copia file + aggiorna CLAUDE.md."""

    async def unassign(self, project_id: int, name: str, type: str) -> None:
        """Rimuove record + elimina copia + aggiorna CLAUDE.md."""

    async def create(self, name: str, type: str, category: str, description: str, content: str) -> None:
        """Crea nuovo file nella library (user-created)."""

    def get_content(self, name: str, type: str) -> str:
        """Ritorna il contenuto markdown della skill."""
```

---

## 5.3 — MCP Tool Descriptions Configurabili

Le descrizioni dei tool MCP vivono già in `backend/app/mcp/default_settings.json`. L'override per-progetto usa le `ProjectSettings` esistenti con chiavi prefissate:

```
mcp_tool_desc.create_issue_spec
mcp_tool_desc.create_issue_plan
mcp_tool_desc.accept_issue
mcp_tool_desc.complete_issue
...
```

Poiché il server MCP è shared (non per-progetto), le descrizioni custom **non** modificano il server MCP stesso. Vengono invece iniettate nel prompt del hook come contesto aggiuntivo:

```
[Tool guidance for this project]
create_issue_plan: ...versione custom per Laravel con Pest...
```

### McpToolDescriptionResolver

```python
class McpToolDescriptionResolver:
    async def resolve(self, tool_name: str, project_id: int) -> str:
        """ProjectSetting override → default_settings.json fallback."""

    async def get_project_overrides(self, project_id: int) -> dict[str, str]:
        """Tutti gli override per un progetto."""

    async def inject_into_prompt(self, prompt: str, project_id: int) -> str:
        """Aggiunge sezione [Tool guidance] al prompt se ci sono override."""
```

---

## Nuovi Endpoint REST

### Library globale

```
GET    /api/library/skills              Lista skill disponibili (filesystem)
GET    /api/library/agents              Lista agent disponibili (filesystem)
POST   /api/library/skills              Crea nuova skill user-created
POST   /api/library/agents              Crea nuovo agent user-created
GET    /api/library/skills/{name}       Contenuto di una skill
PUT    /api/library/skills/{name}       Aggiorna contenuto (solo user-created)
```

### Per-progetto — Skills

```
GET    /api/projects/{id}/skills                Skill assegnate
POST   /api/projects/{id}/skills                Assegna skill { name, type }
DELETE /api/projects/{id}/skills/{type}/{name}  Rimuovi assegnazione
```

### Per-progetto — Templates

```
GET    /api/projects/{id}/templates             Lista tipi con is_overridden flag
GET    /api/projects/{id}/templates/{type}      Contenuto (override o default)
PUT    /api/projects/{id}/templates/{type}      Salva override { content }
DELETE /api/projects/{id}/templates/{type}      Ripristina default
```

---

## UI

### Navigazione

Aggiunge "Library" nella sidebar principale (route `/library`).

### `/library` — Gestione library globale

- Lista skill e agent (filtro per category: tech / domain, tipo: built-in / custom)
- Bottone "Nuova Skill" / "Nuovo Agent" → form con nome, categoria, editor markdown
- Badge "Built-in" vs "Custom"
- Click su una voce → editor markdown fullscreen
- Nessun bottone elimina

### ProjectDetailPage — nuova tab "Library"

Tre sezioni collassabili:

**Skills & Agents**
- Due colonne: "Disponibili" | "Attive nel progetto"
- Card con nome, badge category (tech/domain), descrizione
- Bottone "Aggiungi" / "Rimuovi"
- Badge di sync: verde se il file `.claude/skills/` è presente, giallo se mancante

**Prompt Templates**
- Lista dei 6 tipi
- Editor textarea per ognuno con contenuto corrente
- Badge "Default" / "Personalizzato"
- Bottone "Salva" / "Ripristina default"
- Helper con le variabili disponibili `{{...}}`

**MCP Tool Descriptions**
- Lista dei tool principali
- Textarea per ogni tool con descrizione corrente
- Badge "Default" / "Personalizzato"
- Bottone "Salva" / "Ripristina"

---

## Migrazione Hook Handlers

Tutti i hook handler esistenti vengono aggiornati per usare `PromptTemplateService`:

| Handler | Template type |
|---------|--------------|
| `AutoStartWorkflow` | `workflow` |
| `StartAnalysis` | `workflow` |
| `AutoStartImplementation` | `implementation` |
| `AutoCompletion` | `recap` |

Il campo `auto_workflow_prompt` nelle ProjectSettings rimane come override legacy (viene letto come template di tipo `workflow` se non c'è un record in `prompt_templates`).

---

## Alembic Migrations

Due nuove tabelle:
- `prompt_templates`
- `project_skills`

---

## Built-in Skill Library (contenuto iniziale)

Skills tech: `laravel-12`, `react-19`, `django`, `fastapi`, `nestjs`
Skills domain: `crm`, `saas`, `e-commerce`
Agents: `backend-architect`, `frontend-expert`, `fullstack`

Il contenuto delle skill built-in è curato dal team di Manager AI e versionato in git insieme al codice.

---

## Out of Scope

- Versioning delle skill (storico modifiche)
- Marketplace / import skill da URL esterni
- Skill condivise tra utenti
- Preview live del template con variabili risolte
