import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from animeschedule.types import AirStatus, NotFoundError
from animeschedule.models import AnimeJson, to_anime_detail


SOLO_LEVELING_JSON = {
    "title": "Solo Leveling Season 2 -Arise from the Shadow-",
    "route": "solo-leveling-s2",
    "status": "Finished",
    "premier": "2025-01-04T15:00:00Z",
    "subPremier": "2025-01-04T17:30:00Z",
    "dubPremier": None,
    "jpnTime": "2025-01-04T15:00:00Z",
    "subTime": "2025-01-04T17:30:00Z",
    "dubTime": None,
    "episodes": 25,
}

PAGE_RESPONSE = {
    "page": 1,
    "totalAmount": 1,
    "anime": [SOLO_LEVELING_JSON],
}


@pytest.mark.asyncio
async def test_search_anime_returns_list():
    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, return_value = PAGE_RESPONSE):
        from animeschedule.schedule import search_anime
        results = await search_anime("Solo Leveling")

    assert len(results) == 1
    assert results[0].title == "Solo Leveling Season 2 -Arise from the Shadow-"


@pytest.mark.asyncio
async def test_search_anime_empty():
    empty_page = {"page": 1, "totalAmount": 0, "anime": []}
    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, return_value = empty_page):
        from animeschedule.schedule import search_anime
        results = await search_anime("Nonexistent Anime XYZ")

    assert results == []


def test_find_best_match_exact():
    from animeschedule.schedule import find_best_match
    candidates = [
        AnimeJson.from_dict({**SOLO_LEVELING_JSON, "title": "Solo Leveling"}),
        AnimeJson.from_dict({**SOLO_LEVELING_JSON, "title": "Solo Leveling Season 2 -Arise from the Shadow-"}),
    ]
    result = find_best_match("solo leveling", candidates)
    assert result is not None
    assert result.title == "Solo Leveling"


def test_find_best_match_partial():
    from animeschedule.schedule import find_best_match
    candidates = [
        AnimeJson.from_dict({**SOLO_LEVELING_JSON, "title": "Solo Leveling Season 2 -Arise from the Shadow-"}),
    ]
    result = find_best_match("Solo Leveling", candidates)
    assert result is not None
    assert "Solo Leveling" in result.title


def test_find_best_match_none():
    from animeschedule.schedule import find_best_match
    candidates = [
        AnimeJson.from_dict({**SOLO_LEVELING_JSON, "title": "Totally Different Anime"}),
    ]
    result = find_best_match("Solo Leveling", candidates)
    assert result is None


@pytest.mark.asyncio
async def test_fetch_by_name_success():
    detail_json = {**SOLO_LEVELING_JSON}

    async def mock_get_json(url, params = None):
        if "anime" in url and "solo-leveling" in url:
            return detail_json
        return PAGE_RESPONSE

    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, side_effect = mock_get_json):
        from animeschedule.schedule import fetch_by_name
        detail, episodes = await fetch_by_name("Solo Leveling Season 2 -Arise from the Shadow-")

    assert detail.title == "Solo Leveling Season 2 -Arise from the Shadow-"
    assert detail.status == AirStatus.FINISHED
    assert len(episodes) == 25


@pytest.mark.asyncio
async def test_fetch_by_name_not_found():
    empty_page = {"page": 1, "totalAmount": 0, "anime": []}
    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, return_value = empty_page):
        from animeschedule.schedule import fetch_by_name
        with pytest.raises(NotFoundError, match = "No anime found"):
            await fetch_by_name("Nonexistent Anime")


@pytest.mark.asyncio
async def test_fetch_by_name_no_close_match():
    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, return_value = PAGE_RESPONSE):
        from animeschedule.schedule import fetch_by_name
        with pytest.raises(NotFoundError, match = "No close match"):
            await fetch_by_name("Completely Different Title")


@pytest.mark.asyncio
async def test_fetch_current_schedule():
    ongoing_anime = {**SOLO_LEVELING_JSON, "status": "Ongoing"}
    page_data = {"page": 1, "totalAmount": 1, "anime": [ongoing_anime]}

    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, return_value = page_data):
        from animeschedule.schedule import fetch_current_schedule
        entries = await fetch_current_schedule()

    assert isinstance(entries, list)


@pytest.mark.asyncio
async def test_fetch_current_schedule_skips_no_premier():
    no_premier = {**SOLO_LEVELING_JSON, "status": "Ongoing", "premier": None, "jpnTime": None}
    page_data = {"page": 1, "totalAmount": 1, "anime": [no_premier]}

    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, return_value = page_data):
        from animeschedule.schedule import fetch_current_schedule
        entries = await fetch_current_schedule()

    assert entries == []


@pytest.mark.asyncio
async def test_fetch_all_pages_pagination():
    page1_real = {"page": 1, "totalAmount": 2, "anime": [SOLO_LEVELING_JSON]}
    page2_real = {
        "page": 2,
        "totalAmount": 2,
        "anime": [{**SOLO_LEVELING_JSON, "title": "Second Anime", "route": "second"}],
    }

    call_count = 0

    async def mock_get(url, params = None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return page1_real
        return page2_real

    with patch("animeschedule.schedule.get_json_no_auth", new_callable = AsyncMock, side_effect = mock_get):
        from animeschedule.schedule import _fetch_all_pages
        results = await _fetch_all_pages("winter-2025")

    assert len(results) == 2
