import pytest
from datetime import datetime, timezone
from animeschedule.types import AirStatus
from animeschedule.models import (
    parse_utc, _parse_status, AnimeJson, AnimePage,
    to_anime_summary, to_anime_detail, NULL_SENTINEL,
)


def test_parse_utc_valid():
    result = parse_utc("2025-01-12T14:30:00Z")
    assert result is not None
    assert result.year == 2025
    assert result.month == 1
    assert result.day == 12
    assert result.tzinfo == timezone.utc


def test_parse_utc_null_sentinel():
    assert parse_utc(NULL_SENTINEL) is None


def test_parse_utc_empty():
    assert parse_utc("") is None


def test_parse_utc_invalid_format():
    assert parse_utc("not-a-date") is None


def test_parse_status_known():
    assert _parse_status("Ongoing") == AirStatus.ONGOING
    assert _parse_status("Finished") == AirStatus.FINISHED
    assert _parse_status("Upcoming") == AirStatus.UPCOMING
    assert _parse_status("Delayed") == AirStatus.DELAYED


def test_parse_status_unknown():
    assert _parse_status("SomethingRandom") == AirStatus.UNKNOWN


SOLO_LEVELING_DICT = {
    "title": "Solo Leveling Season 2 -Arise from the Shadow-",
    "route": "solo-leveling-season-2-arise-from-the-shadow",
    "status": "Finished",
    "premier": "2025-01-04T15:00:00Z",
    "subPremier": "2025-01-04T17:30:00Z",
    "dubPremier": None,
    "jpnTime": "2025-01-04T15:00:00Z",
    "subTime": "2025-01-04T17:30:00Z",
    "dubTime": None,
    "episodes": 25,
}


def test_anime_json_from_dict():
    aj = AnimeJson.from_dict(SOLO_LEVELING_DICT)
    assert aj.title == "Solo Leveling Season 2 -Arise from the Shadow-"
    assert aj.route == "solo-leveling-season-2-arise-from-the-shadow"
    assert aj.status == "Finished"
    assert aj.episodes == 25
    assert aj.premier == "2025-01-04T15:00:00Z"
    assert aj.dub_premier is None


def test_anime_json_missing_optional_fields():
    d = {"title": "Test", "route": "test", "status": "Ongoing"}
    aj = AnimeJson.from_dict(d)
    assert aj.premier is None
    assert aj.episodes is None
    assert aj.sub_time is None


def test_anime_page_from_dict():
    d = {
        "page": 1,
        "totalAmount": 2,
        "anime": [SOLO_LEVELING_DICT, {**SOLO_LEVELING_DICT, "title": "Other Anime"}],
    }
    page = AnimePage.from_dict(d)
    assert page.page == 1
    assert page.total_amount == 2
    assert len(page.anime) == 2
    assert page.anime[0].title == "Solo Leveling Season 2 -Arise from the Shadow-"


def test_anime_page_empty_anime():
    d = {"page": 1, "totalAmount": 0, "anime": []}
    page = AnimePage.from_dict(d)
    assert page.anime == []


def test_to_anime_summary():
    aj = AnimeJson.from_dict(SOLO_LEVELING_DICT)
    summary = to_anime_summary(aj)
    assert summary.title == "Solo Leveling Season 2 -Arise from the Shadow-"
    assert summary.status == AirStatus.FINISHED
    assert summary.episodes == 25
    assert summary.premier is not None


def test_to_anime_detail():
    aj = AnimeJson.from_dict(SOLO_LEVELING_DICT)
    detail = to_anime_detail(aj)
    assert detail.title == "Solo Leveling Season 2 -Arise from the Shadow-"
    assert detail.status == AirStatus.FINISHED
    assert detail.episodes == 25
    assert detail.premier is not None
    assert detail.sub_premier is not None
    assert detail.dub_premier is None
    assert detail.dub_time is None


def test_to_anime_detail_null_times():
    d = {
        "title": "Test",
        "route": "test",
        "status": "Ongoing",
        "premier": None,
        "jpnTime": None,
        "episodes": None,
    }
    aj = AnimeJson.from_dict(d)
    detail = to_anime_detail(aj)
    assert detail.premier is None
    assert detail.jpn_time is None
