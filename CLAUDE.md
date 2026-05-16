# lydarr-py — Claude Code Guide

## What this is

Python port of [lydarr](https://github.com/Twigums/lydarr) (Haskell). Daemon that tracks airing anime and releasing manga, searches Nyaa.si for subbed torrents/scanlations, and adds them to Transmission. Includes a web UI for searching media, managing the watchlist, and browsing torrent results manually.

The `nyaa/` and `animeschedule/` packages are **first-party inline ports** of the Haskell libraries at `/home/twi/git/nyaa-hs` and `/home/twi/git/animeschedule-hs`. Do not import external nyaa or animeschedule Python libraries — reimplement from the Haskell source.

The `anilist/` package is a lightweight GraphQL client for the [AniList API](https://anilist.co/graphiql), used for web UI search and manga status/chapter tracking.

See `plan.md` for the full roadmap.

---

## Package layout

```
lydarr-py/
├── anime.toml              # Watchlist: [[media]] blocks with title, type, submitters
├── modules/
│   ├── nyaa/               # Port of nyaa-hs — Nyaa.si scraping + search
│   │   ├── types.py        # Torrent, SearchParams, NyaaError, enums
│   │   ├── categories.py   # Category map lookups
│   │   ├── magnet.py       # magnet_builder()
│   │   ├── http.py         # Async httpx fetchers
│   │   ├── search.py       # Public API: search(), get_torrent(), etc.
│   │   └── parser/
│   │       ├── _utils.py   # Shared helpers: last_segment(), read_int()
│   │       ├── rss.py      # RSS feed → list[Torrent]
│   │       └── html.py     # HTML listing/detail → list[Torrent] / TorrentDetail
│   ├── animeschedule/      # Port of animeschedule-hs — AnimeSchedule API client
│   │   ├── types.py        # AnimeDetail, EpisodeRecord, AirStatus, ScheduleError
│   │   ├── models.py       # JSON → domain types
│   │   ├── endpoints.py    # URL builders
│   │   ├── http.py         # get_json_no_auth()
│   │   ├── episodes.py     # episode_utc(), feed_episodes(), compute_episodes()
│   │   ├── season.py       # current_season(), season_slug()
│   │   └── schedule.py     # search_anime(), fetch_by_name(), fetch_current_schedule()
│   └── anilist/            # AniList GraphQL client — media search and status
│       ├── types.py        # AnilistMedia, MediaType, MediaStatus, AnilistError
│       ├── http.py         # graphql() POST helper
│       └── search.py       # search(), find_by_title()
└── src/
    └── lydarr/
        ├── config.py       # AppConfig from env vars (Transmission URL/auth, media file, download dir)
        ├── torrent_client.py  # is_client_up(), wait_for_client(), add_magnet(), _rpc() via Transmission JSON-RPC
        ├── nyaa_search.py  # search_episode(), search_chapter(): query variants, filter_submitters(), prefer_hevc()
        ├── file_manager.py # MediaEntry(title, type, submitters, deprecated), MediaState, read_entries(), TOML I/O
        ├── tracker.py      # track_media(cfg, state, entry) async coroutine; dispatches anime vs manga
        ├── web/            # FastAPI web UI
        │   ├── app.py      # create_app(cfg, state); app.state holds cfg, anime_state, daemon_task
        │   ├── routes/
        │   │   ├── anime.py    # /api/anime/search|list|add|remove|deprecate|reactivate|submitters|status
        │   │   ├── torrents.py # /api/torrents/search, /api/torrents/add
        │   │   └── daemon.py   # /api/daemon/status|start|stop; /api/rtorrent/status; /api/transmission/start|stop
        │   └── static/
        │       └── index.html  # Single-page UI: 3 resizable panels, floating Start/Stop FAB
        └── __main__.py     # asyncio.run(main()); starts daemon + optional web server; --host/--port flags
```

---

## Key decisions

| Decision | Choice | Reason |
|---|---|---|
| Concurrency | `asyncio` + `asyncio.gather` | One coroutine per title, I/O-bound throughout |
| HTTP | `httpx` async client | Handles AnimeSchedule JSON, AniList GraphQL, Nyaa bytes, and Transmission RPC |
| HTML parsing | `beautifulsoup4` + `lxml` backend | Direct equivalent of html-conduit |
| XML/RSS parsing | `defusedxml` | Safe XML; equivalent of xml-conduit |
| Torrent client | Transmission JSON-RPC | Lightweight, simple API, no extra binary needed |
| Watchlist format | TOML (`anime.toml`) | Human-editable, supports per-title metadata (type, submitters, search_name) |
| Web framework | FastAPI | Async-native, minimal |
| Type annotations | Full throughout | Dataclasses for records, `Enum` for sum types |
| Anime scheduling | AnimeSchedule API | Episode air times; daemon uses this for sleep-until logic |
| Manga status | AniList GraphQL API | Chapter counts and release status; web UI uses it for both anime and manga search |
| Transmission stop | `session-close` RPC | Graceful shutdown via existing RPC channel; no subprocess or PID files |

---

## Watchlist format

```toml
[[media]]
title = "Frieren: Beyond Journey's End"
type = "anime"
submitters = ["SubsPlease", "Erai-raws"]

[[media]]
title = "One Piece"
type = "manga"
submitters = []        # empty = accept all uploaders
last_chapter = 1100   # daemon resumes from next chapter
search_name = ""      # overrides title for Nyaa queries if set
deprecated = true     # hidden in UI; skipped by daemon; can be reactivated
```

Fields:
- `title` — must match AnimeSchedule (for anime) or AniList (for manga) exactly
- `type` — `"anime"` or `"manga"` (default: `"anime"`)
- `submitters` — case-insensitive substring match against torrent title; falls back to all results if empty or no match
- `last_chapter` — manga only; daemon downloads chapters after this number
- `search_name` — optional Nyaa query override (e.g. for sequel season naming differences)
- `deprecated` — optional boolean (default `false`); entry is preserved but hidden/inactive

Read with stdlib `tomllib`; written with a minimal custom serialiser (no extra dependency).

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `ANIME_FILE` | `anime.toml` | Path to watchlist file |
| `TRANSMISSION_URL` | `http://localhost:9091/transmission/rpc` | Transmission RPC endpoint |
| `TRANSMISSION_USER` | unset | Transmission username (if auth enabled) |
| `TRANSMISSION_PASS` | unset | Transmission password (if auth enabled) |
| `LYDARR_DEFAULT_DIR` | `~/Downloads` | Download directory passed to Transmission |
| `LYDARR_USER` | unset | Web UI username for HTTP Basic Auth; leave unset to disable auth |
| `LYDARR_PASS` | unset | Web UI password for HTTP Basic Auth; required when `LYDARR_USER` is set |
| `LYDARR_WEB` | unset | Set to `1` to enable web UI alongside daemon |
| `LYDARR_WEB_HOST` | `0.0.0.0` | Web UI bind address (overridden by `--host`) |
| `LYDARR_WEB_PORT` | `8080` | Web UI port (overridden by `--port`) |

---

## Running

```bash
# Install deps
uv sync

# Run daemon only
uv run python -m lydarr

# Run daemon + web UI
LYDARR_WEB=1 uv run python -m lydarr

# Web UI only (for manual torrent browsing, no tracking)
uv run python -m lydarr --web-only

# Bind to localhost (e.g. behind a reverse proxy)
uv run python -m lydarr --web-only --host 127.0.0.1 --port 8080
```

---

## Conventions

- **snake_case** everywhere — functions, variables, modules
- **No comments** unless the why is non-obvious (a hidden constraint, workaround, etc.)
- **Dataclasses** for all record types; `frozen=True` where the object shouldn't mutate
- **Custom exceptions** (`NyaaError`, `ScheduleError`, `AnilistError`) for domain errors; catch at the tracker boundary
- **`asyncio.sleep`** instead of `time.sleep` — all loops are async
- Prefer returning `None` over raising when a "not found" is a normal outcome (e.g., no torrent yet)

---

## Haskell → Python reference

| Haskell | Python |
|---|---|
| `mapConcurrently_` | `asyncio.gather(*coros)` |
| `threadDelay n` | `await asyncio.sleep(n)` |
| `TVar [Text]` | `MediaState` class with `asyncio.Lock` |
| `try @SomeException` | `try: ... except Exception:` |
| `Either NyaaError a` | raise `NyaaError` / return value |
| `Maybe a` | `a \| None` |
| `fromMaybe def val` | `val or default` |
| `T.isInfixOf` | `substring in string` |
| `T.toLower` | `str.lower()` |
| `printf "%02d" n` | `f"{n:02d}"` |
