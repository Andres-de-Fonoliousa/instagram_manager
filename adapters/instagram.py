import asyncio
import logging
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired
import instagrapi.config as ig_config

log = logging.getLogger("ig")

IG_APP_VERSION = {
    "app_version": "442.0.0.46.79",
    "version_code": "384810185",
    "bloks_versioning_id": "7189b949425f9bf80ea8bd880cf5a3080b292d9b1c4b38a18d112f7c4b71e7a8",
}
ig_config.DEFAULT_APP_VERSION = IG_APP_VERSION["app_version"]
ig_config.APP_SETTINGS = {IG_APP_VERSION["app_version"]: IG_APP_VERSION, **ig_config.APP_SETTINGS}

ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def session_path(username: str) -> Path:
    return SESSIONS_DIR / f"{username}.json"


def login(username: str, password: str, code: str | None = None) -> Client:
    cl = Client(delay_range=[1, 2])
    cl.login(username, password, verification_code=code)
    cl.dump_settings(session_path(username))
    return cl


def load_client(username: str) -> Client:
    cl = Client(delay_range=[1, 2])
    path = session_path(username)
    if not path.exists():
        log.error("No session for @%s. Run: python main.py login -u %s", username, username)
        raise SystemExit(1)
    cl.load_settings(path)
    try:
        cl.get_timeline_feed()
    except LoginRequired:
        log.error(
            "Session for @%s expired. Re-login: python main.py login -u %s (delete %s first)",
            username, username, path,
        )
        raise SystemExit(1)
    return cl


class InstagramPoster:
    def __init__(self, username: str):
        self.username = username
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = load_client(self.username)
        return self._client

    def post(self, image_path: str, caption: str) -> str:
        media = self.client.photo_upload(image_path, caption)
        return f"https://www.instagram.com/p/{media.code}/"

    async def apost(self, image_path: str, caption: str) -> str:
        return await asyncio.to_thread(self.post, image_path, caption)