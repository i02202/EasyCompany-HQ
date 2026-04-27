"""
Campus Factory AI — CrewAI Callbacks
=====================================
Granular event emission for real-time dashboard visibility.

Hooks into CrewAI's Crew-level step_callback and per-Task callback
to emit fine-grained events to the EventBus. The dashboard and Telegram
bot consume these via WebSocket and sync listeners.

Events emitted:
  AGENT_START  — when a new agent begins (detected from step identity)
  AGENT_STEP   — every tool call, thought, or finish with agent name
  TASK_COMPLETE — when a task finishes, with agent + result preview
  FILE_WRITTEN — when output files are saved
"""
import json
import time
from pathlib import Path
from factory_ai.events import bus, EventType


# ─── Agent Tracker ────────────────────────────────────────────────────────
# CrewAI's step_callback doesn't directly tell us which agent is running,
# but we can infer it from the Task callback (which DOES know the agent).
# We also detect agent transitions from the step log content.

_active_agent = {"name": "", "task": ""}


def _detect_agent_from_step(step_output) -> str:
    """Try to extract agent identity from a CrewAI step object."""
    # CrewAI step objects sometimes carry agent info in .log
    if hasattr(step_output, 'log'):
        log = str(step_output.log)
        # CrewAI formats: "Agent: Researcher\n..."
        for line in log.split('\n'):
            if line.strip().startswith('Agent:'):
                return line.split(':', 1)[1].strip()
    return ""


# ─── Crew-level step_callback ─────────────────────────────────────────────
# This is set on the Crew object and fires for EVERY agent step.

def crew_step_callback(step_output, agent=None):
    """Called by CrewAI on every agent reasoning step (thought, tool, finish)."""
    try:
        # Detect agent — prefer the agent param (CrewAI >= 0.55), fallback to log parsing
        detected = ""
        if agent is not None:
            detected = getattr(agent, 'role', str(agent))
        if not detected:
            detected = _detect_agent_from_step(step_output)
        if detected:
            if detected != _active_agent["name"]:
                # New agent started!
                _active_agent["name"] = detected
                bus.emit(EventType.AGENT_START, {
                    "agent": detected,
                    "agent_name": detected,
                })
        agent_name = _active_agent["name"] or "working"

        # Classify step type and extract content
        step_type = "thought"
        tool_name = ""
        content = ""

        if hasattr(step_output, 'tool'):
            step_type = "tool_call"
            tool_name = str(getattr(step_output, 'tool', ''))
            tool_input = str(getattr(step_output, 'tool_input', ''))[:200]
            content = f"{tool_name}({tool_input})"

        elif hasattr(step_output, 'return_values'):
            step_type = "finish"
            rv = step_output.return_values
            if isinstance(rv, dict):
                content = str(rv.get('output', ''))[:500]
            else:
                content = str(rv)[:500]

        elif hasattr(step_output, 'text'):
            content = str(step_output.text)[:500]

        elif hasattr(step_output, 'log'):
            content = str(step_output.log)[:500]

        else:
            content = str(step_output)[:300]

        bus.emit(EventType.AGENT_STEP, {
            "agent": agent_name,
            "agent_name": agent_name,
            "step_type": step_type,
            "tool": tool_name,
            "content": content,
        })

    except Exception as e:
        print(f"[Callbacks] step_callback error: {e}")


# ─── Per-Task callback factory ────────────────────────────────────────────
# Each Task gets its own callback that knows the task name and agent name.

def make_task_callback(task_name: str, agent_name: str, output_dir: Path):
    """Create a per-task callback that emits AGENT_START + TASK_COMPLETE."""

    def callback(task_output):
        # Mark this agent as active (for step_callback agent detection)
        _active_agent["name"] = agent_name
        _active_agent["task"] = task_name

        # Emit TASK_COMPLETE (task just finished — AGENT_START was emitted by step_callback)
        # Note: CrewAI task callbacks fire AFTER task completion, not before

        # Extract FULL result — never truncated.
        # The single result_text=...[:2000] pattern caused a triple-cascade bug:
        # truncated text leaked into (a) output .txt files, (b) training_data.jsonl
        # (via DataCollector reading the event payload). Now we keep both:
        #   result_full     → full output for file + training data
        #   result_preview  → 2K snippet for dashboard / Telegram cards only
        if hasattr(task_output, 'raw'):
            result_full = str(task_output.raw)
        elif hasattr(task_output, 'result'):
            result_full = str(task_output.result)
        else:
            result_full = str(task_output)
        result_preview = result_full[:2000]

        # Emit TASK_COMPLETE — both fields available; consumers pick what they need.
        bus.emit(EventType.TASK_COMPLETE, {
            "task": task_name,
            "agent": agent_name,
            "result_preview": result_preview,
            "result_full": result_full,
        })

        # Save FULL output file (no truncation)
        output_file = output_dir / f"{task_name.replace(' ', '_').lower()}_output.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            output_file.write_text(result_full, encoding="utf-8")
            bus.emit(EventType.FILE_WRITTEN, {"filename": output_file.name})
        except Exception as e:
            print(f"[Callback] Error saving {output_file.name}: {e}")

    return callback


# ─── Crew lifecycle helpers ───────────────────────────────────────────────

def before_kickoff(inputs=None):
    """Called before crew starts. Emits CREW_START if not already emitted."""
    # Note: CREW_START is typically emitted manually in server.py/run.py
    # This is a safety net.
    pass


# ─── Training Data Collector ──────────────────────────────────────────────

class DataCollector:
    """
    Collects agent interactions for fine-tuning dataset.
    Listens to EventBus and saves examples as JSONL.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.examples: list[dict] = []
        self.dataset_path = self.output_dir / "training_data.jsonl"

    def collect(self, event):
        """EventBus listener that collects training examples."""
        if event.type == EventType.TASK_COMPLETE:
            # Prefer result_full (untruncated). Fall back to result_preview for
            # backwards-compat with older event payloads in replayed logs.
            output = event.data.get("result_full") or event.data.get("result_preview", "")
            example = {
                "task": event.data.get("task", ""),
                "agent": event.data.get("agent", ""),
                "output": output,
                "timestamp": event.timestamp,
            }
            self.examples.append(example)
            with open(self.dataset_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        elif event.type == EventType.AGENT_STEP:
            if event.data.get("step_type") == "tool_call":
                example = {
                    "type": "tool_use",
                    "agent": event.data.get("agent", ""),
                    "action": event.data.get("content", ""),
                    "timestamp": event.timestamp,
                }
                self.examples.append(example)
                with open(self.dataset_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(example, ensure_ascii=False) + "\n")

    @property
    def count(self) -> int:
        return len(self.examples)
