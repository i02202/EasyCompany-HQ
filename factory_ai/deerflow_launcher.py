"""
DeerFlow Auto-Launcher
=======================
Starts and monitors the DeerFlow Gateway (port 8001) as a persistent
background service. Gateway mode embeds the LangGraph agent runtime,
so we only need one process.

Called from server.py on startup. Provides:
- Auto-start on server boot
- Health monitoring with auto-restart
- Graceful shutdown
- Log forwarding to our EventBus
"""
import atexit
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from factory_ai.config import DEERFLOW_URL
from factory_ai.events import bus, EventType

DEERFLOW_ROOT = Path(os.getenv(
    "DEERFLOW_ROOT",
    r"C:\Users\Daniel Amer\deer-flow",
))
DEERFLOW_BACKEND = DEERFLOW_ROOT / "backend"
DEERFLOW_UV = DEERFLOW_BACKEND / ".venv" / "Scripts" / "uvicorn.exe"
DEERFLOW_PORT = 8001

_process: subprocess.Popen | None = None
_monitor_thread: threading.Thread | None = None
_shutdown = threading.Event()


def _health_check() -> bool:
    """Quick health check on DeerFlow gateway."""
    for endpoint in ["/api/models", "/docs", "/"]:
        try:
            resp = urllib.request.urlopen(
                f"{DEERFLOW_URL}{endpoint}", timeout=3
            )
            if resp.status == 200:
                return True
        except Exception:
            continue
    return False


def _start_process() -> subprocess.Popen | None:
    """Start the DeerFlow gateway process."""
    if not DEERFLOW_BACKEND.exists():
        print(f"[DeerFlow] Backend not found at {DEERFLOW_BACKEND}")
        return None

    env = {**os.environ}
    env["SKIP_LANGGRAPH_SERVER"] = "1"  # Gateway mode — embedded runtime
    env["PYTHONPATH"] = str(DEERFLOW_BACKEND)
    env["PYTHONIOENCODING"] = "utf-8"

    # Load DeerFlow's .env (using dotenv for proper quote/comment handling)
    deerflow_env = DEERFLOW_ROOT / ".env"
    if deerflow_env.exists():
        try:
            from dotenv import dotenv_values
            deerflow_vals = dotenv_values(deerflow_env)
            env.update({k: v for k, v in deerflow_vals.items() if v is not None})
        except ImportError:
            for line in deerflow_env.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    val = val.strip().strip("'\"")
                    env[key.strip()] = val

    # Use uv to run uvicorn inside DeerFlow's venv
    uv_path = "uv"
    cmd = [
        uv_path, "run",
        "uvicorn", "app.gateway.app:app",
        "--host", "0.0.0.0",
        "--port", str(DEERFLOW_PORT),
    ]

    try:
        print(f"[DeerFlow] Starting gateway on port {DEERFLOW_PORT}...")
        proc = subprocess.Popen(
            cmd,
            cwd=str(DEERFLOW_BACKEND),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Wait a bit and check it didn't crash immediately
        time.sleep(3)
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            print(f"[DeerFlow] Gateway failed to start (exit {proc.returncode})")
            print(f"[DeerFlow] Output: {output[:500]}")
            return None

        print(f"[DeerFlow] Gateway process started (PID {proc.pid})")
        return proc

    except FileNotFoundError:
        print(f"[DeerFlow] 'uv' not found in PATH. Install with: pip install uv")
        return None
    except Exception as e:
        print(f"[DeerFlow] Failed to start: {e}")
        return None


def _log_reader(proc: subprocess.Popen):
    """Read DeerFlow stdout and forward important lines."""
    if not proc.stdout:
        return
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            # Forward important log lines
            if any(kw in line.lower() for kw in ["error", "exception", "started", "listening"]):
                print(f"  [DeerFlow] {line[:200]}")
    except Exception:
        pass


def _monitor_loop():
    """Monitor DeerFlow health and restart if needed."""
    global _process

    # Initial wait for startup (DeerFlow takes ~40s to load all dependencies)
    time.sleep(45)

    consecutive_failures = 0
    max_failures = 3
    restart_cooldown = 30  # seconds between restart attempts

    while not _shutdown.is_set():
        if _process and _process.poll() is not None:
            # Process died
            print(f"[DeerFlow] Gateway process exited (code {_process.returncode})")
            bus.emit(EventType.SYSTEM_STATUS, {
                "service": "deerflow",
                "status": "crashed",
                "detail": f"Exit code {_process.returncode}",
            })

            if not _shutdown.is_set():
                print(f"[DeerFlow] Restarting in {restart_cooldown}s...")
                _shutdown.wait(restart_cooldown)
                if not _shutdown.is_set():
                    _process = _start_process()
                    if _process:
                        threading.Thread(
                            target=_log_reader, args=(_process,), daemon=True
                        ).start()
                        bus.emit(EventType.SYSTEM_STATUS, {
                            "service": "deerflow",
                            "status": "restarted",
                        })
                    consecutive_failures += 1

        elif _process:
            # Process running — do health check
            if _health_check():
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"[DeerFlow] {max_failures} consecutive health check failures")
                    bus.emit(EventType.SYSTEM_STATUS, {
                        "service": "deerflow",
                        "status": "unhealthy",
                        "failures": consecutive_failures,
                    })

        _shutdown.wait(15)  # Check every 15 seconds


def start():
    """Start DeerFlow gateway and health monitor. Called from server.py."""
    global _process, _monitor_thread

    # Check if already running externally
    if _health_check():
        print("[DeerFlow] Gateway already running on port 8001")
        bus.emit(EventType.SYSTEM_STATUS, {
            "service": "deerflow",
            "status": "running",
            "detail": "Already running (external)",
        })
        return True

    _process = _start_process()
    if not _process:
        print("[DeerFlow] Could not start gateway — will use DDG fallback")
        return False

    # Start log reader
    threading.Thread(target=_log_reader, args=(_process,), daemon=True).start()

    # Start health monitor
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()

    # Wait for gateway to become healthy (DeerFlow takes ~40s to load)
    for i in range(25):  # up to 75 seconds
        time.sleep(3)
        if _health_check():
            print(f"[DeerFlow] Gateway healthy after {(i+1)*3}s")
            bus.emit(EventType.SYSTEM_STATUS, {
                "service": "deerflow",
                "status": "running",
            })
            return True

    print("[DeerFlow] Gateway started but not yet healthy — monitor will keep checking")
    return True


def stop():
    """Stop DeerFlow gateway gracefully."""
    global _process
    _shutdown.set()

    if _process and _process.poll() is None:
        print("[DeerFlow] Stopping gateway...")
        _process.terminate()
        try:
            _process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _process.kill()
        print("[DeerFlow] Gateway stopped")


def is_running() -> bool:
    """Check if DeerFlow is running and healthy."""
    return _health_check()


# Ensure cleanup on exit
atexit.register(stop)
