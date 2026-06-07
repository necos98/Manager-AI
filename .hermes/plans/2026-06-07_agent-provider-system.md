# Agent Provider System — Implementation Plan

> **Goal:** Abstract le invocazioni cablate di `claude` dietro un'interfaccia `AgentProvider`, permettendo di switchare tra provider (Claude Code, Hermes, etc.) senza cambiare la logica di negocio.

**Architecture:** Ogni provider implementa un'ABC che genera i comandi corretti per ogni scenario (run-issue, run-pipeline, ask-brainstorm, manage-agent, hook). Un Registry mappa nome → classe. Il provider attivo viene letto da un setting `agent_provider` in `default_settings.json`.

**Tech Stack:** Python ABC, FastAPI settings, asyncio

**Branch:** `feature/agent-provider-system` (git worktree)

---

## Fasi

### Fase 1 — Package `providers/` + ClaudeProvider + Registry

Creare la struttura base: interfaccia, implementazione Claude, registry.

**Files:**
- Create: `backend/app/providers/__init__.py`
- Create: `backend/app/providers/base.py` — ABC
- Create: `backend/app/providers/claude_provider.py` — ClaudeProvider
- Create: `backend/app/providers/registry.py` — AgentProviderRegistry

### Fase 2 — Refactor `pipeline_run_service.py` (2 punti)

Sostituire le stringhe cablate con chiamate al provider.

**Files:**
- Modify: `backend/app/services/pipeline_run_service.py` (linee 568, 888)

### Fase 3 — Refactor `terminal_operations.py` (2 punti)

Sostituire la logica ad-hoc di `create_ask_terminal` e `create_manage_agent_terminal`.

**Files:**
- Modify: `backend/app/services/terminal_operations.py` (linee ~204-216, ~308-319)

### Fase 4 — Refactor `enrich_context.py` hook (1 punto)

Sostituire il comando cablato nell'hook.

**Files:**
- Modify: `backend/app/hooks/handlers/enrich_context.py`

### Fase 5 — Setting `agent_provider` + test

Aggiungere il setting di default e testare tutto.

**Files:**
- Modify: `backend/app/mcp/default_settings.json`
- Create/Modify: `backend/tests/test_agent_providers.py`

### Fase 6 — HermesProvider (opzionale, solo se voluto)

Implementare il provider per Hermes Agent.

**Files:**
- Create: `backend/app/providers/hermes_provider.py`

---

## Dettaglio Task

### Task 1: Creare package `providers/` con ABC

**Objective:** Definire l'interfaccia astratta che ogni provider deve implementare.

**Files:**
- Create: `backend/app/providers/__init__.py`
- Create: `backend/app/providers/base.py`

**`backend/app/providers/__init__.py`:**
```python
```

**`backend/app/providers/base.py`:**
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class AgentProvider(ABC):
    """Interfaccia per provider di coding agent CLI.

    Ogni provider (Claude Code, Hermes, etc.) implementa questi metodi
    per generare i comandi corretti per ogni scenario di spawn.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome univoco del provider (es. 'claude', 'hermes')."""
        ...

    @abstractmethod
    def build_run_issue_command(self, issue_id: str) -> str:
        """Comando per eseguire una issue (scritto nel PTY del terminale).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/run-issue abc-123"
        """
        ...

    @abstractmethod
    def build_run_pipeline_command(self, issue_id: str) -> str:
        """Comando per eseguire uno step di pipeline (scritto nel PTY).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/run-pipeline abc-123"
        """
        ...

    @abstractmethod
    def build_ask_brainstorm_command(self, project_id: str) -> str:
        """Comando per Ask & Brainstorm (scritto nel PTY).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/ask-and-brainstorm proj-1"
        """
        ...

    @abstractmethod
    def build_manage_agent_command(self, intent: str = "") -> str:
        """Comando per Manage Agent (scritto nel PTY).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/manage-agent"
        Se intent è fornito, viene aggiunto come argomento finale.
        """
        ...

    @abstractmethod
    def build_hook_command(
        self, prompt: str, tool_guidance: str = ""
    ) -> list[str]:
        """Comando per hook subprocess (ritorna lista args per
        asyncio.create_subprocess_exec).

        Esempio output (Claude):
          ["claude", "-p", prompt, "--output-format", "text"]
        """
        ...
```

**Test:**
- Verificare che l'ABC abbia tutti i metodi astratti
- Verificare che istanziare AgentProvider dia TypeError

### Task 2: ClaudeProvider

**Objective:** Implementare il provider per Claude Code, che riproduce esattamente i comandi attuali.

**Files:**
- Create: `backend/app/providers/claude_provider.py`

```python
from __future__ import annotations

import shlex

