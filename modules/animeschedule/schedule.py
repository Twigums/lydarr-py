"""AnimeSchedule API: search, fetch by name, and current season schedule."""
from datetime import datetime, timezone

import re

from rapidfuzz.distance import Levenshtein

from animeschedule.types import (
    AnimeDetail, EpisodeRecord, CurrentEntry, NotFoundError,
)
from animeschedule.models import AnimeJson, AnimePage, to_anime_detail, to_anime_summary
from animeschedule.endpoints import anime_list_url, anime_slug_url
from animeschedule.http import get_json_no_auth
from animeschedule.episodes import compute_episodes, next_episode
from animeschedule.season import current_season, season_slug


async def search_anime(query: str) -> list[AnimeJson]:
    data = await get_json_no_auth(anime_list_url(), params = {"q": query})
    return AnimePage.from_dict(data).anime


def _word_tokens(s: str) -> list[str]:
    return re.sub(r"[^\w\s]", "", s.lower()).split()


def _word_similarity(a: str, b: str) -> float:
    wa, wb = _word_tokens(a), _word_tokens(b)
    if not wa or not wb:
        return 0.0
    return 1.0 - Levenshtein.distance(wa, wb) / max(len(wa), len(wb))


def find_best_match(query: str, candidates: list[AnimeJson]) -> AnimeJson | None:
    q = query.lower()
    exact = next((a for a in candidates if a.title.lower() == q), None)
    if exact:
        return exact
    sub = next((a for a in candidates if q in a.title.lower() or a.title.lower() in q), None)
    if sub:
        return sub
    best = max(candidates, key = lambda a: _word_similarity(query, a.title), default = None)
    if best and _word_similarity(query, best.title) >= 0.6:
        return best
    return None


async def fetch_by_name(name: str) -> tuple[AnimeDetail, list[EpisodeRecord]]:
    candidates = await search_anime(name)
    if not candidates:
        raise NotFoundError(f"No anime found matching: {name}")

    hit = find_best_match(name, candidates)
    if hit is None:
        titles = ", ".join(a.title for a in candidates)
        raise NotFoundError(f"No close match for: {name}. Found: {titles}")

    data = await get_json_no_auth(anime_slug_url(hit.route))
    detail = to_anime_detail(AnimeJson.from_dict(data))
    return detail, compute_episodes(detail)


async def _fetch_all_pages(slug: str) -> list[AnimeJson]:
    results: list[AnimeJson] = []
    page = 1
    while True:
        params = {"seasons": slug, "airing-statuses": "ongoing", "page": page}
        data = await get_json_no_auth(anime_list_url(), params = params)
        pg = AnimePage.from_dict(data)
        results.extend(pg.anime)
        if len(results) >= pg.total_amount or not pg.anime:
            break
        page += 1
    return results


async def fetch_current_schedule() -> list[CurrentEntry]:
    now = datetime.now(tz = timezone.utc)
    season, year = current_season(now)
    slug = season_slug(season, year)

    animes = await _fetch_all_pages(slug)
    entries: list[CurrentEntry] = []
    for aj in animes:
        summary = to_anime_summary(aj)
        if summary.premier is None or summary.jpn_time is None:
            continue
        ep_num, ep_utc = next_episode(summary.premier, summary.jpn_time, now)
        entries.append(CurrentEntry(title = summary.title, ep_num = ep_num, utc = ep_utc))
    return entries
