import asyncio
import json
import sys

import aiohttp


async def find_page(port: int):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"http://127.0.0.1:{port}/json/list", timeout=3) as r:
            targets = await r.json()
    for t in targets:
        if t.get("type") == "page":
            return t
    return None


async def close_browser(port: int = 9222) -> bool:
    target = await find_page(port)
    if not target:
        return False
    async with aiohttp.ClientSession() as s:
        ws = await s.ws_connect(target["webSocketDebuggerUrl"], timeout=10)
        await ws.send_str(json.dumps({"id": 1, "method": "Browser.close"}))
        try:
            await ws.receive(timeout=5)
        except Exception:
            pass
    return True


async def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
    ok = await close_browser(port)
    if not ok:
        print(f"No debug Chrome on port {port}.", file=sys.stderr)
        return 1
    print(f"Graceful close sent on port {port}.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
