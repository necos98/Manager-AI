from __future__ import annotations

import asyncio
import platform

from fastapi import APIRouter

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
    """Esegue 'hermes mcp add manager-ai' per connettere Hermes all'MCP server.

    Spawna un subprocess che viene killato dopo l'esecuzione.
    Restituisce stdout, stderr e codice di uscita.
    """
    import os

    base_url = "http://localhost:8000/mcp"

    cmd = [
        "hermes", "mcp", "add", "manager-ai",
        "--url", base_url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=b"n\ny\ny\n"), timeout=30
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "success": False,
                "error": "Timeout dopo 30 secondi. Assicurati che Hermes sia nel PATH.",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }

        exit_code = proc.returncode
        stdout_text = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
        stderr_text = stderr.decode("utf-8", errors="replace").strip() if stderr else ""

        if exit_code == 0:
            return {
                "success": True,
                "message": "Hermes MCP connesso con successo! "
                          "Riavvia la sessione Hermes per vedere i nuovi tool MCP.",
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": exit_code,
            }
        else:
            error_msg = stderr_text or stdout_text or f"Exit code: {exit_code}"
            return {
                "success": False,
                "error": f"Comando fallito: {error_msg}",
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": exit_code,
            }

    except FileNotFoundError:
        return {
            "success": False,
            "error": "Hermes non trovato nel PATH. "
                     "Assicurati che 'hermes' sia installato e accessibile dal terminale.",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Errore imprevisto: {e}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
