"""JSON deserialization and domain conversion for the AnimeSchedule API."""
from dataclasses import dataclass
from datetime import datetime, timezone

from animeschedule.types import AirStatus, AnimeDetail, AnimeSummary

NULL_SENTINEL = "0001-01-01T00:00:00Z"


def parse_utc(text: str) -> datetime | None:
    if not text or text == NULL_SENTINEL:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo = timezone.utc)
    except ValueError:
        return None


def _parse_status(text: str) -> AirStatus:
    try:
        return AirStatus(text)
    except ValueError:
        return AirStatus.UNKNOWN


@dataclass
class AnimeJson:
    title: str
    route: str
    status: str
    premier: str | None
    sub_premier: str | None
    dub_premier: str | None
    jpn_time: str | None
    sub_time: str | None
    dub_time: str | None
    episodes: int | None

    @classmethod
    def from_dict(cls, d: dict) -> "AnimeJson":
        return cls(
            title = d["title"],
            route = d["route"],
            status = d["status"],
            premier = d.get("premier"),
            sub_premier = d.get("subPremier"),
            dub_premier = d.get("dubPremier"),
            jpn_time = d.get("jpnTime"),
            sub_time = d.get("subTime"),
            dub_time = d.get("dubTime"),
            episodes = d.get("episodes"),
        )


@dataclass
class AnimePage:
    page: int
    total_amount: int
    anime: list[AnimeJson]

    @classmethod
    def from_dict(cls, d: dict) -> "AnimePage":
        return cls(
            page = d["page"],
            total_amount = d["totalAmount"],
            anime = [AnimeJson.from_dict(a) for a in d.get("anime", [])],
        )


def to_anime_summary(aj: AnimeJson) -> AnimeSummary:
    return AnimeSummary(
        title = aj.title,
        route = aj.route,
        status = _parse_status(aj.status),
        premier = parse_utc(aj.premier) if aj.premier else None,
        jpn_time = parse_utc(aj.jpn_time) if aj.jpn_time else None,
        episodes = aj.episodes,
    )


def to_anime_detail(aj: AnimeJson) -> AnimeDetail:
    return AnimeDetail(
        title = aj.title,
        route = aj.route,
        premier = parse_utc(aj.premier) if aj.premier else None,
        sub_premier = parse_utc(aj.sub_premier) if aj.sub_premier else None,
        dub_premier = parse_utc(aj.dub_premier) if aj.dub_premier else None,
        jpn_time = parse_utc(aj.jpn_time) if aj.jpn_time else None,
        sub_time = parse_utc(aj.sub_time) if aj.sub_time else None,
        dub_time = parse_utc(aj.dub_time) if aj.dub_time else None,
        status = _parse_status(aj.status),
        episodes = aj.episodes,
    )
