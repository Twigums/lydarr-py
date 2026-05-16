"""Public search API for Nyaa.si."""
from nyaa.types import TorrentSite, Torrent, TorrentDetail, SearchParams
from nyaa.http import (
    fetch_listing, fetch_view, fetch_user_page,
    fetch_search_rss, fetch_search_html,
)
from nyaa.parser.rss import parse_nyaa_rss
from nyaa.parser.html import parse_nyaa, parse_single


async def last_uploads(site: TorrentSite, limit: int | None = None) -> list[Torrent]:
    data = await fetch_listing(site)
    return parse_nyaa(site, data, limit)


async def search(site: TorrentSite, params: SearchParams) -> list[Torrent]:
    if params.user:
        data = await fetch_search_html(site, params)
        return parse_nyaa(site, data)
    data = await fetch_search_rss(site, params)
    return parse_nyaa_rss(site, data)


async def get_torrent(site: TorrentSite, vid: int) -> TorrentDetail:
    data = await fetch_view(site, vid)
    return parse_single(site, data)


async def get_from_user(
    site: TorrentSite, username: str, limit: int | None = None
) -> list[Torrent]:
    data = await fetch_user_page(site, username)
    return parse_nyaa(site, data, limit)
