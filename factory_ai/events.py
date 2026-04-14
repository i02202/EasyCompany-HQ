"""
Campus Factory AI — Event Bus
=============================
Central event system that connects CrewAI execution to all consumers
(dashboard, Telegram bot, fine-tuning data collector).

Events are typed dicts with a 'type' field and timestamped automatically.
"""
import asyncio
import json
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field, asdict


class EventType(str, Enum):
    # Crew lifecycle
    CREW_START = "crew_start"
    CREW_COMPLETE = "crew_complete"
    CREW_ERROR = "crew_error"

    # Agent lifecycle
    AGENT_START = "agent_start"
    AGENT_STEP = "agent_step"
    AGENT_COMPLETE = "agent_complete"

    # Task lifecycle
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"

    # Review / human-in-the-loop
    REVIEW_NEEDED = "review_needed"
    REVIEW_SUBMITTED = "review_submitted"

    # File outputs
    FILE_WRITTEN = "file_written"

    # Training / fine-tuning
    TRAINING_START = "training_start"
    TRAINING_PROGRESS = "training_progress"
    TRAINING_COMPLETE = "training_complete"

    # System status
    SYSTEM_STATUS = "system_status"


@dataclass
class Event:
    type: EventType
    data: dict = field(default_factory=dict)
    timestamp: str = ""
    id: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EventBus:
    """Thread-safe event bus with sync and async support."""

    def __init__(self):
        self._lock = threading.Lock()
        self._event_id = 0
        self._history: list[Event] = []
        self._sync_listeners: list[Callable[[Event], None]] = []
        self._async_queues: list[asyncio.Queue] = []
        self._max_history = 500

    def emit(self, event_type: EventType, data: dict | None = None) -> Event:
        """Emit an event (called from sync CrewAI callbacks)."""
        with self._lock:
            self._event_id += 1
            event = Event(type=event_type, data=data or {}, id=self._event_id)
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            listeners = list(self._sync_listeners)
            queues = list(self._async_queues)

        # Call listeners outside lock to avoid deadlock
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                print(f"[EventBus] Sync listener error: {e}")

        # Push to async queues — use thread-safe call_soon_threadsafe
        for q in queues:
            try:
                loop = q._loop if hasattr(q, '_loop') else None
                if loop and loop.is_running():
                    loop.call_soon_threadsafe(q.put_nowait, event)
                else:
                    q.put_nowait(event)
            except (asyncio.QueueFull, RuntimeError):
                pass  # Drop if consumer is slow or loop closed

        return event

    def on(self, callback: Callable[[Event], None]):
        """Register a synchronous listener."""
        with self._lock:
            self._sync_listeners.append(callback)

    def off(self, callback: Callable[[Event], None]):
        """Remove a synchronous listener."""
        with self._lock:
            self._sync_listeners = [l for l in self._sync_listeners if l is not callback]

    def subscribe(self) -> asyncio.Queue:
        """Create an async queue subscription (for WebSocket consumers)."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        # Capture the running loop for thread-safe puts
        try:
            q._loop = asyncio.get_running_loop()
        except RuntimeError:
            q._loop = None
        with self._lock:
            self._async_queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove an async queue subscription."""
        with self._lock:
            if q in self._async_queues:
                self._async_queues.remove(q)

    def get_history(self, since_id: int = 0, limit: int = 50) -> list[Event]:
        """Get event history, optionally since a given event ID."""
        with self._lock:
            filtered = [e for e in self._history if e.id > since_id]
            return filtered[-limit:]

    @property
    def last_event(self) -> Event | None:
        with self._lock:
            return self._history[-1] if self._history else None


# Global singleton
bus = EventBus()
