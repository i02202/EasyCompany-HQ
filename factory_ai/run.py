#!/usr/bin/env python3
"""
Campus Factory AI — Entry Point
================================
Launches the full system:
  - FastAPI dashboard server (port 8420)
  - WebSocket event streaming
  - Telegram bot (if configured)
  - Crew starts via dashboard button or CLI flag

Usage:
    python -m factory_ai.run              # Start dashboard only
    python -m factory_ai.run --auto       # Start dashboard + auto-launch crew
    python -m factory_ai.run --crew-only  # Run crew without dashboard
"""
import sys
import os
import argparse
from pathlib import Path

# Fix Windows encoding BEFORE any imports that might print emoji
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)


def main():
    parser = argparse.ArgumentParser(description="Campus Factory AI")
    parser.add_argument("--auto", action="store_true", help="Auto-start crew on launch")
    parser.add_argument("--crew-only", action="store_true", help="Run crew without dashboard")
    parser.add_argument("--port", type=int, default=8420, help="Dashboard port")
    parser.add_argument("--train", action="store_true", help="Run training after crew completes")
    args = parser.parse_args()

    if args.crew_only:
        from factory_ai.crews.campus_crew import run
        result = run()
        print("\nFinal Result:")
        print(result)
        if args.train:
            from factory_ai.training import run_training
            run_training()
        return

    # Start Telegram bot
    try:
        from factory_ai.telegram_bot import reporter
        reporter.start()
    except Exception as e:
        print(f"[Telegram] Bot not started: {e}")

    # Auto-start crew if requested
    if args.auto:
        import threading
        from factory_ai.events import bus, EventType

        def auto_crew():
            import time
            time.sleep(2)  # Wait for server to start
            bus.emit(EventType.CREW_START, {"agents": 5, "tasks": 5})
            from factory_ai.crews.campus_crew import campus_crew
            from factory_ai.crew_callbacks import step_callback, task_callback, DataCollector
            from factory_ai.config import OUTPUT_DIR

            campus_crew.step_callback = step_callback
            campus_crew.task_callback = task_callback

            collector = DataCollector(OUTPUT_DIR)
            bus.on(collector.collect)

            try:
                result = campus_crew.kickoff()
                bus.emit(EventType.CREW_COMPLETE, {
                    "result_preview": str(result)[:500],
                    "training_examples": collector.count,
                })
                if args.train:
                    from factory_ai.training import run_training
                    run_training()
            except Exception as e:
                bus.emit(EventType.CREW_ERROR, {"error": str(e)})

        threading.Thread(target=auto_crew, daemon=True).start()

    # Start dashboard server
    import uvicorn
    print("=" * 60)
    print("  CAMPUS FACTORY AI — Dashboard")
    print(f"  http://localhost:{args.port}")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    uvicorn.run("factory_ai.server:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    main()
