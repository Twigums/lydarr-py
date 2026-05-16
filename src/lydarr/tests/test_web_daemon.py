import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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


def test_daemon_status_not_running(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([MediaEntry(title = "Solo Leveling")])
    with TestClient(create_app(cfg, state)) as client:
        resp = client.get("/api/daemon/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running"] is False
    assert "Solo Leveling" in data["tracking"]
    assert data["started_at"] is None


def test_daemon_start(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([MediaEntry(title = "Solo Leveling")])

    never_done = MagicMock()
    never_done.done.return_value = False

    with patch("lydarr.web.routes.daemon.asyncio.create_task", return_value = never_done):
        with TestClient(create_app(cfg, state)) as client:
            resp = client.post("/api/daemon/start")

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_daemon_start_already_running(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([MediaEntry(title = "Solo Leveling")])

    running_task = MagicMock()
    running_task.done.return_value = False

    with patch("lydarr.web.routes.daemon.asyncio.create_task", return_value = running_task):
        with TestClient(create_app(cfg, state)) as client:
            client.post("/api/daemon/start")
            resp = client.post("/api/daemon/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["reason"] == "already running"


def test_daemon_stop_not_running(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([])
    with TestClient(create_app(cfg, state)) as client:
        resp = client.post("/api/daemon/stop")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["reason"] == "not running"


def test_rtorrent_status_online(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([])
    with patch("lydarr.web.routes.daemon.is_client_up", new_callable = AsyncMock, return_value = True):
        with TestClient(create_app(cfg, state)) as client:
            resp = client.get("/api/rtorrent/status")
    assert resp.status_code == 200
    assert resp.json()["online"] is True


def test_rtorrent_status_offline(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([])
    with patch("lydarr.web.routes.daemon.is_client_up", new_callable = AsyncMock, return_value = False):
        with TestClient(create_app(cfg, state)) as client:
            resp = client.get("/api/rtorrent/status")
    assert resp.status_code == 200
    assert resp.json()["online"] is False


def test_daemon_status_tracking_list(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([
        MediaEntry(title = "Solo Leveling"),
        MediaEntry(title = "Dan Da Dan"),
    ])
    with TestClient(create_app(cfg, state)) as client:
        resp = client.get("/api/daemon/status")
    data = resp.json()
    assert "Solo Leveling" in data["tracking"]
    assert "Dan Da Dan" in data["tracking"]


def test_combined_status_transmission_online_daemon_not_running(tmp_path):
    """Regression: when Transmission is online but the daemon is not running,
    the two status endpoints together must indicate that something is active
    so the UI can show Stop instead of Start."""
    cfg = _make_cfg(tmp_path)
    state = MediaState([])
    with patch("lydarr.web.routes.daemon.is_client_up", new_callable = AsyncMock, return_value = True):
        with TestClient(create_app(cfg, state)) as client:
            daemon_resp = client.get("/api/daemon/status")
            tx_resp = client.get("/api/rtorrent/status")
    daemon_data = daemon_resp.json()
    tx_data = tx_resp.json()
    assert daemon_data["running"] is False
    assert tx_data["online"] is True
    # UI derives active = daemon_running OR tx_online — must be True here
    assert daemon_data["running"] or tx_data["online"]


def test_daemon_status_started_at_set_after_start(tmp_path):
    cfg = _make_cfg(tmp_path)
    state = MediaState([MediaEntry(title = "Solo Leveling")])

    done_task = MagicMock()
    done_task.done.return_value = False

    with patch("lydarr.web.routes.daemon.asyncio.create_task", return_value = done_task):
        with TestClient(create_app(cfg, state)) as client:
            client.post("/api/daemon/start")
            resp = client.get("/api/daemon/status")

    data = resp.json()
    assert data["running"] is True
    assert data["started_at"] is not None
