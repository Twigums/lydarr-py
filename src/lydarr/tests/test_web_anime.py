import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from lydarr.config import AppConfig
from lydarr.file_manager import MediaEntry, MediaState
from lydarr.web.app import create_app


def _make_cfg(tmp_path) -> AppConfig:
    return AppConfig(
        anime_file = str(tmp_path / "media.toml"),
        transmission_url = "http://localhost:9091/transmission/rpc",
        transmission_user = None,
        transmission_pass = None,
        default_dir = "/downloads",
        default_dir_set = True,
        lydarr_user = None,
        lydarr_pass = None,
    )


def _make_state(entries: list[MediaEntry] | None = None) -> MediaState:
    return MediaState(entries or [])


def test_list_empty(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state()
    with TestClient(create_app(cfg, state)) as client:
        resp = client.get("/api/anime/list")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_with_entries(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state([
        MediaEntry(title = "Solo Leveling", media_type = "anime", submitters = ["SubsPlease"]),
    ])
    with TestClient(create_app(cfg, state)) as client:
        resp = client.get("/api/anime/list")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Solo Leveling"
    assert data[0]["submitters"] == ["SubsPlease"]
    assert data[0]["type"] == "anime"


def test_add_new_entry(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state()
    with TestClient(create_app(cfg, state)) as client:
        resp = client.post("/api/anime/add", json = {"title": "Solo Leveling", "type": "anime", "submitters": []})
    assert resp.status_code == 200
    assert resp.json()["added"] is True
    assert "Solo Leveling" in state.titles()


def test_add_duplicate_entry(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state([MediaEntry(title = "Solo Leveling")])
    with TestClient(create_app(cfg, state)) as client:
        resp = client.post("/api/anime/add", json = {"title": "Solo Leveling"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["added"] is False
    assert data["reason"] == "already tracked"


def test_remove_existing(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state([MediaEntry(title = "Solo Leveling")])
    with TestClient(create_app(cfg, state)) as client:
        resp = client.post("/api/anime/remove", json = {"title": "Solo Leveling"})
    assert resp.status_code == 200
    assert resp.json()["removed"] is True
    assert "Solo Leveling" not in state.titles()


def test_remove_nonexistent(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state()
    with TestClient(create_app(cfg, state)) as client:
        resp = client.post("/api/anime/remove", json = {"title": "Nonexistent"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["removed"] is False
    assert data["reason"] == "not tracked"


def test_update_submitters(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state([MediaEntry(title = "Solo Leveling", submitters = [])])
    with TestClient(create_app(cfg, state)) as client:
        resp = client.post("/api/anime/submitters", json = {
            "title": "Solo Leveling",
            "submitters": ["SubsPlease", "Erai-raws"],
            "search_name": "Solo Leveling S2",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    entries = state.entries()
    e = next(e for e in entries if e.title == "Solo Leveling")
    assert e.submitters == ["SubsPlease", "Erai-raws"]
    assert e.search_name == "Solo Leveling S2"


def test_update_submitters_not_tracked(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state()
    with TestClient(create_app(cfg, state)) as client:
        resp = client.post("/api/anime/submitters", json = {
            "title": "Nonexistent",
            "submitters": [],
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["reason"] == "not tracked"


def test_search_anime(tmp_path):
    from anilist.types import AnilistMedia, MediaType, MediaStatus
    cfg = _make_cfg(tmp_path)
    state = _make_state()

    fake_media = AnilistMedia(
        id = 153406,
        title_english = "Solo Leveling Season 2",
        title_romaji = "Solo Leveling Season 2 -Arise from the Shadow-",
        media_type = MediaType.ANIME,
        status = MediaStatus.FINISHED,
        episodes = 25,
        chapters = None,
        next_airing_at = None,
        next_airing_episode = None,
    )

    with patch("lydarr.web.routes.anime.anilist_search", new_callable = AsyncMock, return_value = [fake_media]):
        with TestClient(create_app(cfg, state)) as client:
            resp = client.get("/api/anime/search?q=Solo+Leveling")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 153406
    assert data[0]["episodes"] == 25
    assert data[0]["status"] == "FINISHED"


def test_search_manga_type(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state()

    with patch("lydarr.web.routes.anime.anilist_search", new_callable = AsyncMock, return_value = []) as mock_search:
        with TestClient(create_app(cfg, state)) as client:
            resp = client.get("/api/anime/search?q=One+Piece&type=manga")

    assert resp.status_code == 200
    from anilist.types import MediaType
    mock_search.assert_called_once_with("One Piece", MediaType.MANGA)


def test_get_status_found(tmp_path):
    from anilist.types import AnilistMedia, MediaType, MediaStatus
    cfg = _make_cfg(tmp_path)
    state = _make_state()

    fake_media = AnilistMedia(
        id = 153406,
        title_english = "Solo Leveling Season 2",
        title_romaji = None,
        media_type = MediaType.ANIME,
        status = MediaStatus.FINISHED,
        episodes = 25,
        chapters = None,
        next_airing_at = None,
        next_airing_episode = None,
    )

    with patch("lydarr.web.routes.anime.find_by_title", new_callable = AsyncMock, return_value = fake_media):
        with TestClient(create_app(cfg, state)) as client:
            resp = client.get("/api/anime/status?title=Solo+Leveling")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FINISHED"


def test_get_status_not_found(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = _make_state()

    with patch("lydarr.web.routes.anime.find_by_title", new_callable = AsyncMock, return_value = None):
        with TestClient(create_app(cfg, state)) as client:
            resp = client.get("/api/anime/status?title=Nonexistent")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] is None
