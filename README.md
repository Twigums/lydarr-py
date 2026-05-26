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

# Write logs to a file in addition to stdout
uv run python -m lydarr --log lydarr.log
```

The web UI is served at `http://localhost:8080` by default.

## How it works

For each entry in `anime.toml`, a coroutine runs concurrently via `asyncio.gather`:

**Anime:**
1. Fetches episode air schedule from AniList
2. Sleeps until the next episode's air time
3. Searches Nyaa.si (tries four query variants, filters by submitter, prefers HEVC/x265)
4. Retries every 30 minutes until a torrent is found
5. Adds the magnet to Transmission via its JSON-RPC API, saving to a per-title subfolder under `LYDARR_DEFAULT_DIR`
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

When adding a torrent from the browser, click the show title in the watchlist panel first to set the download folder context — the torrent will be saved to the correct per-title subfolder under `LYDARR_DEFAULT_DIR`. Clearing the search box (✕) resets the context.

**Header** — red/green status dots for Transmission and Daemon. **Floating button** (bottom-right) starts and stops both the lydarr daemon and Transmission together via `systemctl --user`.

## Running as a systemd service

### Transmission

Both lydarr and Transmission must run as the **same user** so Transmission can write to that user's download directory. The system package unit (`/lib/systemd/system/transmission-daemon.service`) runs as `debian-transmission`, so a user-level unit is required instead:

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/transmission-daemon.service << 'EOF'
[Unit]
Description=Transmission BitTorrent Daemon
Wants=network-online.target
After=network-online.target

[Service]
Type=notify
ExecStart=/usr/bin/transmission-daemon -f --log-level=error
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now transmission-daemon
```

#### rclone / FUSE download targets

If `LYDARR_DEFAULT_DIR` is on an rclone FUSE mount, disable partial-file renaming in Transmission's `~/.config/transmission-daemon/settings.json` (stop Transmission first, edit, then restart):

```json
"rename-partial-files": false
```

Without this, Transmission downloads to `filename.mkv.part` and renames on completion — rclone FUSE does not support that rename and the transfer fails with an I/O error.

### Lydarr

A service template is included at `lydarr.service`. It assumes the repo is at `~/git/lydarr-py`; adjust the paths if needed:

```bash
# Install
mkdir -p ~/.config/systemd/user
cp lydarr.service ~/.config/systemd/user/lydarr.service
systemctl --user daemon-reload
systemctl --user enable --now lydarr

# Survive logout (keeps user services running without an active login session)
# Required for both lydarr and transmission-daemon user services
loginctl enable-linger
```

Environment variables go in `~/.config/lydarr/env` (one `KEY=value` per line, no `export`). Use absolute paths — the working directory when running as a service may differ from the repo root:

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
| `ANIME_FILE` | `anime.toml` | Path to watchlist file (use absolute path when running as a service) |
| `TRANSMISSION_URL` | `http://localhost:9091/transmission/rpc` | Transmission RPC endpoint |
| `TRANSMISSION_USER` | unset | Transmission username (if auth enabled) |
| `TRANSMISSION_PASS` | unset | Transmission password (if auth enabled) |
| `LYDARR_DEFAULT_DIR` | `~/Downloads` | Root download directory; each title gets its own subfolder |
| `LYDARR_USER` | unset | Web UI username for HTTP Basic Auth; leave unset to disable auth |
| `LYDARR_PASS` | unset | Web UI password; required when `LYDARR_USER` is set |
| `LYDARR_WEB` | unset | Set to `1` to enable web UI alongside daemon |
| `LYDARR_WEB_HOST` | `0.0.0.0` | Web UI bind address (overridden by `--host`) |
| `LYDARR_WEB_PORT` | `8080` | Web UI port (overridden by `--port`) |
