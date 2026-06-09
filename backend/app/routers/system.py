from __future__ import annotations

import asyncio
import platform

from fastapi import APIRouter, HTTPException

from app.schemas.system import SystemInfoResponse
from app.services.wsl_support import (
    get_default_distro,
    get_host_ip_for_wsl,
    list_wsl_distros,
    wsl_available,
)

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
async def system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        platform=platform.system(),
        wsl_available=wsl_available(),
        distros=list_wsl_distros(),
        default_distro=get_default_distro(),
        host_ip_for_wsl=get_host_ip_for_wsl(),
    )


@router.post("/install-hermes-mcp")
async def install_hermes_mcp() -> dict:
    """Restituisce i comandi per connettere Hermes all'MCP orchestrator.

    Mostra all'utente i comandi da copiare ed eseguire nel terminale.
    """
    import os

    backend_port = os.environ.get("BACKEND_PORT", "8000")
    base_url = f"http://localhost:{backend_port}/mcp/"
    orch_url = f"http://localhost:{backend_port}/mcp-orchestrator/"

    return {
        "success": True,
        "commands": [
            f'hermes mcp add manager-ai-orchestrator --url {orch_url}',
            f'hermes mcp add manager-ai-worker --url {base_url}',
        ],
        "message": (
            f"Esegui questi comandi nel terminale del tuo progetto:\n\n"
            f"  hermes mcp add manager-ai-orchestrator --url {orch_url}\n"
            f"  hermes mcp add manager-ai-worker --url {base_url}\n\n"
            f"Poi riavvia la sessione Hermes per vedere i nuovi tool MCP.\n"
            f"Hermes si connette a /mcp-orchestrator/ ({orch_url}) con 39 tool di orchestrazione e amministrazione.\n"
            f"Hermes si connette a /mcp/ ({base_url}) con 37 tool worker per spawn auto-mode (run-issue, pipeline, ecc.)."
        ),
    }


@router.post("/install-hermes-skills")
async def install_hermes_skills() -> dict:
    """Installa globalmente le skill Hermes in ~/.hermes/skills/.

    Copia hermes_skills/manager-ai-orchestrator e
    hermes_skills/manager-ai-issue-worker nella directory
    globale delle skill Hermes.
    """
    import os
    import shutil

    src = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "hermes_skills",
    )
    if not os.path.isdir(src):
        raise HTTPException(status_code=404, detail="hermes_skills folder not found")

    hermes_home = os.environ.get(
        "HERMES_HOME",
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes"),
    )
    hermes_skills_dir = os.path.join(hermes_home, "skills", "autonomous-ai-agents")
    os.makedirs(hermes_skills_dir, exist_ok=True)

    skill_names = [
        "manager-ai-orchestrator",
        "manager-ai-issue-worker",
        "run-issue",
        "run-pipeline",
        "ask-and-brainstorm",
        "manage-agent",
    ]
    copied = []

    for name in skill_names:
        s = os.path.join(src, name)
        if not os.path.isdir(s):
            copied.append({"name": name, "status": "skipped", "reason": "source not found"})
            continue
        d = os.path.join(hermes_skills_dir, name)
        if os.path.isdir(d):
            # Aggiorna SKILL.md esistente
            shutil.copy2(os.path.join(s, "SKILL.md"), os.path.join(d, "SKILL.md"))
            copied.append({"name": name, "status": "updated"})
        else:
            shutil.copytree(s, d)
            copied.append({"name": name, "status": "installed"})

    # Copia anche AGENTS.md come riferimento
    agents_md_src = os.path.join(src, "AGENTS.md")
    if os.path.isfile(agents_md_src):
        shutil.copy2(agents_md_src, hermes_skills_dir)
        copied.append({"name": "AGENTS.md", "status": "installed"})

    return {
        "success": True,
        "copied": copied,
        "path": hermes_skills_dir,
        "message": (
            f"Skill installate in {hermes_skills_dir}. "
            "Riavvia Hermes o esegui /reload-skills per usarle."
        ),
    }


@router.get("/agent-providers")
async def list_agent_providers():
    from app.providers.registry import AgentProviderRegistry

    return AgentProviderRegistry.available()
