import pytest
from pathlib import Path
from unittest.mock import patch
from lydarr.config import load_config, AppConfig


def test_load_config_defaults():
    with patch.dict("os.environ", {}, clear = True):
        cfg = load_config()

    assert cfg.anime_file == "anime.toml"
    assert cfg.transmission_url == "http://localhost:9091/transmission/rpc"
    assert cfg.transmission_user is None
    assert cfg.transmission_pass is None
    assert cfg.default_dir == str(Path.home() / "Downloads")
    assert cfg.default_dir_set is False


def test_load_config_from_env():
    env = {
        "ANIME_FILE": "/custom/watchlist.toml",
        "TRANSMISSION_URL": "http://myserver:9091/transmission/rpc",
        "TRANSMISSION_USER": "admin",
        "TRANSMISSION_PASS": "secret",
        "LYDARR_DEFAULT_DIR": "/media/downloads",
    }
    with patch.dict("os.environ", env, clear = True):
        cfg = load_config()

    assert cfg.anime_file == "/custom/watchlist.toml"
    assert cfg.transmission_url == "http://myserver:9091/transmission/rpc"
    assert cfg.transmission_user == "admin"
    assert cfg.transmission_pass == "secret"
    assert cfg.default_dir == "/media/downloads"
    assert cfg.default_dir_set is True


def test_load_config_empty_user_becomes_none():
    with patch.dict("os.environ", {"TRANSMISSION_USER": "", "TRANSMISSION_PASS": ""}, clear = False):
        cfg = load_config()

    assert cfg.transmission_user is None
    assert cfg.transmission_pass is None


def test_load_config_default_dir_not_set():
    with patch.dict("os.environ", {}, clear = True):
        cfg = load_config()

    assert cfg.default_dir_set is False
    assert "Downloads" in cfg.default_dir


def test_app_config_is_dataclass():
    cfg = AppConfig(
        anime_file = "test.toml",
        transmission_url = "http://localhost:9091/transmission/rpc",
        transmission_user = None,
        transmission_pass = None,
        default_dir = "/tmp",
        default_dir_set = False,
        lydarr_user = None,
        lydarr_pass = None,
    )
    assert cfg.anime_file == "test.toml"
    assert cfg.transmission_user is None
