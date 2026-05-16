"""Nyaa.si episode and chapter search helpers."""
from collections.abc import Callable

from nyaa.types import TorrentSite, Torrent, SearchParams, SortField, SortOrder
from nyaa.search import search


def _anime_params(query: str) -> SearchParams:
    return SearchParams(
        keyword = query,
        filters = 0,
        category = 1,
        subcategory = 2,
        sort = SortField.SEEDERS,
        order = SortOrder.DESC,
    )


def _manga_params(query: str) -> SearchParams:
    return SearchParams(
        keyword = query,
        filters = 0,
        category = 3,
        subcategory = 1,
        sort = SortField.SEEDERS,
        order = SortOrder.DESC,
    )


def is_hevc(name: str) -> bool:
    lower = name.lower()
    return "hevc" in lower or "x265" in lower


def prefer_hevc(torrents: list[Torrent]) -> list[Torrent]:
    hevc = [t for t in torrents if is_hevc(t.name)]
    return hevc if hevc else torrents


def filter_submitters(torrents: list[Torrent], submitters: list[str]) -> list[Torrent]:
    if not submitters:
        return torrents
    lower = [s.lower() for s in submitters]
    filtered = [t for t in torrents if any(s in t.name.lower() for s in lower)]
    return filtered if filtered else torrents


async def _try_queries(queries: list[str], params_fn: Callable[[str], SearchParams]) -> list[Torrent]:
    for query in queries:
        try:
            results = await search(TorrentSite.NYAA_SI, params_fn(query))
            if results:
                return results
        except Exception:
            continue
    return []


async def search_episode(name: str, ep_num: int, submitters: list[str] | None = None) -> str | None:
    pad2 = f"{ep_num:02d}"
    pad3 = f"{ep_num:03d}"
    queries = [
        f"{name} - {pad2}",
        f"{name} - {pad3}",
        f"{name} {pad2}",
        f"{name} {pad3}",
    ]
    results = await _try_queries(queries, _anime_params)
    results = filter_submitters(results, submitters or [])
    preferred = prefer_hevc(results)
    return preferred[0].magnet if preferred else None


async def search_chapter(name: str, chapter_num: int, submitters: list[str] | None = None) -> str | None:
    pad3 = f"{chapter_num:03d}"
    pad2 = f"{chapter_num:02d}"
    queries = [
        f"{name} - Chapter {pad3}",
        f"{name} Chapter {pad3}",
        f"{name} {pad3}",
        f"{name} Chapter {pad2}",
    ]
    results = await _try_queries(queries, _manga_params)
    results = filter_submitters(results, submitters or [])
    return results[0].magnet if results else None
