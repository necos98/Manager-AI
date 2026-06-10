"""
Safe Reload Becanned

Trova il processo backend di Manager AI in esecuzione sulla porta configurata,
lo ferma in modo pulito, poi richiama start.bat per riavviare tutto.

Usage:
    python "Safe Reload Becanned.py"
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START_BAT = ROOT / "start.bat"
ENV_FILE = ROOT / ".env"

# --- Legge la porta backend dal .env (default 8000) ---
BACKEND_PORT = 8000
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            if key.strip() == "BACKEND_PORT":
                try:
                    BACKEND_PORT = int(val.strip())
                except ValueError:
                    pass

print(f"[...] Backend configurato sulla porta {BACKEND_PORT}")


def find_process_on_port(port: int) -> int | None:
    """Trova il PID del processo in ascolto su `port` usando netstat."""
    try:
        # netstat -ano mostra tutte le connessioni con PID
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            # Cerca righe tipo: TCP 0.0.0.0:8001 0.0.0.0:0 LISTENING 12345
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in line:
                addr_part = parts[1] if len(parts) > 1 else ""
                if f":{port}" in addr_part:
                    pid_str = parts[-1]
                    if pid_str.isdigit():
                        return int(pid_str)
        return None
    except Exception as e:
        print(f"[!] Errore netstat: {e}")
        return None


def kill_process(pid: int, timeout_sec: int = 10) -> bool:
    """Termina un processo in modo graduale: prima SIGTERM, poi SIGKILL."""
    try:
        proc_info = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
            capture_output=True, text=True, timeout=10,
        )
        if pid == 0 or str(pid) not in proc_info.stdout:
            print(f"[!] Processo {pid} non trovato (già terminato?)")
            return True

        print(f"[...] Terminazione processo PID {pid}...")

        # 1) Tenta graceful con taskkill /PID
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, timeout=10,
        )

        # 2) Aspetta che sparisca
        for _ in range(timeout_sec):
            time.sleep(1)
            proc_info = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
            )
            if str(pid) not in proc_info.stdout:
                print(f"[ok] Processo {pid} terminato")
                return True

        print(f"[!] Processo {pid} ancora vivo dopo {timeout_sec}s, forzato")
        return False
    except Exception as e:
        print(f"[!] Errore kill: {e}")
        return False


def wait_for_port_free(port: int, timeout_sec: int = 15) -> bool:
    """Aspetta che la porta sia libera."""
    print(f"[...] Attesa che la porta {port} sia libera...")
    for _ in range(timeout_sec):
        pid = find_process_on_port(port)
        if pid is None:
            print(f"[ok] Porta {port} libera")
            return True
        time.sleep(1)
    print(f"[!] Porta {port} ancora occupata dopo {timeout_sec}s")
    return False


def run_start_bat():
    """Lancia start.bat dalla directory del progetto."""
    if not START_BAT.exists():
        print(f"[!] start.bat non trovato: {START_BAT}")
        return False

    print(f"[...] Avvio {START_BAT}...")
    try:
        # Usa shell=True così cmd.exe esegue il .bat
        subprocess.Popen(
            ["cmd.exe", "/c", "start", str(START_BAT)],
            cwd=str(ROOT),
            shell=False,
        )
        print("[ok] start.bat lanciato in una nuova finestra")
        return True
    except Exception as e:
        print(f"[!] Errore avvio start.bat: {e}")
        return False


def main():
    print("=" * 50)
    print("  Safe Reload Backend — Manager AI")
    print("=" * 50)
    print()

    # 1) Trova processo sulla porta
    pid = find_process_on_port(BACKEND_PORT)
    if pid is None:
        print(f"[!] Nessun processo trovato sulla porta {BACKEND_PORT}")
        print("[...] Il backend non è in esecuzione, avvio diretto...")
    else:
        print(f"[...] Trovato processo PID {pid} sulla porta {BACKEND_PORT}")
        kill_process(pid)
        wait_for_port_free(BACKEND_PORT)

    print()
    print("─" * 40)
    print("[...] Riavvio del backend...")
    print("─" * 40)

    # 2) Avvia start.bat
    run_start_bat()

    print()
    print("[ok] Completato. Il backend si sta riavviando nella nuova finestra.")


if __name__ == "__main__":
    main()
