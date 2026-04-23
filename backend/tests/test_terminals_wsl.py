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
