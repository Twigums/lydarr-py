"""Season name and slug helpers."""
from datetime import datetime

from animeschedule.types import SeasonName


def current_season(now: datetime) -> tuple[SeasonName, int]:
    month = now.month
    if month <= 3:
        season = SeasonName.WINTER
    elif month <= 6:
        season = SeasonName.SPRING
    elif month <= 9:
        season = SeasonName.SUMMER
    else:
        season = SeasonName.FALL
    return season, now.year


def season_slug(season: SeasonName, year: int) -> str:
    return f"{season.value}-{year}"
