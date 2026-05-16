"""AnimeSchedule API domain types."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AirStatus(Enum):
    UPCOMING = "Upcoming"
    ONGOING = "Ongoing"
    DELAYED = "Delayed"
    FINISHED = "Finished"
    UNKNOWN = "Unknown"


class SeasonName(Enum):
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"


@dataclass
class AnimeDetail:
    title: str
    route: str
    premier: datetime | None
    sub_premier: datetime | None
    dub_premier: datetime | None
    jpn_time: datetime | None
    sub_time: datetime | None
    dub_time: datetime | None
    status: AirStatus
    episodes: int | None


@dataclass
class EpisodeRecord:
    number: int
    raw: datetime | None
    sub: datetime | None
    dub: datetime | None


@dataclass
class AnimeSummary:
    title: str
    route: str
    status: AirStatus
    premier: datetime | None
    jpn_time: datetime | None
    episodes: int | None


@dataclass
class CurrentEntry:
    title: str
    ep_num: int
    utc: datetime


class ScheduleError(Exception):
    pass


class HttpError(ScheduleError):
    pass


class ParseError(ScheduleError):
    pass


class AuthError(ScheduleError):
    pass


class NotFoundError(ScheduleError):
    pass
