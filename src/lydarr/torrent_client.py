"""Transmission JSON-RPC client."""
import asyncio

import httpx

POLL_INTERVAL = 5

_session_id = "0"
_session_lock = asyncio.Lock()


async def _rpc(url: str, user: str | None, password: str | None, method: str, arguments: dict | None = None) -> httpx.Response:
    global _session_id
    payload = {"method": method, "arguments": arguments or {}}
    auth = (user, password) if user else None
    async with httpx.AsyncClient() as client:
        async with _session_lock:
            r = await client.post(
                url, json = payload,
                headers = {"X-Transmission-Session-Id": _session_id},
                auth = auth,
                timeout = 10,
            )
            if r.status_code == 409:
                _session_id = r.headers.get("X-Transmission-Session-Id", "0")
                r = await client.post(
                    url, json = payload,
                    headers = {"X-Transmission-Session-Id": _session_id},
                    auth = auth,
                    timeout = 10,
                )
        return r


async def is_client_up(url: str, user: str | None, password: str | None) -> bool:
    try:
        r = await _rpc(url, user, password, "session-get")
        return r.status_code == 200
    except Exception:
        return False


async def wait_for_client(url: str, user: str | None, password: str | None) -> None:
    print("Waiting for Transmission...")
    while not await is_client_up(url, user, password):
        print(f"Transmission not reachable at {url}. Retrying in {POLL_INTERVAL}s.")
        await asyncio.sleep(POLL_INTERVAL)
    print("Transmission is up.")


async def add_magnet(url: str, user: str | None, password: str | None, magnet: str, download_dir: str | None = None) -> bool:
    args: dict = {"filename": magnet}
    if download_dir:
        args["download-dir"] = download_dir
    try:
        r = await _rpc(url, user, password, "torrent-add", args)
        if r.status_code != 200:
            return False
        result = r.json().get("result", "")
        return result in ("success", "duplicate torrent")
    except Exception as exc:
        print(f"[torrent_client] add_magnet error: {exc}")
        return False
