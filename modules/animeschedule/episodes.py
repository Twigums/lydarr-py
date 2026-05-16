"""Episode scheduling calculations from premiere and air-time data."""
from datetime import datetime, timedelta, timezone

from animeschedule.types import AnimeDetail, EpisodeRecord

_WEEK = timedelta(weeks = 1)


def episode_utc(premier: datetime, jpn_time: datetime, n: int) -> datetime:
    day = (premier + (n - 1) * _WEEK).date()
    return datetime.combine(day, jpn_time.timetz(), tzinfo = timezone.utc)


def all_episodes(premier: datetime, jpn_time: datetime, total: int) -> list[datetime]:
    return [episode_utc(premier, jpn_time, n) for n in range(1, total + 1)]


def feed_episodes(
    premier: datetime | None, jpn_time: datetime | None, total: int
) -> list[datetime | None]:
    if premier is None or jpn_time is None:
        return [None] * total
    return [episode_utc(premier, jpn_time, n) for n in range(1, total + 1)]


def next_episode(premier: datetime, jpn_time: datetime, now: datetime) -> tuple[int, datetime]:
    ep1 = episode_utc(premier, jpn_time, 1)
    elapsed = max(0.0, (now - ep1).total_seconds())
    weeks_gone = int(elapsed / _WEEK.total_seconds())
    candidate = weeks_gone + 1
    ep_date = episode_utc(premier, jpn_time, candidate)
    if ep_date > now:
        return candidate, ep_date
    return candidate + 1, episode_utc(premier, jpn_time, candidate + 1)


def compute_episodes(detail: AnimeDetail) -> list[EpisodeRecord]:
    total = detail.episodes or 24
    raw_times = feed_episodes(detail.premier, detail.jpn_time, total)
    sub_prem = detail.sub_premier or detail.premier
    sub_times = feed_episodes(sub_prem, detail.sub_time, total)
    dub_prem = detail.dub_premier or detail.premier
    dub_times = feed_episodes(dub_prem, detail.dub_time, total)
    return [
        EpisodeRecord(number = n, raw = r, sub = s, dub = d)
        for n, (r, s, d) in enumerate(zip(raw_times, sub_times, dub_times), start = 1)
    ]
