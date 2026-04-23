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
