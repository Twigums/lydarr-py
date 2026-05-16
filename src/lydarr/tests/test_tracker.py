import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from animeschedule.types import AirStatus, EpisodeRecord, AnimeDetail
from lydarr.config import AppConfig
from lydarr.file_manager import MediaEntry, MediaState
from lydarr.tracker import (
    _log, _pad, _next_episode_time, _step_anime, track_media,
)


def _make_cfg() -> AppConfig:
    return AppConfig(
        anime_file = "/tmp/test.toml",
        transmission_url = "http://localhost:9091/transmission/rpc",
        transmission_user = None,
        transmission_pass = None,
        default_dir = "/downloads",
        default_dir_set = True,
        lydarr_user = None,
        lydarr_pass = None,
    )


def _make_state(titles: list[str] | None = None) -> MediaState:
    entries = [MediaEntry(title = t) for t in (titles or [])]
    return MediaState(entries)


def _make_detail(status: AirStatus, episodes: int | None = 25) -> AnimeDetail:
    return AnimeDetail(
        title = "Solo Leveling",
        route = "solo-leveling-s2",
        premier = datetime(2025, 1, 4, 15, 0, 0, tzinfo = timezone.utc),
        sub_premier = datetime(2025, 1, 4, 17, 30, 0, tzinfo = timezone.utc),
        dub_premier = None,
        jpn_time = datetime(2025, 1, 4, 15, 0, 0, tzinfo = timezone.utc),
        sub_time = datetime(2025, 1, 4, 17, 30, 0, tzinfo = timezone.utc),
        dub_time = None,
        status = status,
        episodes = episodes,
    )


def _make_episodes(n: int, past: bool = True) -> list[EpisodeRecord]:
    now = datetime.now(tz = timezone.utc)
    delta = timedelta(weeks = 1)
    records = []
    for i in range(1, n + 1):
        if past:
            t = now - delta * (n - i + 1)
        else:
            t = now + delta * i
        records.append(EpisodeRecord(number = i, raw = t, sub = t, dub = None))
    return records


def test_log_prints(capsys):
    _log("Solo Leveling", "Test message")
    captured = capsys.readouterr()
    assert "[Solo Leveling] Test message" in captured.out


def test_pad():
    assert _pad(1) == "01"
    assert _pad(10) == "10"
    assert _pad(25) == "25"


def test_next_episode_time_future():
    now = datetime.now(tz = timezone.utc)
    future = now + timedelta(hours = 2)
    episodes = [
        EpisodeRecord(number = 1, raw = now - timedelta(days = 7), sub = now - timedelta(days = 7), dub = None),
        EpisodeRecord(number = 2, raw = future, sub = future, dub = None),
    ]
    result = _next_episode_time(episodes, now)
    assert result is not None
    ep_num, ep_time = result
    assert ep_num == 2
    assert ep_time == future


def test_next_episode_time_none_when_all_past():
    now = datetime.now(tz = timezone.utc)
    past = now - timedelta(hours = 1)
    episodes = [EpisodeRecord(number = 1, raw = past, sub = past, dub = None)]
    result = _next_episode_time(episodes, now)
    assert result is None


def test_next_episode_time_none_sub():
    now = datetime.now(tz = timezone.utc)
    future = now + timedelta(hours = 2)
    episodes = [EpisodeRecord(number = 1, raw = future, sub = None, dub = None)]
    result = _next_episode_time(episodes, now)
    assert result is None


@pytest.mark.asyncio
async def test_step_anime_finished_downloads_all():
    cfg = _make_cfg()
    state = _make_state(["Solo Leveling"])
    entry = MediaEntry(title = "Solo Leveling", submitters = ["SubsPlease"])
    detail = _make_detail(AirStatus.FINISHED, episodes = 25)
    episodes = _make_episodes(25)

    with patch("lydarr.tracker.fetch_by_name", new_callable = AsyncMock, return_value = (detail, episodes)), \
         patch("lydarr.tracker._download_all_episodes", new_callable = AsyncMock) as mock_dl, \
         patch("lydarr.tracker.asyncio.sleep", new_callable = AsyncMock), \
         patch.object(state, "remove", new_callable = AsyncMock) as mock_remove:
        result = await _step_anime(cfg, state, entry)

    mock_dl.assert_called_once_with(cfg, "Solo Leveling", 25, ["SubsPlease"])
    mock_remove.assert_called_once_with("/tmp/test.toml", "Solo Leveling")
    assert result is False


@pytest.mark.asyncio
async def test_step_anime_finished_uses_search_name():
    cfg = _make_cfg()
    state = _make_state(["Solo Leveling"])
    entry = MediaEntry(title = "Solo Leveling", search_name = "Solo Leveling S2", submitters = [])
    detail = _make_detail(AirStatus.FINISHED, episodes = 2)
    episodes = _make_episodes(2)

    with patch("lydarr.tracker.fetch_by_name", new_callable = AsyncMock, return_value = (detail, episodes)), \
         patch("lydarr.tracker._download_all_episodes", new_callable = AsyncMock) as mock_dl, \
         patch("lydarr.tracker.asyncio.sleep", new_callable = AsyncMock), \
         patch.object(state, "remove", new_callable = AsyncMock):
        await _step_anime(cfg, state, entry)

    mock_dl.assert_called_once_with(cfg, "Solo Leveling S2", 2, [])


