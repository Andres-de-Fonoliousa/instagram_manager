import argparse
import asyncio
import json
from pathlib import Path
import os
import sys
import time

import aiohttp

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
PORT = 9222
DEBUG_URL = f"http://127.0.0.1:{PORT}"

parser = argparse.ArgumentParser(
    description="Grab the Instagram session from the live debug Chrome (port 9222)."
)
parser.add_argument(
    "--keep-open",
    action="store_true",
    help="Leave Chrome open after saving (default: close it gracefully so the IG login survives)",
)
args = parser.parse_args()


async def req(ws, m, p=None, timeout=20):
    rid = getattr(ws, "_rid", 0) + 1
    ws._rid = rid
    await ws.send_str(json.dumps({"id": rid, "method": m, "params": p or {}}))
    while True:
        raw = await asyncio.wait_for(ws.receive(), timeout=timeout)
        if raw.type != aiohttp.WSMsgType.TEXT:
            continue
        d = json.loads(raw.data)
        if d.get("id") == rid:
            if "error" in d:
                raise RuntimeError(f"{m}: {d['error']}")
            return d.get("result", {})


async def ev(ws, expr, timeout=15):
    d = await req(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True}, timeout)
    res = d.get("result", {})
    if res.get("exceptionDetails"):
        raise RuntimeError(json.dumps(res["exceptionDetails"])[:200])
    return res.get("result", {}).get("value")


async def find_worker(session):
    for _ in range(30):
        try:
            async with session.get(f"{DEBUG_URL}/json/list", timeout=3) as r:
                targets = await r.json()
            ig = next((x for x in targets if x.get("type") == "page"
                       and "instagram.com" in x.get("url", "")), None)
            if ig:
                return ig
            http = next((x for x in targets if x.get("type") == "page"
                         and x.get("url", "").startswith("http")), None)
            if http:
                return http
        except Exception:
            pass
        await asyncio.sleep(2)
    raise RuntimeError("No Chrome tab available — is the debug browser running?")


async def main():
    async with aiohttp.ClientSession() as s:
        worker = await find_worker(s)
        async with s.ws_connect(worker["webSocketDebuggerUrl"],
                                max_msg_size=2**26, timeout=30) as ws:
            await req(ws, "Runtime.enable")
            await req(ws, "Network.enable")
            await req(ws, "Page.navigate", {"url": "https://www.instagram.com/"})
            print("Instagram opened in the Chrome window. Log in there if asked.")

            deadline = time.time() + 240
            sessionid = None
            while time.time() < deadline:
                try:
                    res = await req(ws, "Network.getAllCookies", None, 15)
                except asyncio.TimeoutError:
                    continue
                for c in res.get("cookies", []):
                    dom = c.get("domain", "")
                    if "instagram.com" in dom and c.get("name") == "sessionid":
                        v = c.get("value", "")
                        if v and "not_found" not in v:
                            exp = c.get("expirationDate")
                            exp = (f"expires {time.strftime('%Y-%m-%d %H:%M', time.localtime(exp))}"
                                   if exp else "SESSION cookie (no expiry — dies on browser close)")
                            print(f"GOT sessionid — {exp}")
                            sessionid = v
                            break
                if sessionid:
                    break
                left = int(deadline - time.time())
                print(f"waiting for login... ({left}s)")
                await asyncio.sleep(5)

            if not sessionid:
                print("Timed out waiting for login.")
                return 1

            from instagrapi import Client
            cl = Client(delay_range=[1, 2])
            cl.login_by_sessionid(sessionid)
            me = cl.account_info()
            print(json.dumps({"username": me.username, "full_name": me.full_name,
                              "pk": me.pk}, indent=2))
            os.makedirs("sessions", exist_ok=True)
            cl.dump_settings(f"sessions/{USERNAME}.json")
            print(f"Session saved to sessions/{USERNAME}.json")
            if not args.keep_open:
                print("Closing Chrome gracefully (cookies flushed, IG login preserved)...")
                try:
                    await req(ws, "Browser.close")
                except Exception as e:
                    print(f"Note: auto-close failed ({e}). Close Chrome normally — "
                          f"never force-kill it, that wipes the IG login.")
    return 0


sys.exit(asyncio.run(main()))