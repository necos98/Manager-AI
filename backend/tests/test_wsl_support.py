import pytest
from app.services.wsl_support import (
    is_wsl_shell,
    win_to_wsl_path,
)


class TestIsWslShell:
    def test_none(self):
        assert is_wsl_shell(None) is False

    def test_empty(self):
        assert is_wsl_shell("") is False

    def test_default_path(self):
        assert is_wsl_shell(r"C:\Windows\System32\wsl.exe") is True

    def test_lowercase(self):
        assert is_wsl_shell(r"c:\windows\system32\wsl.exe") is True

    def test_store_path(self):
        assert is_wsl_shell(r"C:\Program Files\WindowsApps\...\wsl.exe") is True

    def test_cmd_not_wsl(self):
        assert is_wsl_shell(r"C:\Windows\System32\cmd.exe") is False

    def test_bash_not_wsl(self):
        assert is_wsl_shell("/bin/bash") is False


class TestWinToWslPath:
    def test_drive_letter(self):
        assert win_to_wsl_path(r"C:\foo\bar") == "/mnt/c/foo/bar"

    def test_drive_letter_lowercase(self):
        assert win_to_wsl_path(r"d:\x\y") == "/mnt/d/x/y"

    def test_drive_root(self):
        assert win_to_wsl_path("C:\\") == "/mnt/c/"

    def test_unc_wsl_localhost(self):
        assert (
            win_to_wsl_path(r"\\wsl.localhost\Ubuntu\home\u\proj")
            == "/home/u/proj"
        )

    def test_unc_wsl_dollar(self):
        assert (
            win_to_wsl_path(r"\\wsl$\Ubuntu-22.04\home\u\proj")
            == "/home/u/proj"
        )

    def test_posix_passthrough(self):
        assert win_to_wsl_path("/home/user/proj") == "/home/user/proj"

    def test_empty(self):
        assert win_to_wsl_path("") == ""

    def test_unc_wsl_localhost_distro_root_trailing(self):
        assert win_to_wsl_path("\\\\wsl.localhost\\Ubuntu\\") == "/"

    def test_unc_wsl_localhost_distro_root_no_trailing(self):
        assert win_to_wsl_path("\\\\wsl.localhost\\Ubuntu") == "/"

    def test_drive_letter_no_backslash(self):
        # C: alone — treat as drive root
        assert win_to_wsl_path("C:") == "/mnt/c/"
