"""
Campus Factory AI — Telegram Bot
=================================
Reports crew progress to a Telegram chat with INTERACTIVE review approval.

Features:
- Agent start/complete notifications
- Task completion summaries
- Interactive Approve/Reject buttons for reviews (InlineKeyboardMarkup)
- /status command to check crew progress
- Training status updates
- System health reports

Setup:
  1. Create bot via @BotFather → get token
  2. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env
  3. Bot auto-connects when server starts
"""
import asyncio
import json
import os
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# CRITICAL: Load .env BEFORE reading tokens
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from factory_ai.events import bus, EventType, Event
from factory_ai.config import OUTPUT_DIR

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8801"))

# Throttle: don't send more than 1 message per N seconds per event type
_last_sent: dict[str, float] = {}
THROTTLE_SECONDS = 5


def _should_send(event_type: str) -> bool:
    now = time.time()
    last = _last_sent.get(event_type, 0)
    if now - last < THROTTLE_SECONDS:
        return False
    _last_sent[event_type] = now
    return True


def _fmt_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return str(ts)[:8]


class TelegramReporter:
    """Listens to EventBus and sends formatted messages to Telegram.
    Runs a full Application for interactive button handling."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self._app = None
        self._loop = None
        self._thread = None

    def start(self):
        """Start the Telegram bot with interactive handlers in a background thread."""
        if not self.token or not self.chat_id:
            print("[Telegram] No TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID — bot disabled")
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        bus.on(self._on_event)
        print(f"[Telegram] Bot started, reporting to chat {self.chat_id}")

    def _run_loop(self):
        """Run async event loop with Application for interactive handlers."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            from telegram import Bot
            from telegram.ext import Application, CallbackQueryHandler, CommandHandler

            self._app = (
                Application.builder()
                .token(self.token)
                .build()
            )

            # Interactive handlers
            self._app.add_handler(CallbackQueryHandler(self._review_button_handler))
            self._app.add_handler(CommandHandler("status", self._status_command))
            self._app.add_handler(CommandHandler("help", self._help_command))

            # Start polling for button presses and commands
            self._loop.run_until_complete(self._app.initialize())
            self._loop.run_until_complete(self._app.start())
            self._loop.run_until_complete(
                self._app.updater.start_polling(drop_pending_updates=True)
            )
            print("[Telegram] Application polling started (interactive mode)")
            self._loop.run_forever()
        except Exception as e:
            print(f"[Telegram] Application failed, falling back to push-only: {e}")
            # Fallback: just run the event loop for push-only messages
            self._loop.run_forever()

    def _on_event(self, event: Event):
        """Sync callback from EventBus — schedules async send."""
        if not self._loop:
            return

        # DeerFlow AGENT_STEP events are rare — skip throttle for them
        is_deerflow = (
            event.type == EventType.AGENT_STEP
            and event.data.get("agent_name", event.data.get("agent", "")) == "DeerFlow"
        )
        if not is_deerflow and not _should_send(event.type.value):
            return

        # REVIEW_NEEDED gets special treatment — interactive buttons
        if event.type == EventType.REVIEW_NEEDED:
            asyncio.run_coroutine_threadsafe(
                self._send_review_request(event),
                self._loop,
            )
            return

        msg = self._format_event(event)
        if msg is None:
            return

        image_path = self._get_event_image(event)
        asyncio.run_coroutine_threadsafe(
            self._send(msg, image_path),
            self._loop,
        )

    # ─── Interactive Review ──────────────────────────────────────────────

    async def _send_review_request(self, event: Event):
        """Send review request with Approve/Reject inline buttons."""
        try:
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

            d = event.data
            event_id = event.id
            agent = d.get("agent", "?")
            description = d.get("description", "Output ready for review")
            preview = d.get("preview", "")[:500]

            text = (
                f"⚠️ *Review Needed*\n"
                f"Agent: *{agent}*\n"
                f"{description}\n"
            )
            if preview:
                text += f"\n```\n{preview[:300]}\n```\n"

            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve:{event_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject:{event_id}"),
                ],
                [
                    InlineKeyboardButton(
                        "📝 Approve with note",
                        callback_data=f"approve_note:{event_id}",
                    ),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            bot = self._app.bot if self._app else Bot(token=self.token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )

            # Also send image if available
            image_path = self._get_event_image(event)
            if image_path and image_path.exists():
                with open(image_path, "rb") as f:
                    await bot.send_photo(
                        chat_id=self.chat_id,
                        photo=f,
                        caption=f"Preview for review #{event_id}",
                    )

        except Exception as e:
            print(f"[Telegram] Error sending review request: {e}")

    async def _review_button_handler(self, update, context):
        """Handle Approve/Reject button presses from Telegram."""
        query = update.callback_query
        await query.answer()

        data = query.data
        if ":" not in data:
            return

        action, event_id_str = data.split(":", 1)
        try:
            event_id = int(event_id_str)
        except ValueError:
            await query.edit_message_text("Invalid review ID")
            return

        # Map button actions to review API actions
        if action == "approve_note":
            # For "approve with note", approve and mention they can add notes via dashboard
            api_action = "approve"
            notes = "(Approved via Telegram — add detailed notes in dashboard)"
        elif action in ("approve", "reject"):
            api_action = action
            notes = f"(Via Telegram by {query.from_user.first_name})"
        else:
            return

        # POST to the local review API
        success = await self._submit_review(event_id, api_action, notes)

        if success:
            emoji = "✅" if api_action == "approve" else "❌"
            await query.edit_message_text(
                f"{emoji} Review #{event_id}: *{api_action.upper()}*\n"
                f"By: {query.from_user.first_name}\n"
                f"{notes}",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                f"⚠️ Failed to submit review #{event_id}. "
                f"Dashboard may be unreachable."
            )

    async def _submit_review(self, event_id: int, action: str, notes: str) -> bool:
        """POST review decision to the FastAPI server."""
        def _do_post():
            url = f"http://localhost:{DASHBOARD_PORT}/api/reviews/{event_id}"
            payload = json.dumps({
                "action": action,
                "notes": notes,
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            return resp.status == 200

        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _do_post)
        except Exception as e:
            print(f"[Telegram] Review submit error: {e}")
            return False

    # ─── Commands ────────────────────────────────────────────────────────

    async def _status_command(self, update, context):
        """Handle /status command — show current crew progress."""
        try:
            def _fetch_status():
                url = f"http://localhost:{DASHBOARD_PORT}/api/status"
                resp = urllib.request.urlopen(url, timeout=5)
                return json.loads(resp.read())

            loop = asyncio.get_running_loop()
            state = await loop.run_in_executor(None, _fetch_status)

            status = state.get("status", "unknown")
            progress = state.get("progress", 0)
            tasks_done = state.get("tasks_completed", 0)
            tasks_total = state.get("tasks_total", 6)
            current_agent = state.get("current_agent", "none")
            events = state.get("events_count", 0)

            emoji_map = {
                "idle": "⏸", "running": "🏃", "paused_for_review": "⚠️",
                "complete": "🎉", "error": "❌",
            }
            emoji = emoji_map.get(status, "❓")

            bar_len = 10
            filled = int(bar_len * progress / 100)
            bar = "█" * filled + "░" * (bar_len - filled)

            text = (
                f"{emoji} *Campus Factory AI Status*\n\n"
                f"Status: `{status}`\n"
                f"Progress: [{bar}] {progress}%\n"
                f"Tasks: {tasks_done}/{tasks_total}\n"
                f"Current Agent: *{current_agent or 'none'}*\n"
                f"Events: {events}\n"
            )

            # Training info
            training = state.get("training", {})
            if training.get("status") != "idle":
                text += (
                    f"\n🧠 Training: `{training.get('status')}`\n"
                    f"Examples: {training.get('examples_collected', 0)}\n"
                )

            await update.message.reply_text(text, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Could not fetch status: `{e}`",
                parse_mode="Markdown",
            )

    async def _help_command(self, update, context):
        """Handle /help command."""
        text = (
            "🤖 *Campus Factory AI Bot*\n\n"
            "Commands:\n"
            "  /status — Current crew progress\n"
            "  /help — Show this message\n\n"
            "When a review is needed, tap the inline buttons "
            "to Approve or Reject directly from Telegram."
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    # ─── Event Formatting ────────────────────────────────────────────────

    def _format_event(self, event: Event) -> str | None:
        """Format event into a Telegram-friendly message. Returns None to skip."""
        t = event.type
        d = event.data

        if t == EventType.CREW_START:
            return (
                "🏗 *Campus Factory AI — Crew Started*\n"
                f"Agents: {d.get('agents', 6)} | Tasks: {d.get('tasks', 6)}\n"
                f"Time: {_fmt_time(event.timestamp)}"
            )

        elif t == EventType.AGENT_START:
            return f"🤖 Agent started: *{d.get('agent', '?')}*"

        elif t == EventType.TASK_COMPLETE:
            preview = d.get("result_preview", "")[:300]
            task = d.get("task", "?")
            return (
                f"✅ *Task Complete: {task}*\n"
                f"Agent: {d.get('agent', '?')}\n"
                f"```\n{preview}\n```"
            )

        # REVIEW_NEEDED handled separately with interactive buttons

        elif t == EventType.CREW_COMPLETE:
            return (
                "🎉 *Campus Factory AI — Crew Complete!*\n"
                f"Training examples: {d.get('training_examples', 0)}\n"
                f"Check `factory_ai/output/` for results"
            )

        elif t == EventType.CREW_ERROR:
            return f"❌ *Crew Error*\n`{d.get('error', 'Unknown error')}`"

        elif t == EventType.TRAINING_START:
            return (
                f"🧠 *Fine-tuning Started*\n"
                f"Epochs: {d.get('epochs', '?')}\n"
                f"Examples: {d.get('examples', '?')}"
            )

        elif t == EventType.TRAINING_PROGRESS:
            return (
                f"📊 Training epoch {d.get('epoch', '?')}/{d.get('epochs_total', '?')}\n"
                f"Loss: {d.get('loss', '--')}"
            )

        elif t == EventType.TRAINING_COMPLETE:
            return "🎓 *Fine-tuning Complete!* Model updated."

        elif t == EventType.AGENT_STEP:
            agent_name = d.get("agent_name", d.get("agent", ""))
            if agent_name == "DeerFlow":
                step_type = d.get("step_type", "")
                tool = d.get("tool", "")
                content = d.get("content", "")[:200]
                if step_type == "tool_call":
                    return (
                        f"🔍 *DeerFlow Deep Research Started*\n"
                        f"Tool: `{tool}`\n"
                        f"{content}\n"
                        f"⏳ This may take 5-10 min (multi-agent pipeline)"
                    )
                elif step_type == "finish":
                    return (
                        f"📋 *DeerFlow Research Complete*\n"
                        f"Tool: `{tool}`\n"
                        f"```\n{content}\n```"
                    )
            return None

        elif t == EventType.FILE_WRITTEN:
            return f"📄 File written: `{d.get('filename', '?')}`"

        return None

    def _get_event_image(self, event: Event) -> Path | None:
        """Check if event has an associated image to send."""
        if event.type in (EventType.REVIEW_NEEDED, EventType.CREW_COMPLETE):
            for pattern in ["*.png", "*.jpg", "*preview*"]:
                images = sorted(
                    OUTPUT_DIR.glob(pattern),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if images:
                    return images[0]
        return None

    async def _send(self, text: str, image_path: Path | None = None):
        """Send message (and optionally image) to Telegram."""
        try:
            bot = self._app.bot if self._app else None
            if not bot:
                from telegram import Bot
                bot = Bot(token=self.token)

            if image_path and image_path.exists():
                with open(image_path, "rb") as f:
                    await bot.send_photo(
                        chat_id=self.chat_id,
                        photo=f,
                        caption=text[:1024],
                        parse_mode="Markdown",
                    )
            else:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode="Markdown",
                )
        except Exception as e:
            print(f"[Telegram] Send error: {e}")


# Global instance
reporter = TelegramReporter(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