from app.providers.base import AgentProvider


class ClaudeProvider(AgentProvider):
    """Provider per Claude Code CLI.

    Genera comandi con il formato attuale:
      claude --dangerously-skip-permissions "/<modalità> <args>"
    """

    @property
    def name(self) -> str:
        return "claude"

    def build_run_issue_command(self, issue_id: str) -> str:
        return (
            f"claude --dangerously-skip-permissions "
            f"\"/run-issue {shlex.quote(issue_id)}\""
        )

    def build_run_pipeline_command(self, issue_id: str) -> str:
        return (
            f"claude --dangerously-skip-permissions "
            f"\"/run-pipeline {shlex.quote(issue_id)}\""
        )

    def build_ask_brainstorm_command(self, project_id: str) -> str:
        return (
            f"claude --dangerously-skip-permissions "
            f"\"/ask-and-brainstorm {shlex.quote(project_id)}\""
        )

    def build_manage_agent_command(self, intent: str = "") -> str:
        base = (
            "claude --dangerously-skip-permissions "
            "\"/manage-agent\""
        )
        if intent:
            base += f" {shlex.quote(intent)}"
        return base

    def build_hook_command(
        self, prompt: str, tool_guidance: str = ""
    ) -> list[str]:
        cmd = ["claude", "-p", prompt]
        if tool_guidance:
            cmd += ["--append-system-prompt", tool_guidance]
        cmd += ["--output-format", "text"]
        return cmd
```

**Test:**
```python
def test_claude_provider_commands():
    p = ClaudeProvider()
    assert "claude" in p.build_run_issue_command("iss-1")
    assert "/run-issue iss-1" in p.build_run_issue_command("iss-1")
    assert p.build_hook_command("test") == ["claude", "-p", "test", "--output-format", "text"]
```

### Task 3: AgentProviderRegistry

**Objective:** Registry che permette di registrare e ottenere provider per nome.

**Files:**
- Create: `backend/app/providers/registry.py`

```python
from __future__ import annotations

from app.providers.base import AgentProvider
from app.providers.claude_provider import ClaudeProvider