@pytest.mark.asyncio
async def test_step_anime_ongoing_returns_true():
    cfg = _make_cfg()
    state = _make_state(["Solo Leveling"])
    entry = MediaEntry(title = "Solo Leveling", submitters = [])
    detail = _make_detail(AirStatus.ONGOING)
    now = datetime.now(tz = timezone.utc)
    future = now + timedelta(hours = 2)
    episodes = [EpisodeRecord(number = 1, raw = future, sub = future, dub = None)]

    with patch("lydarr.tracker.fetch_by_name", new_callable = AsyncMock, return_value = (detail, episodes)), \
         patch("lydarr.tracker._sleep_until", new_callable = AsyncMock), \
         patch("lydarr.tracker._wait_and_add_episode", new_callable = AsyncMock), \
         patch("lydarr.tracker.asyncio.sleep", new_callable = AsyncMock):
        result = await _step_anime(cfg, state, entry)

    assert result is True


@pytest.mark.asyncio
async def test_step_anime_ongoing_no_sub_time():
    cfg = _make_cfg()
    state = _make_state(["Solo Leveling"])
    entry = MediaEntry(title = "Solo Leveling", submitters = [])
    detail = _make_detail(AirStatus.ONGOING)
    episodes = [EpisodeRecord(number = 1, raw = None, sub = None, dub = None)]

    with patch("lydarr.tracker.fetch_by_name", new_callable = AsyncMock, return_value = (detail, episodes)), \
         patch("lydarr.tracker.asyncio.sleep", new_callable = AsyncMock) as mock_sleep:
        result = await _step_anime(cfg, state, entry)

    mock_sleep.assert_called_once_with(6 * 3600)
    assert result is True


@pytest.mark.asyncio
async def test_step_anime_upcoming_sleeps():
    cfg = _make_cfg()
    state = _make_state(["Solo Leveling"])
    entry = MediaEntry(title = "Solo Leveling", submitters = [])
    detail = _make_detail(AirStatus.UPCOMING)
    episodes = []

    with patch("lydarr.tracker.fetch_by_name", new_callable = AsyncMock, return_value = (detail, episodes)), \
         patch("lydarr.tracker.asyncio.sleep", new_callable = AsyncMock) as mock_sleep:
        result = await _step_anime(cfg, state, entry)

    mock_sleep.assert_called_once_with(6 * 3600)
    assert result is True


@pytest.mark.asyncio
async def test_step_anime_unknown_status():
    cfg = _make_cfg()
    state = _make_state(["Solo Leveling"])
    entry = MediaEntry(title = "Solo Leveling", submitters = [])
    detail = _make_detail(AirStatus.UNKNOWN)
    episodes = []

    with patch("lydarr.tracker.fetch_by_name", new_callable = AsyncMock, return_value = (detail, episodes)), \
         patch("lydarr.tracker.asyncio.sleep", new_callable = AsyncMock) as mock_sleep:
        result = await _step_anime(cfg, state, entry)

    mock_sleep.assert_called_once_with(3600)
    assert result is True


@pytest.mark.asyncio
async def test_track_media_stops_on_false():
    cfg = _make_cfg()
    state = _make_state()
    entry = MediaEntry(title = "Solo Leveling")

    call_count = 0

    async def mock_step(_, s, e):
        nonlocal call_count
        call_count += 1
        return False

    with patch("lydarr.tracker._step_anime", new_callable = AsyncMock, side_effect = mock_step):
        await track_media(cfg, state, entry)

    assert call_count == 1


@pytest.mark.asyncio
async def test_track_media_retries_on_exception():
    cfg = _make_cfg()
    state = _make_state()
    entry = MediaEntry(title = "Solo Leveling")

    call_count = 0

    async def mock_step(_, s, e):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Unexpected error")
        return False

    with patch("lydarr.tracker._step_anime", new_callable = AsyncMock, side_effect = mock_step), \
         patch("lydarr.tracker.asyncio.sleep", new_callable = AsyncMock):
        await track_media(cfg, state, entry)

    assert call_count == 2


@pytest.mark.asyncio
async def test_track_media_manga_uses_step_manga():
    cfg = _make_cfg()
    state = _make_state()
    entry = MediaEntry(title = "One Piece", media_type = "manga")

    with patch("lydarr.tracker._step_manga", new_callable = AsyncMock, return_value = False) as mock_manga, \
         patch("lydarr.tracker._step_anime", new_callable = AsyncMock, return_value = False) as mock_anime:
        await track_media(cfg, state, entry)

    mock_manga.assert_called_once()
    mock_anime.assert_not_called()


