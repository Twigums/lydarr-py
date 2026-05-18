# lydarr-py

aka "That Time Crunchyroll Ruined My Life, So I Paid Claude $100 To Revive Me?" (クランチロールに人生をぶっ壊された　クロードに１００００円を払っちゃってオレは復活した件）

Anime torrent downloader daemon that tracks airing anime/manga. The daemon waits for each episode or chapter's release, searches nyaa, and adds them to `transmission-daemon` automatically. A web UI is also included for QOL to search for and manage anime/manga.

## Requirements

1. Install `uv`.

2. `apt install transmission-daemon`

## Setup

```bash
uv sync
```

Add entries to `anime.toml` manually:

```toml
[[media]]
title = "TITLE_OF_ANIME"
type = "anime" # "anime" or "manga"
search_name = "SEARCH_NAME" # title used to search nyaa with
submitters = ["SUBMITTER_1", "SUBMITTER_2"] # chosen submitter(s)
deprecated = true # skipped by daemon


# TODO
[[media]]
title = "TITLE_OF_MANGA"
type = "manga"
submitters = [] # empty = accept all uploaders
last_chapter = 1
```

Or use the web-ui below...

## Configuration

Copy the example env file and fill in your values:

Either locally:

```bash
cp .env.example .env
```

Or user:

```bash
mkdir -p ~/.config/lydarr
cp .env.example ~/.config/lydarr/env
```

In `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `ANIME_FILE` | `anime.toml` | Path to watchlist file |
| `TRANSMISSION_URL` | `http://localhost:9091/transmission/rpc` | Transmission RPC endpoint |
| `TRANSMISSION_USER` | unset | Transmission username (if auth enabled) |
| `TRANSMISSION_PASS` | unset | Transmission password (if auth enabled) |
| `LYDARR_DEFAULT_DIR` | `~/Downloads` | Default download directory |
| `LYDARR_WEB` | unset | Set to `1` to enable web UI alongside daemon |
| `LYDARR_WEB_HOST` | `0.0.0.0` | Web UI bind address (overridden by `--host`) |
| `LYDARR_WEB_PORT` | `8080` | Web UI port (overridden by `--port`) |

## Usage

```bash
# Daemon only
uv run python -m lydarr

# Web UI only (daemon can be started on web)
uv run python -m lydarr --web-only

# Bind to a specific address/port
uv run python -m lydarr --web-only --host 127.0.0.1 --port 8080
```

## Systemd service

Template is included at `lydarr.service`.

```bash
mkdir -p ~/.config/systemd/user
cp lydarr.service ~/.config/systemd/user/lydarr.service
systemctl --user daemon-reload
systemctl --user enable --now lydarr

loginctl enable-linger
```