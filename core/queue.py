import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tzlocal import get_localzone

log = logging.getLogger("queue")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONTENT_DIR = ROOT / "content"
PENDING = CONTENT_DIR / "pending"
POSTED = CONTENT_DIR / "posted"
FAILED = CONTENT_DIR / "failed"
for d in (DATA_DIR, PENDING, POSTED, FAILED):
    d.mkdir(parents=True, exist_ok=True)

LOCAL_TZ = get_localzone()

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_DATE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")
_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FRONT_RE.match(text)
    meta: dict = {}
    body = text.strip()
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
        body = text[m.end():].strip()
    return meta, body


def parse_dt(value: str) -> datetime:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=LOCAL_TZ)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {value!r} (use e.g. 2026-08-15 10:00)")


@dataclass
class ContentItem:
    slug: str
    folder: Path
    meta: dict
    caption: str
    image: Path | None
    platforms: list[str]
    scheduled_at: datetime

    def caption_for(self, platform: str) -> str:
        return self.meta.get(f"caption_{platform}", self.caption)

    def is_due(self, now: datetime | None = None) -> bool:
        return self.scheduled_at <= (now or datetime.now(LOCAL_TZ))


def load_item(folder: Path) -> ContentItem:
    md = folder / "post.md"
    if not md.exists():
        raise ValueError(f"{folder.name}: missing post.md")
    meta, body = parse_frontmatter(md.read_text(encoding="utf-8"))
    image = next(
        (p for p in sorted(folder.iterdir()) if p.suffix.lower() in IMAGE_SUFFIXES),
        None,
    )
    platforms = [p.strip().lower() for p in meta.get("platforms", "").split(",") if p.strip()]
    scheduled_at = parse_dt(meta["date"]) if meta.get("date") else datetime.now(LOCAL_TZ)
    return ContentItem(
        slug=folder.name,
        folder=folder,
        meta=meta,
        caption=body,
        image=image,
        platforms=platforms,
        scheduled_at=scheduled_at,
    )


def scan_pending() -> list[ContentItem]:
    items = []
    for folder in sorted(PENDING.iterdir()):
        if not folder.is_dir() or not (folder / "post.md").exists():
            continue
        try:
            items.append(load_item(folder))
        except ValueError as e:
            log.warning("Skipping invalid item: %s", e)
    return items


def enqueue(source_md: Path, image: Path | None, name: str | None = None) -> ContentItem:
    slug = name or source_md.stem
    dest = PENDING / slug
    if dest.exists():
        raise ValueError(f"Queue item already exists: {slug}")
    dest.mkdir(parents=True)
    shutil.copy2(source_md, dest / "post.md")
    if image:
        shutil.copy2(image, dest / image.name)
    log.info("Queued %s", slug)
    return load_item(dest)


def _write_report(item: ContentItem, report: str):
    (item.folder / "report.txt").write_text(report, encoding="utf-8")


def mark_posted(item: ContentItem, report: str):
    _write_report(item, report)
    ts = datetime.now(LOCAL_TZ).strftime("%Y%m%d_%H%M%S")
    item.folder.rename(POSTED / f"{item.slug}__{ts}")
    log.info("Marked posted: %s", item.slug)


def mark_failed(item: ContentItem, report: str):
    _write_report(item, report)
    dest = FAILED / item.slug
    if dest.exists():
        shutil.rmtree(dest)
    item.folder.rename(dest)
    log.error("Moved to failed: %s", item.slug)