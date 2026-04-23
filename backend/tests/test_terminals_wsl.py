import pytest
from unittest.mock import MagicMock, patch

from app.routers.terminals import _inject_env_vars


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
    assert spawn["appname"].lower().endswith("wsl.exe")
    assert "-d Ubuntu-22.04" in spawn["cmdline"]
    assert "wsl.exe" in spawn["cmdline"]


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
