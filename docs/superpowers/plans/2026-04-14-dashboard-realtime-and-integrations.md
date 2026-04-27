# Dashboard Real-Time + Integrations Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Factory AI dashboard show ALL crew activity in real-time (no refresh needed), enable Telegram-based review approval, integrate DeerFlow properly, and boost the Researcher agent's output quality.

**Architecture:** 5 parallel improvements that share the EventBus as backbone. Tasks 1-2 are the most impactful (real-time visibility). Task 3 enables DeerFlow. Task 4 is model management. Task 5 improves content quality.

**Tech Stack:** Python (CrewAI, FastAPI, python-telegram-bot 22.7), JavaScript (Canvas dashboard), DeerFlow 2.0 (LangGraph), Ollama (qwen3:8b, campus-expert)

---

### Task 1: Granular Event Emission — Make the Dashboard See Everything

**Problem:** `AGENT_START`, `TASK_START` are defined in EventType but never emitted. `step_callback` emits `AGENT_STEP` but with `agent_name="unknown"`. The dashboard handles these events in JS but never receives them — so the user sees no progress until a task completes.

**Files:**
- Modify: `factory_ai/crew_callbacks.py` (the main fix)
- Modify: `factory_ai/crews/campus_crew.py` (wire callbacks properly)
- Modify: `factory_ai/dashboard/index.html` (enhance WS handler)

- [ ] **Step 1: Rewrite crew_callbacks.py with proper agent identity extraction**

CrewAI's `step_callback` receives either `AgentAction` or `AgentFinish` objects. Both have `.tool`, `.tool_input`, and the agent can be identified from `.log` or the step object. The task callback gets `TaskOutput` which has `.agent` (str).

```python
# factory_ai/crew_callbacks.py
"""
Crew Callbacks — Granular event emission for real-time dashboard.
"""
import time
from factory_ai.events import bus, EventType
from factory_ai.config import OUTPUT_DIR


# Track which agent is currently active
_current_agent = {"name": "unknown", "started_at": None}


def step_callback(step_output):
    """Called on every CrewAI reasoning step (thought, tool call, finish)."""
    agent_name = _current_agent["name"]

    # Extract step details
    step_type = "thought"
    content = ""
    tool_name = ""
    tool_input = ""

    if hasattr(step_output, 'tool'):
        step_type = "tool_call"
        tool_name = getattr(step_output, 'tool', '')
        tool_input = str(getattr(step_output, 'tool_input', ''))[:200]
        content = f"{tool_name}({tool_input})"
    elif hasattr(step_output, 'return_values'):
        step_type = "finish"
        content = str(getattr(step_output, 'return_values', ''))[:300]
    elif hasattr(step_output, 'log'):
        log = str(step_output.log)
        # Try to extract agent name from log
        if "Agent:" in log:
            parts = log.split("Agent:")
            if len(parts) > 1:
                agent_name = parts[1].strip().split("\n")[0].strip()
                _current_agent["name"] = agent_name
        content = log[:300]

    bus.emit(EventType.AGENT_STEP, {
        "agent": agent_name,
        "step_type": step_type,
        "tool": tool_name,
        "content": content,
        "timestamp": time.time(),
    })


def task_callback(task_output):
    """Called when a CrewAI task completes."""
    result_text = ""
    agent_name = ""

    if hasattr(task_output, 'agent'):
        agent_name = str(task_output.agent)
    if hasattr(task_output, 'raw'):
        result_text = str(task_output.raw)[:2000]
    elif hasattr(task_output, 'result'):
        result_text = str(task_output.result)[:2000]

    bus.emit(EventType.TASK_COMPLETE, {
        "agent": agent_name,
        "result_preview": result_text,
    })


def make_task_callback(task_name: str, agent_name: str):
    """Create a per-task callback that emits AGENT_START + TASK_COMPLETE."""
    _started = {"done": False}

    def callback(task_output):
        # Emit AGENT_START on first call (task beginning)
        if not _started["done"]:
            _started["done"] = True

        # Update current agent tracker
        _current_agent["name"] = agent_name

        result_text = ""
        if hasattr(task_output, 'raw'):
            result_text = str(task_output.raw)[:2000]
        elif hasattr(task_output, 'result'):
            result_text = str(task_output.result)[:2000]
        else:
            result_text = str(task_output)[:2000]

        bus.emit(EventType.TASK_COMPLETE, {
            "task": task_name,
            "agent": agent_name,
            "result_preview": result_text,
        })

        # Save output
        output_file = OUTPUT_DIR / f"{task_name.replace(' ', '_').lower()}_output.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            output_file.write_text(result_text, encoding="utf-8")
            bus.emit(EventType.FILE_WRITTEN, {"filename": output_file.name})
        except Exception as e:
            print(f"[Callback] Error saving output: {e}")

    return callback


class DataCollector:
    """Collects agent interactions for fine-tuning data."""
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.count = 0
        self.path = output_dir / "training_data.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def collect(self, event):
        import json
        if event.type in (EventType.AGENT_STEP, EventType.TASK_COMPLETE):
            data = {
                "type": "tool_use" if event.data.get("step_type") == "tool_call" else "output",
                "agent": event.data.get("agent", ""),
                "task": event.data.get("task", ""),
                "output": event.data.get("result_preview", event.data.get("content", "")),
                "timestamp": event.timestamp,
            }
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            self.count += 1
```