class AgentProviderRegistry:
    """Registry dei provider disponibili.

    Uso:
        provider = AgentProviderRegistry.get("claude")
        cmd = provider.build_run_pipeline_command("iss-1")
    """

    _providers: dict[str, type[AgentProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[AgentProvider]) -> None:
        if not issubclass(provider_cls, AgentProvider):
            raise TypeError(
                f"{provider_cls.__name__} must subclass AgentProvider"
            )
        cls._providers[name] = provider_cls

    @classmethod
    def get(cls, name: str) -> AgentProvider:
        if name not in cls._providers:
            raise KeyError(
                f"Unknown agent provider: {name!r}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[name]()

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._providers.keys())


def register_builtin_providers() -> None:
    """Registra i provider built-in (chiamato all'avvio)."""
    AgentProviderRegistry.register("claude", ClaudeProvider)


# Auto-register built-in providers on import
register_builtin_providers()
```

**Test:**
```python
def test_register_get():
    p = AgentProviderRegistry.get("claude")
    assert p.name == "claude"
```

### Task 4: Refactor `pipeline_run_service._run_step`

**Objective:** Sostituire `claude --dangerously-skip-permissions "/run-pipeline {issue_id}"` con chiamata al provider.

**Changes in** `backend/app/services/pipeline_run_service.py` ~linea 568:

PRIMA:
```python
command = f'claude --dangerously-skip-permissions "/run-pipeline {issue_id}"'
```

DOPO:
```python
from app.providers.registry import AgentProviderRegistry

provider = AgentProviderRegistry.get("claude")
command = provider.build_run_pipeline_command(issue_id)
```

### Task 5: Refactor `pipeline_run_service.start_step`

**Objective:** Stessa sostituzione nel metodo `start_step` (linea ~888).

PRIMA:
```python
command = f'claude --dangerously-skip-permissions "/run-pipeline {run.issue_id}"'
```

DOPO:
```python
provider = AgentProviderRegistry.get("claude")
command = provider.build_run_pipeline_command(run.issue_id)
```

### Task 6: Refactor `create_ask_terminal`

**Objective:** Sostituire la logica ad-hoc di `ask_brainstorm_command` + `claude.skip_permissions` con chiamata al provider e risoluzione variabili dopo.

**Changes in** `backend/app/services/terminal_operations.py` ~linee 204-216:

PRIMA:
```python
cmd = await settings_svc.get("ask_brainstorm_command")
skip_perms = (
    await settings_svc.get("claude.skip_permissions") == "true"
)
if skip_perms and cmd.startswith("claude "):
    cmd = (
        "claude --dangerously-skip-permissions "
        + cmd[len("claude ") :]
    )
```

DOPO:
```python
provider_name = await settings_svc.get("agent_provider")
provider = AgentProviderRegistry.get(provider_name)
cmd = provider.build_ask_brainstorm_command(data.project_id)
```

NOTA: La risoluzione delle variabili (`$project_id`, `$project_path`) avviene DOPO, nel blocco esistente. Il provider produce il comando base; le variabili vengono risolte dal chiamante.

### Task 7: Refactor `create_manage_agent_terminal`

**Objective:** Stessa logica per `manage_agent_command`.

**Changes in** `backend/app/services/terminal_operations.py` ~linee 308-319:

PRIMA:
```python
cmd = await settings_svc.get("manage_agent_command")
skip_perms = (
    await settings_svc.get("claude.skip_permissions") == "true"
)
if skip_perms and cmd.startswith("claude "):
    cmd = (
        "claude --dangerously-skip-permissions "
        + cmd[len("claude ") :]
    )
if data.agent_id and agent_intent:
    cmd += f' "{agent_intent}"'
```

DOPO:
```python
provider_name = await settings_svc.get("agent_provider")
provider = AgentProviderRegistry.get(provider_name)
cmd = provider.build_manage_agent_command(
    agent_intent if data.agent_id else ""
)
```

### Task 8: Refactor `enrich_context` hook

**Objective:** Sostituire `["claude", "-p", prompt]` con chiamata al provider.

**Changes in** `backend/app/hooks/handlers/enrich_context.py` ~linea 53:

PRIMA:
```python
cmd = ["claude", "-p", prompt]
if tool_guidance:
    cmd += ["--append-system-prompt", tool_guidance]
cmd += ["--output-format", "text"]
```

DOPO:
```python
from app.providers.registry import AgentProviderRegistry

provider = AgentProviderRegistry.get("claude")
cmd = provider.build_hook_command(prompt, tool_guidance)
```

NOTA: L'hook non ha accesso al DB, quindi per ora usiamo `"claude"` hardcoded. In futuro si può rendere configurabile via env var o setting globale.

### Task 9: Aggiungere setting `agent_provider`

**Objective:** Aggiungere il setting di default per selezionare il provider attivo.

**Changes in** `backend/app/mcp/default_settings.json`:
```json
"agent_provider": "claude",
```

Rimuovere `"claude.skip_permissions": "false"` — non più necessario (ogni provider sa quali flags usare).

### Task 10: Test completi

**Files:**
- Create: `backend/tests/test_agent_providers.py`

Test da includere:
1. `test_claude_provider_run_issue_command` — formato corretto
2. `test_claude_provider_run_pipeline_command` — formato corretto
3. `test_claude_provider_ask_brainstorm_command` — formato corretto
4. `test_claude_provider_manage_agent_no_intent` — senza intent
5. `test_claude_provider_manage_agent_with_intent` — con intent
6. `test_claude_provider_hook_command` — formato lista per subprocess
7. `test_claude_provider_hook_command_with_guidance` — con tool_guidance
8. `test_register_invalid_provider` — TypeError se non sottoclasse ABC
9. `test_get_unknown_provider` — KeyError con messaggio utile
10. `test_available_providers` — lista dei provider registrati

---

## Rischi e Tradeoff

1. **Retrocompatibilità**: `ask_brainstorm_command` e `manage_agent_command` settings rimangono in `default_settings.json` ma non vengono più usati dal codice se `agent_provider` è impostato. Si possono deprecare in una fase successiva.

2. **Hook senza DB**: `enrich_context.py` non ha accesso a `AsyncSession`, quindi il provider è hardcoded a `"claude"`. In futuro si può risolvere con un setting globale accessibile senza DB.

3. **shlex.quote**: I provider che generano comandi per PTY (stringhe) devono usare `shlex.quote()` per i parametri. I provider che generano liste per subprocess no — è responsabilità del chiamante.

4. **Provider diversi per step di pipeline**: Attualmente non supportato, ma l'architettura lo permetterebbe aggiungendo un campo `provider` sull'agente/pipeline.

---

## Verifica Finale

Dopo tutte le fasi:

```bash
cd backend
python -m pytest tests/test_agent_providers.py -v
python -m pytest tests/test_pipeline_run_service.py -v -x
python -m pytest tests/test_terminal_service.py -v -x
python -m pytest tests/test_terminal_router.py -v -x
python -m pytest tests/test_terminal_command_service.py -v -x
python -m pytest tests/test_ask_terminal.py -v -x
python -m pytest tests/test_terminal_operations.py -v -x  # se esiste
```

(Alcuni test potrebbero non esistere ancora — verificare con `search_files`)
