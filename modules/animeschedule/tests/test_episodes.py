import pytest
from datetime import datetime, timezone, timedelta
from animeschedule.types import AnimeDetail, AirStatus
from animeschedule.episodes import (
    episode_utc, all_episodes, feed_episodes, next_episode, compute_episodes,
)


PREMIER = datetime(2025, 1, 4, 15, 0, 0, tzinfo = timezone.utc)
JPN_TIME = datetime(2025, 1, 4, 15, 0, 0, tzinfo = timezone.utc)


def test_episode_utc_first_episode():
    ep1 = episode_utc(PREMIER, JPN_TIME, 1)
    assert ep1.date() == PREMIER.date()
    assert ep1.tzinfo == timezone.utc


def test_episode_utc_second_episode_one_week_later():
    ep1 = episode_utc(PREMIER, JPN_TIME, 1)
    ep2 = episode_utc(PREMIER, JPN_TIME, 2)
    assert (ep2 - ep1).days == 7


def test_episode_utc_25th_episode():
    ep25 = episode_utc(PREMIER, JPN_TIME, 25)
    ep1 = episode_utc(PREMIER, JPN_TIME, 1)
    assert (ep25 - ep1).days == 24 * 7


def test_all_episodes_count():
    eps = all_episodes(PREMIER, JPN_TIME, 25)
    assert len(eps) == 25


def test_all_episodes_weekly_spacing():
    eps = all_episodes(PREMIER, JPN_TIME, 4)
    for i in range(1, len(eps)):
        assert (eps[i] - eps[i - 1]).days == 7


def test_feed_episodes_with_data():
    eps = feed_episodes(PREMIER, JPN_TIME, 3)
    assert len(eps) == 3
    assert all(e is not None for e in eps)


def test_feed_episodes_no_premier():
    eps = feed_episodes(None, JPN_TIME, 5)
    assert len(eps) == 5
    assert all(e is None for e in eps)


def test_feed_episodes_no_jpn_time():
    eps = feed_episodes(PREMIER, None, 5)
    assert len(eps) == 5
    assert all(e is None for e in eps)


def test_feed_episodes_both_none():
    eps = feed_episodes(None, None, 3)
    assert eps == [None, None, None]


def test_next_episode_before_ep1():
    now = PREMIER - timedelta(hours = 1)
    ep_num, ep_time = next_episode(PREMIER, JPN_TIME, now)
    assert ep_num == 1
    assert ep_time == PREMIER


def test_next_episode_between_ep1_and_ep2():
    now = PREMIER + timedelta(days = 3)
    ep_num, ep_time = next_episode(PREMIER, JPN_TIME, now)
    assert ep_num == 2


def test_next_episode_after_ep2_airs():
    ep2_time = episode_utc(PREMIER, JPN_TIME, 2)
    now = ep2_time + timedelta(hours = 1)
    ep_num, ep_time = next_episode(PREMIER, JPN_TIME, now)
    assert ep_num == 3


def _make_detail(status = AirStatus.ONGOING, episodes = 12, premier = PREMIER, jpn_time = JPN_TIME):
    return AnimeDetail(
        title = "Solo Leveling",
        route = "solo-leveling",
        premier = premier,
        sub_premier = premier,
        dub_premier = None,
        jpn_time = jpn_time,
        sub_time = jpn_time,
        dub_time = None,
        status = status,
        episodes = episodes,
    )


def test_compute_episodes_count():
    detail = _make_detail(episodes = 25)
    records = compute_episodes(detail)
    assert len(records) == 25


def test_compute_episodes_numbers():
    detail = _make_detail(episodes = 3)
    records = compute_episodes(detail)
    assert [r.number for r in records] == [1, 2, 3]


def test_compute_episodes_defaults_to_24():
    detail = _make_detail(episodes = None)
    records = compute_episodes(detail)
    assert len(records) == 24


def test_compute_episodes_raw_and_sub():
    detail = _make_detail(episodes = 2)
    records = compute_episodes(detail)
    assert records[0].raw is not None
    assert records[0].sub is not None
    assert records[0].dub is None


def test_compute_episodes_no_premier():
    detail = _make_detail(episodes = 5, premier = None, jpn_time = None)
    records = compute_episodes(detail)
    assert all(r.raw is None for r in records)
