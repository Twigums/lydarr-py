# lydarr-py

Python port of [lydarr](https://github.com/Twigums/lydarr). Daemon that tracks airing anime and releasing manga, waits for each episode or chapter's release, searches [Nyaa.si](https://nyaa.si) for subbed torrents/scanlations, and adds them to Transmission automatically. Includes a web UI for searching media, managing the watchlist, and browsing torrent results manually.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- [Transmission](https://transmissionbt.com/) (`transmission-daemon`)

## Setup

```bash
git clone https://github.com/Twigums/lydarr-py
cd lydarr-py
uv sync
```

Add entries to `anime.toml`:

```toml
[[media]]
title = "Frieren: Beyond Journey's End"
type = "anime"
submitters = ["SubsPlease"]

[[media]]
title = "One Piece"
type = "manga"
submitters = []          # empty = accept all uploaders
last_chapter = 1100      # daemon resumes from the next chapter
```

- Titles are fuzzy-matched against [AniList](https://anilist.co) (used for episode air times, chapter counts, and release status for both anime and manga).
- `submitters` filters by group name substring in the torrent title (e.g. `"SubsPlease"` matches `"[SubsPlease] ... - 01 (1080p)"`). Falls back to all results if none match.
- `search_name` (optional) overrides the title used for both AniList and Nyaa lookups — useful when the watchlist title doesn't fuzzy-match the AniList entry.
- `deprecated` (optional) marks an entry as inactive — preserved in the file but skipped by the daemon and shown separately in the UI.

## Usage

```bash
# Daemon only
uv run python -m lydarr

# Daemon + web UI
LYDARR_WEB=1 uv run python -m lydarr

# Web UI only (browse and manage without auto-tracking)
uv run python -m lydarr --web-only

# Bind to a specific address/port (e.g. behind a reverse proxy)
uv run python -m lydarr --web-only --host 127.0.0.1 --port 8080
```

The web UI is served at `http://localhost:8080` by default.

## How it works

For each entry in `anime.toml`, a coroutine runs concurrently via `asyncio.gather`:

**Anime:**
1. Fetches episode air schedule from AniList
2. Sleeps until the next episode's air time
3. Searches Nyaa.si (tries four query variants, filters by submitter, prefers HEVC/x265)
4. Retries every 30 minutes until a torrent is found
5. Adds the magnet to Transmission via its JSON-RPC API
6. Removes the entry from `anime.toml` once all episodes are downloaded

**Manga:**
1. Fetches chapter count and status from AniList
2. Downloads any chapters newer than `last_chapter` sequentially
3. Updates `last_chapter` in `anime.toml` after each successful add
4. Checks again every 24 hours (releasing/hiatus) or removes the entry when finished

## Web UI

Three resizable panels:

- **Media search** — search AniList by title (anime or manga), view status and next airing info, add to watchlist
- **Watchlist** — current `anime.toml` entries with submitter tags; click a title to search its torrents; edit submitters and search name inline; deprecate or remove entries
- **Torrent browser** — search Nyaa by title and optional episode number, filter by HEVC/x265 or torrent type (Trusted/Normal/Remake), sort by any column (resizable), add directly to Transmission

**Header** — red/green status dots for Transmission and Daemon. **Floating button** (bottom-right) starts and stops both the lydarr daemon and Transmission together.

## Running as a systemd service

A service template is included at `lydarr.service`. Install it as a user service:

```bash
# Install
mkdir -p ~/.config/systemd/user
cp lydarr.service ~/.config/systemd/user/lydarr.service
systemctl --user daemon-reload
systemctl --user enable --now lydarr

# Survive logout (start at boot without an active login session)
loginctl enable-linger
```

Environment variables go in `~/.config/lydarr/env` (one `KEY=value` per line, no `export`):

```bash
mkdir -p ~/.config/lydarr
cp .env.example ~/.config/lydarr/env
# edit ~/.config/lydarr/env
```

Common commands:

```bash
systemctl --user status lydarr
systemctl --user restart lydarr
systemctl --user stop lydarr
journalctl --user -u lydarr -f      # live logs
journalctl --user -u lydarr -n 100  # last 100 lines
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `ANIME_FILE` | `anime.toml` | Path to watchlist file |
| `TRANSMISSION_URL` | `http://localhost:9091/transmission/rpc` | Transmission RPC endpoint |
| `TRANSMISSION_USER` | unset | Transmission username (if auth enabled) |
| `TRANSMISSION_PASS` | unset | Transmission password (if auth enabled) |
| `LYDARR_DEFAULT_DIR` | `~/Downloads` | Download directory passed to Transmission |
| `LYDARR_WEB` | unset | Set to `1` to enable web UI alongside daemon |
| `LYDARR_WEB_HOST` | `0.0.0.0` | Web UI bind address (overridden by `--host`) |
| `LYDARR_WEB_PORT` | `8080` | Web UI port (overridden by `--port`) |