- [ ] **Step 2: Wire AGENT_START + TASK_START in campus_crew.py**

Add `step_callback` to each agent and emit `AGENT_START`/`TASK_START` using CrewAI's proper hooks:

```python
# In campus_crew.py, for each agent add:
researcher = Agent(
    ...
    step_callback=step_callback,  # Wire the granular callback
)

# For the crew, add before_kickoff and task_started hooks:
# Before each task, emit TASK_START
def _make_task_start_emitter(task_name, agent_name):
    def emitter(task_output=None):
        _current_agent["name"] = agent_name
        bus.emit(EventType.AGENT_START, {"agent": agent_name})
        bus.emit(EventType.TASK_START, {"task": task_name, "agent": agent_name})
    return emitter
```

- [ ] **Step 3: Update dashboard JS to use WebSocket events for live updates**

The WebSocket handler already handles `agent_start`, `agent_step`, `task_complete` etc. The fix is to ensure:
1. `agent_start` → highlight agent card immediately
2. `agent_step` with `step_type=tool_call` → show tool name in agent detail
3. `task_complete` → mark agent done, update progress bar
4. Remove manual refresh intervals for data that comes via WS

- [ ] **Step 4: Test by starting crew and verifying dashboard updates in real-time**

- [ ] **Step 5: Commit**

---

### Task 2: Telegram Interactive Reviews

**Problem:** The Telegram bot is push-only. When `REVIEW_NEEDED` fires, the user sees a message but can only approve via the web dashboard. Need inline keyboard buttons.

**Files:**
- Modify: `factory_ai/telegram_bot.py` (add interactive handler)
- Modify: `factory_ai/server.py` (expose review API for bot)

- [ ] **Step 1: Add Application with CallbackQueryHandler to telegram_bot.py**

Replace the send-only bot with a full `Application` that:
1. On `REVIEW_NEEDED`: sends message with `InlineKeyboardMarkup` containing Approve/Reject buttons + callback_data
2. On button press: `CallbackQueryHandler` calls `/api/reviews/{event_id}` via HTTP
3. On `/comment <text>`: adds notes to the current review

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Build keyboard for review
keyboard = [
    [
        InlineKeyboardButton("Approve", callback_data=f"approve:{event_id}"),
        InlineKeyboardButton("Reject", callback_data=f"reject:{event_id}"),
    ],
    [InlineKeyboardButton("Approve with note...", callback_data=f"note:{event_id}")],
]
reply_markup = InlineKeyboardMarkup(keyboard)
await bot.send_message(chat_id, text, reply_markup=reply_markup)

