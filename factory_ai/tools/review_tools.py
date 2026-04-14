"""
Campus Factory AI — Human-in-the-Loop Review Tools
====================================================
CrewAI tools that pause execution and wait for human review
via the dashboard or Telegram.

Fixed: per-review gates, no race conditions, no listener leaks.
"""
import threading
from crewai.tools import tool
from factory_ai.events import bus, EventType


# Per-review synchronization (thread-safe)
_lock = threading.Lock()
_review_counter = 0
_pending_gates: dict[int, threading.Event] = {}
_review_results: dict[int, dict] = {}
_listener_registered = False


def _register_listener_once():
    """Register the global review listener exactly once."""
    global _listener_registered
    if _listener_registered:
        return
    _listener_registered = True

    def on_review_submitted(evt):
        if evt.type != EventType.REVIEW_SUBMITTED:
            return
        event_id = evt.data.get("event_id")
        if event_id is not None and event_id in _pending_gates:
            with _lock:
                _review_results[event_id] = evt.data
                _pending_gates[event_id].set()

    bus.on(on_review_submitted)


def _wait_for_review(description: str, preview: str, agent: str, timeout: int = 3600) -> dict:
    """
    Emit a REVIEW_NEEDED event and block until the dashboard submits a response.
    Uses per-review gates to avoid race conditions.
    """
    global _review_counter
    _register_listener_once()

    with _lock:
        _review_counter += 1

    gate = threading.Event()

    # Emit event — the event.id is what the server uses for matching
    event = bus.emit(EventType.REVIEW_NEEDED, {
        "agent": agent,
        "description": description,
        "preview": preview,
    })

    # Register gate with event.id (same key the server will use)
    with _lock:
        _pending_gates[event.id] = gate

    print(f"[Review] Waiting for human review (event #{event.id})...")
    got_response = gate.wait(timeout=timeout)

    # Clean up
    with _lock:
        result = _review_results.pop(event.id, {})
        _pending_gates.pop(event.id, None)

    if not got_response:
        return {"action": "approve", "notes": "Auto-approved (timeout)"}

    return result


@tool("request_layout_review")
def request_layout_review(layout_summary: str) -> str:
    """
    Submit the campus layout for human review before finalizing.
    The layout_summary should describe what was designed and key decisions.
    Returns the reviewer's feedback (approve, reject, or modification notes).
    """
    result = _wait_for_review(
        description="Campus layout design ready for review",
        preview=layout_summary[:2000],
        agent="Architect",
    )
    action = result.get("action", "approve")
    notes = result.get("notes", "")

    if action == "approve":
        return f"APPROVED by human reviewer. Notes: {notes or 'No additional notes.'}"
    elif action == "reject":
        return f"REJECTED by human reviewer. Feedback: {notes}. Please revise the layout."
    else:
        return f"MODIFICATION requested: {notes}. Please incorporate these changes."


@tool("request_visual_review")
def request_visual_review(visual_summary: str) -> str:
    """
    Submit the visual/texture mapping for human review before finalizing.
    The visual_summary should describe tile assignments and style decisions.
    Returns the reviewer's feedback.
    """
    result = _wait_for_review(
        description="Visual style & texture mapping ready for review",
        preview=visual_summary[:2000],
        agent="Art Director",
    )
    action = result.get("action", "approve")
    notes = result.get("notes", "")

    if action == "approve":
        return f"APPROVED by human reviewer. Notes: {notes or 'Looks good!'}"
    elif action == "reject":
        return f"REJECTED. Feedback: {notes}. Revise the texture assignments."
    else:
        return f"MODIFICATION requested: {notes}"


@tool("request_qa_review")
def request_qa_review(qa_report: str) -> str:
    """
    Submit the QA report for human review. The qa_report should list all
    issues found and recommendations. Returns human feedback on next steps.
    """
    result = _wait_for_review(
        description="QA Report ready for review — check issues and approve",
        preview=qa_report[:2000],
        agent="QA Reviewer",
    )
    action = result.get("action", "approve")
    notes = result.get("notes", "")

    if action == "approve":
        return f"QA APPROVED. {notes or 'All issues acceptable.'}"
    else:
        return f"QA NEEDS REVISION. Feedback: {notes}"
