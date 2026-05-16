import pytest
from datetime import datetime, timezone
from animeschedule.types import SeasonName
from animeschedule.season import current_season, season_slug


def _dt(month: int) -> datetime:
    return datetime(2025, month, 15, tzinfo = timezone.utc)


def test_winter_months():
    for month in [1, 2, 3]:
        season, year = current_season(_dt(month))
        assert season == SeasonName.WINTER, f"Month {month} should be Winter"
        assert year == 2025


def test_spring_months():
    for month in [4, 5, 6]:
        season, year = current_season(_dt(month))
        assert season == SeasonName.SPRING, f"Month {month} should be Spring"


def test_summer_months():
    for month in [7, 8, 9]:
        season, year = current_season(_dt(month))
        assert season == SeasonName.SUMMER, f"Month {month} should be Summer"


def test_fall_months():
    for month in [10, 11, 12]:
        season, year = current_season(_dt(month))
        assert season == SeasonName.FALL, f"Month {month} should be Fall"


def test_year_returned():
    season, year = current_season(datetime(2024, 7, 1, tzinfo = timezone.utc))
    assert year == 2024


def test_season_slug_winter():
    assert season_slug(SeasonName.WINTER, 2025) == "winter-2025"


def test_season_slug_spring():
    assert season_slug(SeasonName.SPRING, 2025) == "spring-2025"


def test_season_slug_summer():
    assert season_slug(SeasonName.SUMMER, 2024) == "summer-2024"


def test_season_slug_fall():
    assert season_slug(SeasonName.FALL, 2023) == "fall-2023"


def test_current_season_boundary_march():
    dt = datetime(2025, 3, 31, tzinfo = timezone.utc)
    season, _ = current_season(dt)
    assert season == SeasonName.WINTER


def test_current_season_boundary_april():
    dt = datetime(2025, 4, 1, tzinfo = timezone.utc)
    season, _ = current_season(dt)
    assert season == SeasonName.SPRING
