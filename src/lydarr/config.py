"""Configuration loaded from environment variables."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    anime_file: str
    transmission_url: str
    transmission_user: str | None
    transmission_pass: str | None
    default_dir: str
    default_dir_set: bool
    lydarr_user: str | None
    lydarr_pass: str | None


def load_config() -> AppConfig:
    anime_file = os.environ.get("ANIME_FILE", "anime.toml")
    transmission_url = os.environ.get("TRANSMISSION_URL", "http://localhost:9091/transmission/rpc")
    transmission_user = os.environ.get("TRANSMISSION_USER") or None
    transmission_pass = os.environ.get("TRANSMISSION_PASS") or None
    default_dir_env = os.environ.get("LYDARR_DEFAULT_DIR")
    default_dir = default_dir_env or str(Path.home() / "Downloads")
    lydarr_user = os.environ.get("LYDARR_USER") or None
    lydarr_pass = os.environ.get("LYDARR_PASS") or None
    return AppConfig(
        anime_file = anime_file,
        transmission_url = transmission_url,
        transmission_user = transmission_user,
        transmission_pass = transmission_pass,
        default_dir = default_dir,
        default_dir_set = default_dir_env is not None,
        lydarr_user = lydarr_user,
        lydarr_pass = lydarr_pass,
    )
