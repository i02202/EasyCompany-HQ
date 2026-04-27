"""
Campus Factory AI — MemPalace (Persistent Memory)
===================================================
Persistent memory system that survives across crew runs.
Each agent builds up knowledge over time — lessons learned, good patterns,
mistakes to avoid. This reduces re-discovery in subsequent runs.

Inspired by EvoNexus MemPalace pattern:
  - Per-agent memory files (JSONL)
  - Global shared memory for cross-agent insights
  - Auto-maintenance (prune old/low-quality entries)
  - Injected into agent system prompts at crew start

Storage: factory_ai/memory/store/
  - {agent_name}.jsonl — per-agent memories
  - _shared.jsonl — cross-agent insights
  - _meta.json — maintenance metadata
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from factory_ai.config import FACTORY_ROOT

MEMORY_STORE = FACTORY_ROOT / "memory" / "store"
MAX_MEMORIES_PER_AGENT = 50
MAX_SHARED_MEMORIES = 100
MAX_AGE_DAYS = 30  # Auto-prune entries older than this


def _ensure_store():
    MEMORY_STORE.mkdir(parents=True, exist_ok=True)


def _agent_file(agent_name: str) -> Path:
    # Whitelist: only alphanumerics, hyphens, underscores (prevents path traversal)
    safe = re.sub(r"[^\w\-]", "_", agent_name.lower())
    # Extra safety: take only the final path component
    safe = Path(safe).name
    return MEMORY_STORE / f"{safe}.jsonl"


def _shared_file() -> Path:
    return MEMORY_STORE / "_shared.jsonl"


def _meta_file() -> Path:
    return MEMORY_STORE / "_meta.json"


# ─── Write ────────────────────────────────────────────────────────────────────

def remember(agent_name: str, content: str, category: str = "insight", quality: float = 0.5):
    """Store a memory for an agent.

    Args:
        agent_name: Which agent learned this
        content: The insight/lesson/pattern (max 500 chars)
        category: "insight" | "mistake" | "pattern" | "preference"
        quality: 0.0-1.0 how useful this is (higher = kept longer)
    """
    _ensure_store()
    entry = {
        "content": content[:500],
        "category": category,
        "quality": min(1.0, max(0.0, quality)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uses": 0,
    }
    path = _agent_file(agent_name)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def remember_shared(content: str, source_agent: str = "", category: str = "cross_agent"):
    """Store a shared memory visible to all agents."""
    _ensure_store()
    entry = {
        "content": content[:500],
        "category": category,
        "source": source_agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uses": 0,
    }
    path = _shared_file()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ─── Read ─────────────────────────────────────────────────────────────────────

def recall(agent_name: str, limit: int = 10) -> list[dict]:
    """Retrieve recent memories for an agent, sorted by quality × recency."""
    path = _agent_file(agent_name)
    if not path.exists():
        return []

    entries = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Score: quality * recency_factor
    now = time.time()
    for e in entries:
        try:
            ts = datetime.fromisoformat(e["timestamp"]).timestamp()
            age_days = (now - ts) / 86400
            recency = max(0.1, 1.0 - (age_days / MAX_AGE_DAYS))
        except Exception:
            recency = 0.5
        e["_score"] = e.get("quality", 0.5) * recency

    entries.sort(key=lambda e: e["_score"], reverse=True)
    return entries[:limit]


def recall_shared(limit: int = 10) -> list[dict]:
    """Retrieve shared memories visible to all agents."""
    path = _shared_file()
    if not path.exists():
        return []

    entries = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return entries[-limit:]


def build_memory_prompt(agent_name: str, max_entries: int = 8) -> str:
    """Build a memory injection string for an agent's system prompt.

    Returns empty string if no memories exist (first run).
    """
    agent_mems = recall(agent_name, limit=max_entries)
    shared_mems = recall_shared(limit=5)

    if not agent_mems and not shared_mems:
        return ""

    parts = ["\n\n--- MEMORY (lessons from previous runs) ---"]

    if agent_mems:
        parts.append("Your past insights:")
        for m in agent_mems:
            parts.append(f"  [{m.get('category', '?')}] {m.get('content', '')}")

    if shared_mems:
        parts.append("\nTeam-wide knowledge:")
        for m in shared_mems:
            src = f" (from {m.get('source', '')})" if m.get("source") else ""
            parts.append(f"  {m.get('content', '')}{src}")

    parts.append("--- END MEMORY ---\n")
    return "\n".join(parts)


# ─── Maintenance ──────────────────────────────────────────────────────────────

def maintain():
    """Run maintenance: prune old/low-quality entries, enforce limits.

    Call periodically (e.g., weekly routine or at crew start).
    """
    _ensure_store()
    now = time.time()
    pruned_total = 0

    for jsonl_file in MEMORY_STORE.glob("*.jsonl"):
        entries = []
        for line in jsonl_file.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Prune by age
            try:
                ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                age_days = (now - ts) / 86400
                if age_days > MAX_AGE_DAYS and entry.get("quality", 0.5) < 0.7:
                    pruned_total += 1
                    continue
            except Exception:
                pass

            entries.append(entry)

        # Enforce limit
        is_shared = jsonl_file.name == "_shared.jsonl"
        limit = MAX_SHARED_MEMORIES if is_shared else MAX_MEMORIES_PER_AGENT
        if len(entries) > limit:
            # Keep highest quality
            entries.sort(key=lambda e: e.get("quality", 0.5), reverse=True)
            pruned_total += len(entries) - limit
            entries = entries[:limit]

        # Re-sort by timestamp so recall_shared()'s tail-slice returns most recent
        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=False)

        # Atomic rewrite: write to temp file, then os.replace() (safe on crash)
        tmp_path = jsonl_file.with_suffix(".jsonl.tmp")
        tmp_path.write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n",
            encoding="utf-8",
        )
        os.replace(str(tmp_path), str(jsonl_file))

    # Update meta
    meta = {"last_maintenance": datetime.now(timezone.utc).isoformat(), "pruned": pruned_total}
    _meta_file().write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def get_stats() -> dict:
    """Get memory store statistics."""
    _ensure_store()
    stats = {"agents": {}, "shared": 0, "total": 0}
    for jsonl_file in MEMORY_STORE.glob("*.jsonl"):
        try:
            count = sum(1 for line in jsonl_file.read_text(encoding="utf-8").strip().split("\n") if line)
        except Exception:
            count = -1  # Signal unreadable file
        if jsonl_file.name == "_shared.jsonl":
            stats["shared"] = count
        else:
            stats["agents"][jsonl_file.stem] = count
        if count > 0:
            stats["total"] += count

    meta_path = _meta_file()
    if meta_path.exists():
        try:
            stats["meta"] = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            stats["meta"] = {"error": "corrupt meta file"}

    return stats
