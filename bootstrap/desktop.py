"""Desktop window, icon, health polling, process lifecycle.

Estratto da start.py: pywebview window, icon conversion, port cleanup,
health monitor, shutdown logic per modalità headless e desktop.
"""

import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from bootstrap.config import Config


# ── Process management ──────────────────────────────────────────────────────

def _get_pids_on_port(port: int) -> list[int]:
    """Return list of PIDs listening on *port* (Windows netstat)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print(f"[!] netstat not found — skipping port-{port} check")
        return []

    pids: list[int] = []
    needle = f":{port}"
    for line in result.stdout.splitlines():
        line = line.strip()
        if needle not in line or "LISTENING" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[-1])
            pids.append(pid)
        except (ValueError, IndexError):
            continue
    return pids


def kill_process_on_port(port: int) -> None:
    """Kill any existing backend process listening on *port*."""
    pids = _get_pids_on_port(port)
    if not pids:
        print(f"[ok] No existing backend found on port {port}")
        return

    for pid in pids:
        print(f"[...] Found existing backend on PID {pid}, terminating...")
        try:
            kill_result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True,
                check=False,
            )
            if kill_result.returncode == 0:
                print(f"[ok] Process PID {pid} terminated")
            else:
                print(
                    f"[!] Could not terminate PID {pid}: "
                    f"{kill_result.stderr.strip() or kill_result.stdout.strip()}"
                )
        except FileNotFoundError:
            print(f"[!] taskkill not found — could not terminate PID {pid}")
        except Exception as exc:
            print(f"[!] Error terminating PID {pid}: {exc}")


# ── Icon conversion ─────────────────────────────────────────────────────────

def convert_icon(root: Path) -> None:
    """Convert logo.png to logo.ico if needed."""
    logo_png = root / "logo.png"
    logo_ico = root / "logo.ico"

    if not logo_png.exists():
        return

    if logo_ico.exists() and logo_ico.stat().st_mtime >= logo_png.stat().st_mtime:
        return

    try:
        from PIL import Image

        img = Image.open(logo_png)
        img.save(logo_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
        print("[ok] App icon created: logo.ico")
    except Exception as e:
        print(f"[!] Could not create logo.ico: {e}")


# ── Wait helpers ────────────────────────────────────────────────────────────

def wait_for_ready(name: str, proc: subprocess.Popen, port: int, timeout: int = 30) -> None:
    """Wait for a server process to start listening on *port*."""
    print(f"[...] Waiting for {name} to be ready...")
    for _ in range(timeout):
        if proc.poll() is not None:
            print(f"[!] {name} exited with code {proc.returncode}")
            sys.exit(1)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    else:
        print(f"[!] {name} did not start within {timeout // 2} seconds")
        proc.terminate()
        sys.exit(1)
    print(f"[ok] {name} is ready")


def _make_shutdown(processes: list[subprocess.Popen]) -> callable:
    """Build a shutdown function that terminates all given processes."""
    called = {"done": False}

    def shutdown(sig=None, frame=None):
        if called["done"]:
            return
        called["done"] = True
        print("\n[...] Shutting down...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[ok] All processes stopped")

    return shutdown


# ── Headless mode ───────────────────────────────────────────────────────────

def wait_and_cleanup(processes: list[subprocess.Popen]) -> None:
    """Headless mode: signal handler + poll until one process exits."""
    shutdown = _make_shutdown(processes)

    def handle_sigint(sig, frame):
        shutdown(sig, frame)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        for i, proc in enumerate(processes):
            ret = proc.poll()
            if ret is not None:
                name = ["Backend", "Frontend", "MCP Worker", "MCP Orch"][i] if i < 4 else f"Process {i}"
                print(f"\n[!] {name} exited with code {ret}")
                shutdown()
                sys.exit(1 if ret != 0 else 0)
        time.sleep(0.5)


# ── Desktop mode (pywebview) ────────────────────────────────────────────────

def run_desktop(config: Config, processes: list[subprocess.Popen]) -> None:
    """Open pywebview desktop window and block until user closes it."""
    import webview

    frontend_url = f"http://localhost:{config.frontend_port}"
    shutdown = _make_shutdown(processes)
    stop_event = threading.Event()

    # Set Windows AppUserModelID
    try:
        sys.path.insert(0, str(config.backend_dir))
        from app.desktop_icon import set_app_user_model_id
        set_app_user_model_id()
    except Exception:
        pass

    window = webview.create_window(
        "Manager AI",
        frontend_url,
        width=1400,
        height=900,
    )
    window.events.closed += lambda: stop_event.set()

    def poll_worker():
        """Watch subprocess health on the webview worker thread."""
        logo_ico = config.root / "logo.ico"
        icon_set = False
        while not stop_event.is_set():
            if not icon_set:
                try:
                    sys.path.insert(0, str(config.backend_dir))
                    from app.desktop_icon import set_app_window_icon
                    if set_app_window_icon("Manager AI", str(logo_ico)):
                        icon_set = True
                except Exception:
                    pass
            for proc in processes:
                ret = proc.poll()
                if ret is not None:
                    proc_name = "Backend" if proc is processes[0] else "Frontend"
                    print(f"\n[!] {proc_name} exited with code {ret}")
                    stop_event.set()
                    try:
                        window.destroy()
                    except Exception:
                        pass
                    return
            time.sleep(0.5)

    def handle_sigint(sig, frame):
        stop_event.set()
        try:
            window.destroy()
        except Exception:
            pass

    signal.signal(signal.SIGINT, handle_sigint)

    webview_storage = config.data_dir / "webview"
    webview_storage.mkdir(parents=True, exist_ok=True)

    try:
        webview.start(
            func=poll_worker,
            debug=bool(os.environ.get("MANAGER_AI_DEV")),
            private_mode=False,
            storage_path=str(webview_storage),
        )
    finally:
        shutdown()
