"""
Campus Factory AI — Dashboard Server
=====================================
FastAPI server providing:
- WebSocket for real-time event streaming
- REST endpoints for crew control, status, and review
- Static file serving for the dashboard frontend
- Training status monitoring
"""
import asyncio
import json
import os
import threading
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env at server startup
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from factory_ai.config import OUTPUT_DIR, PROJECT_ROOT, ZONES, OLLAMA_BASE_URL, OLLAMA_MODEL
from factory_ai.events import bus, EventType, Event

app = FastAPI(title="Campus Factory AI — Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── State ─────────────────────────────────────────────────────────────────
crew_state = {
    "status": "idle",       # idle | running | paused_for_review | complete | error
    "current_agent": None,
    "current_task": None,
    "progress": 0,          # 0-100
    "tasks_completed": 0,
    "tasks_total": 6,
    "start_time": None,
    "events_count": 0,
    "training": {
        "status": "idle",   # idle | collecting | training | complete
        "examples_collected": 0,
        "epochs_done": 0,
        "epochs_total": 0,
        "loss": None,
    },
}

# Pending reviews queue (human-in-the-loop)
pending_reviews: list[dict] = []
review_responses: dict[int, dict] = {}  # event_id → response
review_event = threading.Event()  # signals when a review is submitted


def update_state_from_event(event: Event):
    """Sync listener to update crew_state from events."""
    crew_state["events_count"] = event.id

    if event.type == EventType.CREW_START:
        crew_state["status"] = "running"
        crew_state["start_time"] = event.timestamp
        crew_state["progress"] = 0
        crew_state["tasks_completed"] = 0

    elif event.type == EventType.AGENT_START:
        crew_state["current_agent"] = event.data.get("agent", "")

    elif event.type == EventType.TASK_START:
        crew_state["current_task"] = event.data.get("task", "")

    elif event.type == EventType.TASK_COMPLETE:
        crew_state["tasks_completed"] += 1
        crew_state["progress"] = int(
            (crew_state["tasks_completed"] / crew_state["tasks_total"]) * 100
        )

    elif event.type == EventType.REVIEW_NEEDED:
        crew_state["status"] = "paused_for_review"
        pending_reviews.append({
            "event_id": event.id,
            "agent": event.data.get("agent", ""),
            "description": event.data.get("description", ""),
            "preview": event.data.get("preview", ""),
            "timestamp": event.timestamp,
        })

    elif event.type == EventType.REVIEW_SUBMITTED:
        crew_state["status"] = "running"

    elif event.type == EventType.CREW_COMPLETE:
        crew_state["status"] = "complete"
        crew_state["progress"] = 100

    elif event.type == EventType.CREW_ERROR:
        crew_state["status"] = "error"

    elif event.type == EventType.TRAINING_START:
        crew_state["training"]["status"] = "training"
        crew_state["training"]["epochs_total"] = event.data.get("epochs", 0)

    elif event.type == EventType.TRAINING_PROGRESS:
        crew_state["training"]["epochs_done"] = event.data.get("epoch", 0)
        crew_state["training"]["loss"] = event.data.get("loss", None)

    elif event.type == EventType.TRAINING_COMPLETE:
        crew_state["training"]["status"] = "complete"


bus.on(update_state_from_event)

# ─── Telegram Bot (auto-start) ────────────────────────────────────────────
try:
    from factory_ai.telegram_bot import reporter as telegram_reporter
    telegram_reporter.start()
except Exception as e:
    print(f"[Server] Telegram bot failed to start: {e}")


# ─── WebSocket ─────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    queue = bus.subscribe()
    try:
        # Send current state immediately
        await ws.send_json({"type": "state", "data": crew_state})
        # Send recent history
        for event in bus.get_history(limit=20):
            await ws.send_text(event.to_json())
        # Stream live events
        while True:
            event = await queue.get()
            await ws.send_text(event.to_json())
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(queue)


# ─── REST API ──────────────────────────────────────────────────────────────
@app.get("/api/status")
async def get_status():
    return crew_state


@app.get("/api/events")
async def get_events(since_id: int = 0, limit: int = 50):
    events = bus.get_history(since_id=since_id, limit=limit)
    return [e.to_dict() for e in events]


@app.get("/api/zones")
async def get_zones():
    return ZONES


@app.get("/api/zones/props")
async def get_zone_props():
    """Get prop counts and details per zone from output/zones/*.json."""
    zones_dir = OUTPUT_DIR / "zones"
    result = {}
    for zname in ZONES:
        zone_file = zones_dir / f"{zname}.json"
        if zone_file.exists():
            try:
                props = json.loads(zone_file.read_text(encoding="utf-8"))
                prop_ids = {}
                for p in props:
                    pid = p.get("id", "?")
                    prop_ids[pid] = prop_ids.get(pid, 0) + 1
                result[zname] = {
                    "count": len(props),
                    "props": prop_ids,
                    "positions": [{"id": p["id"], "x": p["x"], "y": p["y"]} for p in props],
                }
            except Exception:
                result[zname] = {"count": 0, "props": {}, "positions": []}
        else:
            result[zname] = {"count": 0, "props": {}, "positions": []}
    return result


@app.get("/api/training/detail")
async def get_training_detail():
    """Detailed training info: dataset, adapter, GGUF, model."""
    from factory_ai.training import get_training_info
    info = get_training_info()
    info.update(crew_state["training"])
    # Add adapter checkpoint details
    adapter_dir = OUTPUT_DIR / "training" / "lora_adapter"
    checkpoints = sorted(adapter_dir.glob("checkpoint-*")) if adapter_dir.exists() else []
    info["checkpoints"] = [cp.name for cp in checkpoints]
    # Check for GGUF
    gguf_path = OUTPUT_DIR / "training" / "campus-expert.gguf"
    info["gguf_exists"] = gguf_path.exists()
    info["gguf_size_mb"] = round(gguf_path.stat().st_size / 1e6, 1) if gguf_path.exists() else 0
    # Check merged model
    merged = OUTPUT_DIR / "training" / "merged_model"
    info["merged_exists"] = merged.exists()
    return info


@app.get("/api/tile-mappings")
async def get_tile_mappings():
    """Get the prop ID → texture filename mappings."""
    mappings_file = OUTPUT_DIR / "tile_mappings.json"
    if mappings_file.exists():
        return json.loads(mappings_file.read_text(encoding="utf-8"))
    return {}


@app.get("/api/reviews")
async def get_pending_reviews():
    return pending_reviews


@app.post("/api/reviews/{event_id}")
async def submit_review(event_id: int, body: dict):
    """Submit a human review decision."""
    action = body.get("action", "approve")  # approve | reject | modify
    notes = body.get("notes", "")
    modifications = body.get("modifications", {})

    review_responses[event_id] = {
        "action": action,
        "notes": notes,
        "modifications": modifications,
    }

    # Remove from pending
    pending_reviews[:] = [r for r in pending_reviews if r["event_id"] != event_id]

    bus.emit(EventType.REVIEW_SUBMITTED, {
        "event_id": event_id,
        "action": action,
        "notes": notes,
    })

    # Signal the crew thread that review is done
    review_event.set()

    return {"status": "ok", "action": action}


@app.get("/api/outputs")
async def list_outputs():
    """List files in the output directory."""
    output_dir = OUTPUT_DIR
    if not output_dir.exists():
        return []
    files = []
    for f in sorted(output_dir.iterdir()):
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return files


@app.get("/api/outputs/{filename}")
async def get_output(filename: str):
    """Read a specific output file."""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(filepath)


@app.get("/api/training")
async def get_training_status():
    from factory_ai.training import get_training_info
    info = get_training_info()
    info.update(crew_state["training"])
    return info


@app.post("/api/training/start")
async def start_training(body: dict = {}):
    """Launch fine-tuning in a background thread."""
    if crew_state["training"]["status"] == "training":
        raise HTTPException(409, "Training already in progress")

    epochs = body.get("epochs", 3)

    def run_training():
        from factory_ai.training import run_training
        run_training(epochs=epochs)

    thread = threading.Thread(target=run_training, daemon=True)
    thread.start()
    return {"status": "started", "epochs": epochs}


@app.get("/api/system")
async def get_system_status():
    """System health: Ollama status, GPU, model info."""
    import subprocess
    info = {
        "ollama_url": OLLAMA_BASE_URL,
        "ollama_model": OLLAMA_MODEL,
        "ollama_running": False,
        "gpu_info": "unknown",
        "models_loaded": [],
    }
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        data = json.loads(resp.read())
        info["ollama_running"] = True
        info["models_loaded"] = [
            {"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 1)}
            for m in data.get("models", [])
        ]
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            info["gpu_info"] = r.stdout.strip()
    except Exception:
        info["gpu_info"] = "nvidia-smi not available"

    return info


@app.post("/api/crew/start")
async def start_crew():
    """Start the campus redesign crew in a background thread."""
    if crew_state["status"] == "running":
        raise HTTPException(409, "Crew is already running")

    def run_crew():
        try:
            # Callbacks are now wired directly on Task objects in campus_crew.py
            # No need to set crew.step_callback — that was WRONG
            from factory_ai.crews.campus_crew import campus_crew
            from factory_ai.crew_callbacks import DataCollector

            # Attach data collector for fine-tuning
            collector = DataCollector(OUTPUT_DIR)
            bus.on(collector.collect)
            crew_state["training"]["status"] = "collecting"

            bus.emit(EventType.CREW_START, {"agents": 5, "tasks": 5})
            result = campus_crew.kickoff()

            crew_state["training"]["examples_collected"] = collector.count
            bus.emit(EventType.CREW_COMPLETE, {
                "result_preview": str(result)[:500],
                "training_examples": collector.count,
            })
        except Exception as e:
            bus.emit(EventType.CREW_ERROR, {"error": str(e)})

    thread = threading.Thread(target=run_crew, daemon=True)
    thread.start()
    return {"status": "started"}


@app.post("/api/crew/stop")
async def stop_crew():
    """Signal crew to stop (best-effort)."""
    crew_state["status"] = "idle"
    bus.emit(EventType.CREW_ERROR, {"error": "Stopped by user"})
    return {"status": "stopped"}


# ─── Dashboard Frontend ───────────────────────────────────────────────────
DASHBOARD_DIR = Path(__file__).parent / "dashboard"

@app.get("/")
async def serve_dashboard():
    index = DASHBOARD_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard not built yet</h1>")


# Mount static files if directory exists
if DASHBOARD_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")

# Serve tile assets for the construction canvas
ASSETS_DIR = PROJECT_ROOT / "assets" / "tiles"
if ASSETS_DIR.exists():
    app.mount("/assets/tiles", StaticFiles(directory=str(ASSETS_DIR)), name="tiles")
