"""Magnet link construction for Nyaa torrents."""
from urllib.parse import quote

MAGNET_TRACKERS: list[str] = [
    "http://nyaa.tracker.wf:7777/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.torrent.eu.org:451/announce",
]


def magnet_builder(info_hash: str, title: str) -> str:
    trackers = "".join(f"&tr={quote(t, safe = '')}" for t in MAGNET_TRACKERS)
    return f"magnet:?xt=urn:btih:{info_hash}&dn={quote(title, safe = '')}{trackers}"
