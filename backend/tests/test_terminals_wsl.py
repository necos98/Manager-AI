import pytest
from unittest.mock import MagicMock, patch

from app.routers.terminals import _inject_env_vars, _inject_wsl_mcp_registration


def test_inject_env_vars_wsl_uses_export():
    pty = MagicMock()
    _inject_env_vars(pty, {"A": "1", "B": "2"}, is_wsl=True)
    pty.write.assert_called_once()
    written = pty.write.call_args.args[0]
    assert "export A=1" in written
    assert "export B=2" in written
    assert "set " not in written


def test_inject_env_vars_windows_non_wsl_uses_set():
    pty = MagicMock()
    with patch("app.routers.terminals.platform.system", return_value="Windows"):
        _inject_env_vars(pty, {"A": "1"}, is_wsl=False)
    written = pty.write.call_args.args[0]
    assert "set A=1" in written


def test_inject_env_vars_linux_host_uses_export():
    pty = MagicMock()
    with patch("app.routers.terminals.platform.system", return_value="Linux"):
        _inject_env_vars(pty, {"A": "1"}, is_wsl=False)
    written = pty.write.call_args.args[0]
    assert "export A=1" in written


def test_inject_env_vars_wsl_quotes_values_with_spaces():
    pty = MagicMock()
    _inject_env_vars(pty, {"GREETING": "hello world", "SAFE": "x"}, is_wsl=True)
    written = pty.write.call_args.args[0]
    # Spaces must be quoted so bash sees one argument per export
    assert "export GREETING='hello world'" in written
    assert "export SAFE=x" in written


def test_inject_env_vars_wsl_quotes_shell_metacharacters():
    pty = MagicMock()
    _inject_env_vars(pty, {"X": "a;b`c$d"}, is_wsl=True)
    written = pty.write.call_args.args[0]
    # No literal command separator or subshell leaks through
    assert "a;b`c$d" not in written.replace("'a;b`c$d'", "")
    # Quoted value round-trips through shlex
    import shlex
    assert shlex.split(written[len("export X="):])[0] == "a;b`c$d"


def test_inject_wsl_mcp_registration_is_idempotent_and_silent():
    pty = MagicMock()
    _inject_wsl_mcp_registration(pty)
    written = pty.write.call_args.args[0]
    # Guard so first-run (no claude installed) is a silent no-op
    assert "command -v claude" in written
    # Remove before add so a changed WSL gateway IP re-syncs the registration
    assert "claude mcp remove ManagerAi" in written
    assert "claude mcp add ManagerAi" in written
    # URL comes from the exported env var, not a hardcoded localhost
    assert '"$MANAGER_AI_BASE_URL/mcp/"' in written
    # Output suppressed so the user's prompt stays clean
    assert ">/dev/null 2>&1" in written


def _make_fake_pty(spawns):
    class FakePTY:
        def __init__(self, *a, **k): pass
        def spawn(self, appname, cmdline=None, cwd=None, env=None):
            spawns.append({"appname": appname, "cmdline": cmdline, "cwd": cwd})
        def write(self, *a, **k): pass
        def close(self): pass
        def read(self, blocking=True): return ""
        def set_size(self, *a, **k): pass
    return FakePTY


def test_service_create_appends_distro(monkeypatch):
    from app.services import terminal_service as ts
    spawns = []
    monkeypatch.setattr(ts, "PTY", _make_fake_pty(spawns))
    svc = ts.TerminalService()
    svc.create(
        issue_id="i", project_id="p", project_path="C:\\x",
        shell=r"C:\Windows\System32\wsl.exe",
        wsl_distro="Ubuntu-22.04",
    )
    spawn = spawns[-1]
    # pywinpty concatenates appname + cmdline; passing cmdline with an argv[0]
    # causes wsl.exe to re-run itself inside bash. Everything must live in appname.
    assert spawn["cmdline"] is None
    assert "-d Ubuntu-22.04" in spawn["appname"]
    assert "wsl.exe" in spawn["appname"].lower()
    # WSL shells must not receive a Windows cwd — UNC project paths would make
    # CreateProcess fail, and the router emits `cd` inside bash anyway.
    assert spawn["cwd"] is None


def test_service_create_unc_path_does_not_leak_to_spawn(monkeypatch):
    """UNC project paths must never reach winpty as cwd."""
    from app.services import terminal_service as ts
    spawns = []
    monkeypatch.setattr(ts, "PTY", _make_fake_pty(spawns))
    svc = ts.TerminalService()
    svc.create(
        issue_id="i", project_id="p",
        project_path=r"\\wsl.localhost\Ubuntu-22.04\home\u\proj",
        shell=r"C:\Windows\System32\wsl.exe",
    )
    assert spawns[-1]["cwd"] is None


def test_service_create_non_wsl_keeps_cwd(monkeypatch):
    """Non-WSL shells still receive the project_path as cwd."""
    from app.services import terminal_service as ts
    spawns = []
    monkeypatch.setattr(ts, "PTY", _make_fake_pty(spawns))
    svc = ts.TerminalService()
    svc.create(
        issue_id="i", project_id="p", project_path=r"C:\dev\proj",
        shell=r"C:\Windows\System32\cmd.exe",
    )
    assert spawns[-1]["cwd"] == r"C:\dev\proj"


def test_service_create_rejects_injection(monkeypatch):
    from app.services import terminal_service as ts
    monkeypatch.setattr(ts, "PTY", _make_fake_pty([]))
    svc = ts.TerminalService()
    with pytest.raises(ValueError):
        svc.create(
            issue_id="i", project_id="p", project_path="C:\\x",
            shell=r"C:\Windows\System32\wsl.exe",
            wsl_distro="foo; rm -rf /",
        )


def test_service_create_ignores_distro_for_non_wsl_shell(monkeypatch):
    """wsl_distro set on a non-WSL shell must be silently ignored, not rejected."""
    from app.services import terminal_service as ts
    spawns = []
    monkeypatch.setattr(ts, "PTY", _make_fake_pty(spawns))
    svc = ts.TerminalService()
    # Even a value that would fail the regex must not raise when shell is cmd.exe
    svc.create(
        issue_id="i", project_id="p", project_path="C:\\x",
        shell=r"C:\Windows\System32\cmd.exe",
        wsl_distro="foo; rm -rf /",
    )
    spawn = spawns[-1]
    assert spawn["appname"].lower().endswith("cmd.exe")
    assert spawn["cmdline"] is None
