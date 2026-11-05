import json
import logging
from pathlib import Path

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from core.queue import PENDING, scan_pending
from core.scheduler import PLATFORM_NAMES, process_item

log = logging.getLogger("bot")

ADMIN_FILE = Path(__file__).resolve().parent.parent / "data" / "admin.json"


def load_admin_chat() -> int | None:
    if ADMIN_FILE.exists():
        try:
            return int(json.loads(ADMIN_FILE.read_text(encoding="utf-8")).get("chat_id"))
        except (ValueError, json.JSONDecodeError):
            pass
    return None


def save_admin_chat(chat_id: int):
    ADMIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_FILE.write_text(json.dumps({"chat_id": chat_id}), encoding="utf-8")


class Notifier:
    def __init__(self, bot: Bot | None):
        self.bot = bot

    async def notify(self, text: str):
        chat = load_admin_chat()
        if self.bot and chat:
            try:
                await self.bot.send_message(chat, text)
            except Exception:
                log.exception("Failed to notify admin")


def build_router(services: dict, cfg, notifier: Notifier | None = None) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        if not message.chat.type == "private":
            return
        save_admin_chat(message.chat.id)
        await message.answer("Control panel ready. Commands: /status, /queue, /post <slug>")

    @router.message(Command("status"))
    async def cmd_status(message: Message):
        if message.chat.id != load_admin_chat():
            return
        enabled = ", ".join(PLATFORM_NAMES.get(p, p) for p in sorted(services)) or "none"
        items = scan_pending()
        due = sum(1 for i in items if i.is_due())
        await message.answer(
            f"Adapters enabled: {enabled}\n"
            f"Queue: {len(items)} pending ({due} due now)\n"
            f"Poll interval: {cfg.poll_interval_seconds}s"
        )

    @router.message(Command("queue"))
    async def cmd_queue(message: Message):
        if message.chat.id != load_admin_chat():
            return
        items = scan_pending()
        if not items:
            await message.answer("Queue is empty.")
            return
        lines = []
        for item in items:
            platforms = ", ".join(PLATFORM_NAMES.get(p, p) for p in item.platforms) or "-"
            when = f"{item.scheduled_at:%Y-%m-%d %H:%M}"
            flag = " (due)" if item.is_due() else ""
            image = " +img" if item.image else ""
            lines.append(f"- {item.slug} [{when}{flag}] {platforms}{image}")
        await message.answer("\n".join(lines))

    @router.message(Command("post"))
    async def cmd_post(message: Message, command: CommandObject):
        if message.chat.id != load_admin_chat():
            return
        slug = (command.args or "").strip()
        if not slug:
            await message.answer("Usage: /post <slug>")
            return
        item = next((i for i in scan_pending() if i.slug == slug), None)
        if item is None:
            await message.answer(f"No queued item named {slug!r}.")
            return
        await message.answer(f"Posting {item.slug}...")
        ok, results = await process_item(item, services, notifier, cfg.default_platforms)
        report = "\n".join(f"{PLATFORM_NAMES.get(p, p)}: {v}" for p, v in results.items())
        await message.answer(f"{'OK' if ok else 'FAILED'}\n{report}")

    return router