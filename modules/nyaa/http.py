"""Async HTTP fetchers for Nyaa.si pages and feeds."""
import httpx

from nyaa.types import TorrentSite, SearchParams, HttpError


async def _get(url: str, params: dict | None = None) -> bytes:
    try:
        async with httpx.AsyncClient(follow_redirects = True, timeout = httpx.Timeout(10, read = 30)) as client:
            response = await client.get(url, params = params)
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as exc:
        raise HttpError(str(exc)) from exc


async def fetch_listing(site: TorrentSite) -> bytes:
    return await _get(site.base_url)


async def fetch_view(site: TorrentSite, vid: int) -> bytes:
    return await _get(f"{site.base_url}/view/{vid}")


async def fetch_user_page(site: TorrentSite, username: str) -> bytes:
    return await _get(f"{site.base_url}/user/{username}")


async def fetch_search_rss(site: TorrentSite, params: SearchParams) -> bytes:
    query = {
        "f": params.filters,
        "c": params.category_param,
        "q": params.keyword,
        "s": params.sort.value,
        "o": params.order.value,
        "page": "rss",
    }
    return await _get(site.base_url, params = query)


async def fetch_search_html(site: TorrentSite, params: SearchParams) -> bytes:
    username = params.user or ""
    query: dict = {
        "f": params.filters,
        "c": params.category_param,
        "q": params.keyword,
        "s": params.sort.value,
        "o": params.order.value,
    }
    if params.page > 0:
        query["p"] = params.page
    return await _get(f"{site.base_url}/user/{username}", params = query)
