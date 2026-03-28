from __future__ import annotations

import os
import platform
import threading
import uuid
from datetime import datetime, timezone

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    from winpty import PTY

    DEFAULT_SHELL = os.environ.get("MANAGER_AI_SHELL", r"C:\Windows\System32\cmd.exe")
else:
    import fcntl
    import pty as pty_mod
    import select
    import struct
    import subprocess
    import termios

    DEFAULT_SHELL = os.environ.get("MANAGER_AI_SHELL", "/bin/bash")

    class PTY:
        """Linux PTY wrapper matching the winpty API."""

        def __init__(self, cols: int = 120, rows: int = 30):
            self._master_fd: int | None = None
            self._process: subprocess.Popen | None = None
            self._cols = cols
            self._rows = rows

        def spawn(self, shell: str, cwd: str | None = None) -> None:
            master_fd, slave_fd = pty_mod.openpty()
            # Set initial size
            winsize = struct.pack("HHHH", self._rows, self._cols, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
            self._master_fd = master_fd
            self._process = subprocess.Popen(
                [shell],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=cwd,
                preexec_fn=os.setsid,
            )
            os.close(slave_fd)

        def read(self, blocking: bool = True) -> str:
            if self._master_fd is None:
                return ""
            if not blocking:
                ready, _, _ = select.select([self._master_fd], [], [], 0)
                if not ready:
                    return ""
            try:
                data = os.read(self._master_fd, 4096)
                if not data:
                    return ""
                return data.decode("utf-8", errors="replace")
            except OSError:
                return ""

        def write(self, data: str) -> None:
            if self._master_fd is not None:
                os.write(self._master_fd, data.encode("utf-8"))

        def set_size(self, cols: int, rows: int) -> None:
            self._cols = cols
            self._rows = rows
            if self._master_fd is not None:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)

        def close(self) -> None:
            if self._master_fd is not None:
                try:
                    os.close(self._master_fd)
                except OSError:
                    pass
                self._master_fd = None
            if self._process is not None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=3)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                self._process = None

# Maximum size of the output buffer per terminal (in bytes).
# When exceeded, oldest output is trimmed from the front.
MAX_BUFFER_SIZE = 100_000  # ~100 KB


class TerminalService:
    """In-memory registry of active terminal sessions with PTY lifecycle management."""

    def __init__(self):
        self._terminals: dict[str, dict] = {}
        self._buffers: dict[str, bytearray] = {}
        self._lock = threading.Lock()

    def create(
        self,
        issue_id: str,
        project_id: str,
        project_path: str,
        cols: int = 120,
        rows: int = 30,
        shell: str | None = None,
    ) -> dict:
        shell_to_use = shell or DEFAULT_SHELL

        pty = PTY(cols, rows)
        pty.spawn(shell_to_use, cwd=project_path)

        term_id = str(uuid.uuid4())
        entry = {
            "id": term_id,
            "issue_id": issue_id,
            "project_id": project_id,
            "project_path": project_path,
            "pty": pty,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "cols": cols,
            "rows": rows,
        }
        with self._lock:
            self._terminals[term_id] = entry
            self._buffers[term_id] = bytearray()
        return self._to_response(entry)

    def get(self, terminal_id: str) -> dict:
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")
        return self._to_response(self._terminals[terminal_id])

    def get_pty(self, terminal_id: str) -> PTY:
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")
        return self._terminals[terminal_id]["pty"]

    def list_active(
        self,
        project_id: str | None = None,
        issue_id: str | None = None,
    ) -> list[dict]:
        results = []
        for term in self._terminals.values():
            if term["status"] != "active":
                continue
            if project_id and term["project_id"] != project_id:
                continue
            if issue_id and term["issue_id"] != issue_id:
                continue
            results.append(self._to_response(term))
        return results

    def active_count(self) -> int:
        return sum(1 for t in self._terminals.values() if t["status"] == "active")

    def append_output(self, terminal_id: str, data: str) -> None:
        """Append PTY output to the terminal's scrollback buffer."""
        with self._lock:
            buf = self._buffers.get(terminal_id)
            if buf is None:
                return
            buf.extend(data.encode("utf-8", errors="replace"))
            if len(buf) > MAX_BUFFER_SIZE:
                excess = len(buf) - MAX_BUFFER_SIZE
                del buf[:excess]

    def get_buffered_output(self, terminal_id: str) -> str:
        """Return all buffered output for a terminal."""
        with self._lock:
            buf = self._buffers.get(terminal_id)
            if not buf:
                return ""
            return buf.decode("utf-8", errors="replace")

    def kill(self, terminal_id: str) -> None:
        with self._lock:
            if terminal_id not in self._terminals:
                raise KeyError(f"Terminal {terminal_id} not found")
            entry = self._terminals.pop(terminal_id)
            self._buffers.pop(terminal_id, None)
        try:
            pty = entry["pty"]
            if hasattr(pty, "close"):
                pty.close()
        except Exception:
            pass

    def mark_closed(self, terminal_id: str) -> None:
        with self._lock:
            if terminal_id in self._terminals:
                self._terminals.pop(terminal_id)
            self._buffers.pop(terminal_id, None)

    def resize(self, terminal_id: str, cols: int, rows: int) -> None:
        if terminal_id not in self._terminals:
            raise KeyError(f"Terminal {terminal_id} not found")
        entry = self._terminals[terminal_id]
        entry["cols"] = cols
        entry["rows"] = rows
        entry["pty"].set_size(cols, rows)

    def _to_response(self, entry: dict) -> dict:
        return {
            "id": entry["id"],
            "issue_id": entry["issue_id"],
            "project_id": entry["project_id"],
            "project_path": entry["project_path"],
            "status": entry["status"],
            "created_at": entry["created_at"],
            "cols": entry["cols"],
            "rows": entry["rows"],
        }


# Module-level singleton
terminal_service = TerminalService()
