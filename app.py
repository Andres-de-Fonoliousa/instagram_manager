import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.control import Notifier, build_router
from core.config import load_config
from core.scheduler import build_scheduler, make_services

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("instagrapi").setLevel(logging.INFO)
log = logging.getLogger("app")


async def main():
    cfg = load_config()
    bot = Bot(cfg.telegram["bot_token"]) if cfg.telegram.get("bot_token") else None
    services = make_services(cfg, bot)
    notifier = Notifier(bot)

    scheduler = build_scheduler(services, notifier, cfg)
    scheduler.start()
    log.info("Scheduler started (%ss poll). Enabled adapters: %s",
             cfg.poll_interval_seconds, ", ".join(sorted(services)) or "none")

    if not bot:
        log.warning("No telegram bot_token in config — running scheduler only. Ctrl+C to stop.")
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            scheduler.shutdown(wait=False)
        return

    dp = Dispatcher()
    dp.include_router(build_router(services, cfg, notifier))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())