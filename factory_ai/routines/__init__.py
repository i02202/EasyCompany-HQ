"""
Campus Factory AI — Routines System
=====================================
Automated scheduled tasks inspired by EvoNexus (7 automated routines).

Routines are lightweight background jobs that run on schedule:
  - health_check: System connectivity (Ollama, DeerFlow, Gateway)
  - memory_maintenance: Prune old memories, enforce limits
  - output_cleanup: Remove stale output files older than 7 days
  - model_warmup: Pre-load models into Ollama VRAM before crew run

Routines run via threading.Timer and are managed by the RoutineManager.
"""
import json
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from factory_ai.config import OLLAMA_BASE_URL, OLLAMA_MODEL, GATEWAY_URL, OUTPUT_DIR
from factory_ai.events import bus, EventType


class Routine:
    """A single repeating background task."""

    def __init__(self, name: str, fn: Callable, interval_seconds: int, enabled: bool = True):
        self.name = name
        self.fn = fn
        self.interval = interval_seconds
        self.enabled = enabled
        self.last_run: str | None = None
        self.last_result: str | None = None
        self.run_count: int = 0
        self._timer: threading.Timer | None = None

    def start(self):
        if not self.enabled:
            return
        self._schedule()

    def stop(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule(self):
        self._timer = threading.Timer(self.interval, self._execute)
        self._timer.daemon = True
        self._timer.start()

    def _execute(self):
        try:
            result = self.fn()
            self.last_result = str(result)[:200] if result else "ok"
            self.run_count += 1
            self.last_run = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            self.last_result = f"error: {e}"
        finally:
            if self.enabled:
                self._schedule()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "interval_seconds": self.interval,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "last_result": self.last_result,
            "run_count": self.run_count,
        }


# ─── Built-in Routines ───────────────────────────────────────────────────────

def _health_check() -> str:
    """Check Ollama, Gateway, and DeerFlow connectivity."""
    results = {}

    # Ollama
    try:
        resp = urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        results["ollama"] = f"ok ({len(models)} models)"
    except Exception as e:
        results["ollama"] = f"error: {e}"

    # Gateway
    try:
        resp = urllib.request.urlopen(f"{GATEWAY_URL}/api/health", timeout=3)
        results["gateway"] = "ok"
    except Exception:
        results["gateway"] = "offline"

    # DeerFlow
    from factory_ai.config import DEERFLOW_URL
    try:
        resp = urllib.request.urlopen(f"{DEERFLOW_URL}/api/models", timeout=3)
        results["deerflow"] = "ok"
    except Exception:
        results["deerflow"] = "offline"

    bus.emit(EventType.SYSTEM_STATUS, {"health": results})
    return json.dumps(results)


def _memory_maintenance() -> str:
    """Run MemPalace maintenance (prune old entries)."""
    from factory_ai.memory import maintain, get_stats
    meta = maintain()
    stats = get_stats()
    return f"pruned={meta.get('pruned', 0)}, total={stats.get('total', 0)}"


def _output_cleanup() -> str:
    """Remove output files older than 7 days."""
    cutoff = time.time() - (7 * 86400)
    removed = 0
    for f in OUTPUT_DIR.glob("**/*"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return f"removed {removed} old files"


def _model_warmup() -> str:
    """Pre-load the brain model into Ollama VRAM."""
    try:
        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "options": {"num_predict": 1},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=60)
        return f"{OLLAMA_MODEL} warmed up"
    except Exception as e:
        return f"warmup failed: {e}"


# ─── Manager ─────────────────────────────────────────────────────────────────

class RoutineManager:
    """Manages all routines lifecycle."""

    def __init__(self):
        self.routines: dict[str, Routine] = {}

    def register(self, routine: Routine):
        self.routines[routine.name] = routine

    def start_all(self):
        for r in self.routines.values():
            r.start()
        names = [r.name for r in self.routines.values() if r.enabled]
        print(f"[Routines] Started {len(names)}: {', '.join(names)}")

    def stop_all(self):
        for r in self.routines.values():
            r.stop()

    def get_status(self) -> list[dict]:
        return [r.to_dict() for r in self.routines.values()]


# ─── Default Manager ─────────────────────────────────────────────────────────

manager = RoutineManager()
manager.register(Routine("health_check", _health_check, interval_seconds=300))       # every 5 min
manager.register(Routine("memory_maintenance", _memory_maintenance, interval_seconds=3600))  # every 1h
manager.register(Routine("output_cleanup", _output_cleanup, interval_seconds=86400, enabled=False))  # daily, off by default
manager.register(Routine("model_warmup", _model_warmup, interval_seconds=1800))      # every 30 min
