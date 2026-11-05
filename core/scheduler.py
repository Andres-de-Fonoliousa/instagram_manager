import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.queue import mark_failed, mark_posted, scan_pending

log = logging.getLogger("scheduler")

PLATFORM_NAMES = {"ig": "Instagram", "tg": "Telegram", "tw": "Twitter/X"}


def make_services(cfg, bot=None) -> dict:
    from adapters.instagram import InstagramPoster
    from adapters.telegram import TelegramPoster

    services: dict = {}
    if cfg.instagram.get("username"):
        services["ig"] = InstagramPoster(cfg.instagram["username"])
    if cfg.telegram.get("channel") and bot is not None:
        services["tg"] = TelegramPoster(bot, cfg.telegram["channel"])
    return services


async def process_item(item, services: dict, notifier=None, default_platforms: str = "") -> tuple[bool, dict]:
    results: dict[str, str] = {}
    failures: list[str] = []
    platforms = item.platforms or [
        p.strip().lower() for p in (default_platforms or "").split(",") if p.strip()
    ]
    for platform in platforms:
        service = services.get(platform)
        if service is None:
            results[platform] = "skipped (not configured)"
            continue
        try:
            url = await service.apost(str(item.image) if item.image else "", item.caption_for(platform))
            results[platform] = url
            log.info("%s: posted %s -> %s", platform, item.slug, url)
        except Exception as e:
            log.exception("%s: posting %s failed", platform, item.slug)
            results[platform] = f"FAILED: {e}"
            failures.append(platform)

    ok = not failures
    report = "\n".join(f"{PLATFORM_NAMES.get(p, p)}: {v}" for p, v in results.items())
    log.info("%s %s:\n%s", "OK" if ok else "FAILED", item.slug, report)
    if ok:
        mark_posted(item, report)
    else:
        mark_failed(item, report)
    if notifier:
        await notifier(f"{'OK' if ok else 'FAILED'} {item.slug}\n{report}")
    return ok, results


async def tick(services: dict, notifier=None, default_platforms: str = ""):
    for item in scan_pending():
        if not item.is_due():
            continue
        try:
            await process_item(item, services, notifier, default_platforms)
        except Exception:
            log.exception("Processing %s failed", item.slug)


def build_scheduler(services: dict, notifier=None, cfg=None) -> AsyncIOScheduler:
    from tzlocal import get_localzone

    poll = cfg.poll_interval_seconds if cfg else 60
    defaults = cfg.default_platforms if cfg else ""
    scheduler = AsyncIOScheduler(timezone=get_localzone())
    scheduler.add_job(tick, "interval", seconds=poll, args=[services, notifier, defaults])
    return scheduler