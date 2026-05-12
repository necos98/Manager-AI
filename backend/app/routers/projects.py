import json
import logging
import os
import shlex
import shutil

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.project import DashboardProject, ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.terminal import TerminalResponse
from app.services.project_service import ProjectService
from app.services.terminal_service import terminal_service
from app.services.wsl_support import is_wsl_shell, win_to_wsl_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _claude_resources_source() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "claude_resources",
    )


def _check_manager_json(project) -> dict:
    path = os.path.join(project.path, "manager.json")
    if not os.path.isfile(path):
        return {"installed": False, "path": path}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        installed = data.get("project_id") == project.id
    except Exception:
        installed = False
    return {"installed": installed, "path": path}


def _check_claude_resources(project) -> dict:
    dest = os.path.join(project.path, ".claude")
    src = _claude_resources_source()
    if not os.path.isdir(src):
        return {"installed": False, "path": dest, "missing": []}
    expected = [i for i in os.listdir(src) if not i.startswith(".")]
    if not os.path.isdir(dest):
        return {"installed": False, "path": dest, "missing": expected}
    missing = [i for i in expected if not os.path.exists(os.path.join(dest, i))]
    return {"installed": len(missing) == 0, "path": dest, "missing": missing}


def _check_mcp(project) -> dict:
    project_mcp = os.path.join(project.path, ".mcp.json")
    if os.path.isfile(project_mcp):
        try:
            with open(project_mcp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "ManagerAi" in (data.get("mcpServers") or {}):
                return {"installed": True, "location": project_mcp}
        except Exception:
            pass

    home_cfg = os.path.join(os.path.expanduser("~"), ".claude.json")
    if os.path.isfile(home_cfg):
        try:
            with open(home_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "ManagerAi" in (data.get("mcpServers") or {}):
                return {"installed": True, "location": home_cfg}
            norm = os.path.normpath(project.path).lower()
            for key, val in (data.get("projects") or {}).items():
                if os.path.normpath(key).lower() == norm and "ManagerAi" in (val.get("mcpServers") or {}):
                    return {"installed": True, "location": home_cfg}
        except Exception:
            pass
    return {"installed": False, "location": None}


def _check_playwright_mcp(project) -> dict:
    project_mcp = os.path.join(project.path, ".mcp.json")
    if os.path.isfile(project_mcp):
        try:
            with open(project_mcp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "Playwright" in (data.get("mcpServers") or {}):
                return {"installed": True, "location": project_mcp}
        except Exception:
            pass

    home_cfg = os.path.join(os.path.expanduser("~"), ".claude.json")
    if os.path.isfile(home_cfg):
        try:
            with open(home_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "Playwright" in (data.get("mcpServers") or {}):
                return {"installed": True, "location": home_cfg}
            norm = os.path.normpath(project.path).lower()
            for key, val in (data.get("projects") or {}).items():
                if os.path.normpath(key).lower() == norm and "Playwright" in (val.get("mcpServers") or {}):
                    return {"installed": True, "location": home_cfg}
        except Exception:
            pass
    return {"installed": False, "location": None}


def _check_resource_consistency(project) -> dict:
    """Scan all .manager_ai/ YAML files for project_id mismatches and auto-fix them.

    Authority is manager.json. Resources checked:
      - issues.yaml (index)
      - .manager_ai/issues/<id>/issue.yaml (individual)
      - memories.yaml (index)
      - .manager_ai/memories/<id>.md (frontmatter)
    """
    mgr_json = os.path.join(project.path, "manager.json")
    if not os.path.isfile(mgr_json):
        return {"ok": None, "scanned": 0, "fixed": 0, "details": [], "note": "manager.json missing"}
    try:
        with open(mgr_json, "r", encoding="utf-8") as f:
            auth_id = json.load(f).get("project_id")
    except Exception:
        return {"ok": None, "scanned": 0, "fixed": 0, "details": [], "note": "manager.json unreadable"}
    if not auth_id:
        return {"ok": None, "scanned": 0, "fixed": 0, "details": [], "note": "manager.json missing project_id"}

    mgr_dir = os.path.join(project.path, ".manager_ai")
    scanned = 0
    fixed = 0
    details = []

    def _fix_yaml_file(filepath, entries_key):
        nonlocal scanned, fixed
        if not os.path.isfile(filepath):
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return
        entries = data.get(entries_key, [])
        if not isinstance(entries, list):
            return
        changed = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            scanned += 1
            if entry.get("project_id") != auth_id:
                entry["project_id"] = auth_id
                changed = True
                fixed += 1
                details.append({
                    "resource_id": entry.get("id"),
                    "resource_type": entries_key,
                    "file": os.path.relpath(filepath, project.path),
                })
        if changed:
            tmp = filepath + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=4096)
            os.replace(tmp, filepath)

    def _fix_issue_files():
        nonlocal scanned, fixed
        issues_dir = os.path.join(mgr_dir, "issues")
        if not os.path.isdir(issues_dir):
            return
        for name in os.listdir(issues_dir):
            filepath = os.path.join(issues_dir, name, "issue.yaml")
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            scanned += 1
            if data.get("project_id") != auth_id:
                data["project_id"] = auth_id
                fixed += 1
                details.append({
                    "resource_id": data.get("id"),
                    "resource_type": "issue",
                    "file": os.path.relpath(filepath, project.path),
                })
                tmp = filepath + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=4096)
                os.replace(tmp, filepath)

    def _fix_memory_md_files():
        nonlocal scanned, fixed
        mem_dir = os.path.join(mgr_dir, "memories")
        if not os.path.isdir(mem_dir):
            return
        for name in os.listdir(mem_dir):
            if not name.endswith(".md"):
                continue
            filepath = os.path.join(mem_dir, name)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                continue
            if not raw.startswith("---"):
                continue
            parts = raw.split("---", 2)
            if len(parts) < 3:
                continue
            frontmatter = parts[1]
            try:
                fm = yaml.safe_load(frontmatter) or {}
            except Exception:
                continue
            if not isinstance(fm, dict):
                continue
            scanned += 1
            if fm.get("project_id") != auth_id:
                fm["project_id"] = auth_id
                fixed += 1
                details.append({
                    "resource_id": fm.get("id"),
                    "resource_type": "memory",
                    "file": os.path.relpath(filepath, project.path),
                })
                new_fm = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=4096).rstrip()
                new_raw = "---\n" + new_fm + "\n---" + parts[2]
                tmp = filepath + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(new_raw)
                os.replace(tmp, filepath)

    _fix_yaml_file(os.path.join(mgr_dir, "issues.yaml"), "issues")
    _fix_issue_files()
    _fix_yaml_file(os.path.join(mgr_dir, "memories.yaml"), "memories")
    _fix_memory_md_files()

    return {"ok": fixed == 0, "scanned": scanned, "fixed": fixed, "details": details}


async def _enrich_project(service: ProjectService, project) -> dict:
    """Add issue_counts to a project response."""
    counts = await service.get_issue_counts(project.id)
    result = ProjectResponse.model_validate(project)
    result.issue_counts = counts
    return result


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description,
        tech_stack=data.tech_stack, shell=data.shell
    )
    await db.commit()
    return await _enrich_project(service, project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(archived: bool = False, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    projects = await service.list_all(archived=archived)
    return [await _enrich_project(service, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    return await _enrich_project(service, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update(project_id, **data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.archive(project_id)
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.unarchive(project_id)
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    # Validate project exists (raises NotFoundError if not)
    await service.get_by_id(project_id)
    # Kill active terminals for this project
    for term in terminal_service.list_active(project_id=project_id):
        try:
            terminal_service.kill(term["id"])
        except KeyError:
            pass
    await service.delete(project_id)
    await db.commit()


def _require_valid_project_dir(project) -> None:
    if not os.path.isabs(project.path):
        raise HTTPException(
            status_code=400,
            detail=f"Project path is not absolute: {project.path!r}. Update project path.",
        )
    if not os.path.isdir(project.path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project.path}")


@router.post("/{project_id}/install-manager-json", status_code=200)
async def install_manager_json(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    _require_valid_project_dir(project)
    dest = os.path.join(project.path, "manager.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"project_id": project.id}, f, indent=2)
    return {"path": dest}


@router.post("/{project_id}/install-claude-resources", status_code=200)
async def install_claude_resources(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    _require_valid_project_dir(project)

    src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "claude_resources")
    if not os.path.isdir(src):
        raise HTTPException(status_code=404, detail="claude_resources folder not found")

    dest = os.path.join(project.path, ".claude")
    os.makedirs(dest, exist_ok=True)

    copied = []
    for item in os.listdir(src):
        if item.startswith("."):
            continue
        s = os.path.join(src, item)
        d = os.path.join(dest, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
        copied.append(item)

    return {"path": dest, "copied": copied}


@router.get("/{project_id}/health")
async def project_health(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    return {
        "manager_json": _check_manager_json(project),
        "claude_resources": _check_claude_resources(project),
        "mcp": _check_mcp(project),
        "playwright_mcp": _check_playwright_mcp(project),
        "resource_consistency": _check_resource_consistency(project),
    }


@router.post("/{project_id}/install-mcp", response_model=TerminalResponse, status_code=201)
async def install_mcp(project_id: str, db: AsyncSession = Depends(get_db)):
    """Spawn a terminal and re-register the Manager AI MCP server.

    Idempotent: runs `claude mcp remove ManagerAi` before `claude mcp add`
    so the caller can use this as both "install" and "reinstall". When the
    project shell is wsl.exe, the URL resolves at runtime from the WSL2
    gateway IP; otherwise it uses localhost.
    """
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if not os.path.isdir(project.path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project.path}")

    try:
        terminal = terminal_service.create(
            issue_id="",
            project_id=project_id,
            project_path=project.path,
            shell=project.shell,
            wsl_distro=project.wsl_distro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    port = int(os.environ.get("BACKEND_PORT") or settings.backend_port)
    is_wsl = is_wsl_shell(project.shell)

    try:
        pty = terminal_service.get_pty(terminal["id"])
        if is_wsl:
            cwd = win_to_wsl_path(project.path)
            url = f'"http://localhost:{port}/mcp/"'
            pty.write(f"cd {shlex.quote(cwd)}\r\n")
            pty.write(
                "claude mcp remove ManagerAi 2>/dev/null; "
                f"claude mcp add ManagerAi --transport http {url}\r\n"
            )
        else:
            url = f"http://localhost:{port}/mcp/"
            pty.write(
                "claude mcp remove ManagerAi 2>nul & "
                f"claude mcp add ManagerAi --transport http {url}\r\n"
            )
    except Exception:
        logger.warning("Failed to write install-mcp command for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)


@router.post("/{project_id}/install-playwright-mcp", response_model=TerminalResponse, status_code=201)
async def install_playwright_mcp(project_id: str, db: AsyncSession = Depends(get_db)):
    """Spawn a terminal and re-register the Playwright MCP server.

    Idempotent: runs `claude mcp remove Playwright` before `claude mcp add`.
    When the project shell is wsl.exe, the URL resolves at runtime from the WSL2
    gateway IP; otherwise it uses localhost.
    """
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if not os.path.isdir(project.path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project.path}")

    try:
        terminal = terminal_service.create(
            issue_id="",
            project_id=project_id,
            project_path=project.path,
            shell=project.shell,
            wsl_distro=project.wsl_distro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    is_wsl = is_wsl_shell(project.shell)

    try:
        pty = terminal_service.get_pty(terminal["id"])
        if is_wsl:
            cwd = win_to_wsl_path(project.path)
            pty.write(f"cd {shlex.quote(cwd)}\r\n")
            pty.write(
                "claude mcp remove Playwright 2>/dev/null; "
                "claude mcp add Playwright -- npx @playwright/mcp@latest\r\n"
            )
        else:
            pty.write(
                "claude mcp remove Playwright 2>nul & "
                "claude mcp add Playwright -- npx @playwright/mcp@latest\r\n"
            )
    except Exception:
        logger.warning("Failed to write install-playwright-mcp command for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)


dashboard_router = APIRouter(tags=["dashboard"])


@dashboard_router.get("/api/dashboard", response_model=list[DashboardProject])
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    svc = ProjectService(db)
    return await svc.get_dashboard_data()
