import json
from pathlib import Path
import sys

import browser_cookie3

def _username_from_config() -> str:
    path = Path("config.json")
    if not path.exists():
        print("config.json missing - copy config.example.json to config.json and set instagram.username", file=sys.stderr)
        raise SystemExit(1)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    name = cfg.get("instagram", {}).get("username")
    if not name:
        print("instagram.username not set in config.json", file=sys.stderr)
        raise SystemExit(1)
    return name


USERNAME = _username_from_config()


def grab_cookies():
    for name, loader in (
        ("chrome", browser_cookie3.chrome),
        ("edge", browser_cookie3.edge),
        ("brave", browser_cookie3.brave),
        ("firefox", browser_cookie3.firefox),
    ):
        try:
            result = loader(domain_name="instagram.com")
            if isinstance(result, tuple):
                cj, errors = result
            else:
                cj, errors = result, []
            for cookie in cj:
                if cookie.name == "sessionid":
                    return cookie.value
            if errors:
                print(f"{name}: {errors[0] if errors else 'no cookies'}", file=sys.stderr)
        except Exception as e:
            print(f"{name}: {e}", file=sys.stderr)
    return None


if __name__ == "__main__":
    sid = grab_cookies()
    if not sid:
        print("NO_SESSIONID", file=sys.stderr)
        sys.exit(1)
    from instagrapi import Client

    cl = Client(delay_range=[1, 2])
    cl.set_sessionid(sid)
    me = cl.account_info()
    print(json.dumps({"username": me.username, "full_name": me.full_name, "pk": me.pk, "media": me.media_count}, indent=2))
    cl.dump_settings(f"sessions/{USERNAME}.json")
    print(f"Session saved to sessions/{USERNAME}.json")