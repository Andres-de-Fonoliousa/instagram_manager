import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("config")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"


@dataclass
class Config:
    timezone: str = "Asia/Damascus"
    poll_interval_seconds: int = 60
    default_platforms: str = "ig, tg"
    instagram: dict = field(default_factory=dict)
    telegram: dict = field(default_factory=dict)
    twitter: dict = field(default_factory=dict)


def load_config() -> Config:
    if not CONFIG_PATH.exists():
        log.error("config.json missing. Copy config.example.json -> config.json and fill in tokens.")
        raise SystemExit(1)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        log.error("config.json is not valid JSON: %s", e)
        raise SystemExit(1)
    return Config(**data)