# Handler
async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, event_id = query.data.split(":")
    # POST to /api/reviews/{event_id}
    import urllib.request, json
    req = urllib.request.Request(
        f"http://localhost:{PORT}/api/reviews/{event_id}",
        data=json.dumps({"action": action, "notes": ""}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5)
    await query.edit_message_text(f"Review #{event_id}: {action.upper()}")
```

- [ ] **Step 2: Add /status command to check crew progress from Telegram**
- [ ] **Step 3: Test review flow: start crew → wait for REVIEW_NEEDED → approve via Telegram**
- [ ] **Step 4: Commit**

---

### Task 3: DeerFlow Integration

**Problem:** DeerFlow 2.0 is installed at `C:\Users\Daniel Amer\deer-flow\` but not running. The HTTP fallback in `deerflow_tools.py` points to port 2026 (wrong — DeerFlow gateway uses 8001, langgraph dev uses 2024). No events emitted from DeerFlow calls.

**Files:**
- Modify: `factory_ai/tools/deerflow_tools.py` (fix port, add events, health check)
- Modify: `.env` (add DEERFLOW_URL)
- Modify: `factory_ai/config.py` (add DEERFLOW_URL config)
- Modify: `factory_ai/server.py` (add /api/deerflow/status endpoint)
- Create: `scripts/start-deerflow.sh` (convenience script)

- [ ] **Step 1: Add DEERFLOW_URL to .env and config.py**

```
# .env
DEERFLOW_URL=http://localhost:8001
```

- [ ] **Step 2: Fix deerflow_tools.py — correct port, add bus events, health check**

```python
def _deerflow_http_query(prompt: str) -> str:
    bus.emit(EventType.AGENT_STEP, {
        "agent": "DeerFlow",
        "step_type": "tool_call",
        "tool": "deep_research",
        "content": prompt[:100],
    })
    # ... existing HTTP logic but with correct URL from config ...
    bus.emit(EventType.AGENT_STEP, {
        "agent": "DeerFlow",
        "step_type": "finish",
        "content": result[:200],
    })
    return result
```

- [ ] **Step 3: Add /api/deerflow/status endpoint to server.py**

Check if DeerFlow gateway is reachable at configured URL.

- [ ] **Step 4: Update dashboard DeerFlow indicator to use the new endpoint**
- [ ] **Step 5: Create start-deerflow script and test end-to-end**
- [ ] **Step 6: Commit**

---

### Task 4: Fine-Tuned Model Update

**Problem:** campus-expert (Qwen2.5-1.5B) doesn't support tool calling. We have new training data from the latest crew run. Options: (A) retrain on Qwen3:8B which supports tools, (B) keep hybrid approach (campus-expert for knowledge, qwen3:8b for tools), (C) add tool-call training examples.

**Recommendation:** Option B for now — campus-expert stays as knowledge model, qwen3:8b handles tool calling. In parallel, collect more ChatML examples and retrain when we have 100+.

**Files:**
- Modify: `factory_ai/training.py` (update to collect tool-call examples too)
- Modify: `factory_ai/crews/campus_crew.py` (already done — tool_llm = qwen3:8b)

- [ ] **Step 1: Update DataCollector to capture tool-call patterns for future training**
- [ ] **Step 2: Add training data from this crew run to the dataset**
- [ ] **Step 3: Update get_training_info to report hybrid model status**
- [ ] **Step 4: Commit**

---

### Task 5: Boost Researcher Agent

**Problem:** The Researcher uses DDG + static reference data. Zones end up with few unique assets (9-20 props when some zones could have 30+). The fal.ai API key is configured but not used for on-demand texture generation.

**Files:**
- Modify: `factory_ai/tools/research_tools.py` (better DDG queries, more furniture types)
- Create: `factory_ai/tools/asset_gen_tools.py` (fal.ai integration for texture generation)
- Modify: `factory_ai/crews/campus_crew.py` (give Researcher + Art Director the new tools)

- [ ] **Step 1: Expand FURNITURE_DIMENSIONS and OFFICE_REFERENCE_DATA**

Add 40+ more furniture types covering items zones are missing:
- Standing desks variants, monitor arms, cable trays
- Acoustic panels, room dividers, privacy screens
- Reception desks, coat racks, umbrella stands
- Whiteboards (mobile), projectors, video conferencing units
- Kitchen items: dishwasher, toaster, water cooler, trash/recycling

- [ ] **Step 2: Create asset_gen_tools.py with fal.ai texture generation**

```python
@tool("generate_prop_texture")
def generate_prop_texture(prop_name: str, style: str = "isometric pixel art") -> str:
    """Generate a new prop texture using fal.ai image generation.
    Returns the path to the saved PNG file."""
    import fal_client
    result = fal_client.submit("fal-ai/flux/schnell", {
        "prompt": f"isometric pixel art {prop_name}, 64x64, transparent background, "
                  f"game asset, modern tech office style, {style}",
        "image_size": {"width": 128, "height": 128},
    })
    # Save to assets/tiles/{prop_name}.png
    ...
```

- [ ] **Step 3: Wire new tools to Researcher and Art Director agents**
- [ ] **Step 4: Test by running Researcher task and verifying expanded output**
- [ ] **Step 5: Commit**

---

## Execution Order

Tasks 1 and 2 are the highest priority (user can't see anything without them).
Task 3 is independent.
Tasks 4 and 5 can run after 1-3 are done.

**Recommended:** 1 → 2 → 3 → 4 → 5

## Dependencies

```
Task 1 (Events) ← required by → Task 2 (Telegram uses events)
Task 1 (Events) ← required by → Task 3 (DeerFlow emits events)
Task 3 (DeerFlow) ← enhances → Task 5 (Researcher uses DeerFlow)
Task 4 (Model) ← uses data from → Task 1 (DataCollector improvements)
```
