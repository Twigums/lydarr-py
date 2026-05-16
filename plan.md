# lydarr-py — Implementation Plan

Python port of the Haskell `lydarr` daemon, with an added web UI for manually browsing anime and torrents.

---

## Overview

lydarr-py has two modes of operation that can run together:

1. **Daemon** — reads `anime.txt`, tracks each anime concurrently, waits for air times, searches Nyaa, adds torrents to rtorrent automatically.
2. **Web UI** — a local browser interface to search AnimeSchedule, add anime to `anime.txt`, and browse/filter Nyaa torrent results before committing.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        lydarr-py                        │
│                                                         │
│  ┌──────────────┐     ┌────────────────────────────┐    │
│  │    Daemon    │     │          Web UI            │    │
│  │              │     │  FastAPI + vanilla JS      │    │
│  │ track_anime  │     │                            │    │
│  │  (asyncio)   │     │  /api/anime/search         │    │
│  │              │     │  /api/anime/add            │    │
│  │  anime.txt ◄─┼─────┼─ /api/torrents/search      │    │
│  │  rtorrent ◄──┼─────┼─ /api/torrents/add         │    │
│  └──────┬───────┘     └────────────┬───────────────┘    │
│         │                          │                    │
│    ┌────▼──────────────────────────▼────┐               │
│    │           Shared modules           │               │
│    │  modules/nyaa/   modules/          │               │
│    │  (Nyaa.si)       animeschedule/    │               │
│    └────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Project setup ✓

**Goal:** Runnable `uv`-managed Python project with all dependencies declared.

### Tasks
- [x] Create `pyproject.toml` with `uv` tooling and all dependencies
- [x] Create empty `anime.txt`
- [x] Create all `__init__.py` stubs to establish the package tree
- [x] Verify `uv sync` succeeds

### Dependencies

| Package | Purpose |
|---|---|
| `httpx` | Async HTTP client (nyaa + animeschedule) |
| `beautifulsoup4` | HTML parsing for Nyaa listing/detail pages |
| `lxml` | Fast BS4 parser backend |
| `defusedxml` | Safe XML parsing for Nyaa RSS feeds |
| `fastapi` | Web UI backend |
| `uvicorn[standard]` | ASGI server for FastAPI |
| `pyrosimple` | Provides `rtxmlrpc` CLI used for rtorrent interaction |

---

## Phase 2 — `modules/nyaa/` package ✓

Port of `/home/twi/git/nyaa-hs`. Implements Nyaa.si scraping via both RSS and HTML.

### `modules/nyaa/types.py`
- `TorrentSite` enum: `NYAA_SI`, `SUKEBEI_NYAA_SI`, `NYAA_LAND`
- `TorrentType` enum: `NORMAL`, `REMAKE`, `TRUSTED`
- `SortField` enum: `ID`, `SIZE`, `SEEDERS`, `LEECHERS`, `DOWNLOADS`
- `SortOrder` enum: `ASC`, `DESC`
- `@dataclass(frozen=True) Torrent` — id, category, url, name, download_url, magnet, size, date, seeders, leechers, completed, type
- `@dataclass(frozen=True) TorrentDetail` — extends Torrent with uploader, info_hash, files, description
- `@dataclass SearchParams` — keyword, user, category, subcategory, filters, page, sort, order; `default_search_params(keyword)` constructor
- `NyaaError(Exception)` base; `HttpError`, `ParseError`, `NotFound` subclasses

### `modules/nyaa/categories.py`
- `NYAA_CATEGORIES: dict[tuple[str, str], str]` — maps `("1","2")` → `"Anime - English-translated"` etc.
- `SUKEBEI_CATEGORIES: dict[tuple[str, str], str]`
- `category_for_site(site, raw) -> str` — looks up from category URL fragment

### `modules/nyaa/magnet.py`
- `MAGNET_TRACKERS: list[str]`
- `magnet_builder(info_hash, title) -> str` — builds `magnet:?xt=urn:btih:...` URL with percent-encoding

### `modules/nyaa/http.py`
- Async httpx client (module-level `AsyncClient` or per-call)
- `fetch_listing(site) -> bytes`
- `fetch_view(site, vid) -> bytes`
- `fetch_user_page(site, username) -> bytes`
- `fetch_search_rss(site, params) -> bytes` — primary search path (no user filter)
- `fetch_search_html(site, params) -> bytes` — user-filtered search

All raise `HttpError` on failure.

### `modules/nyaa/parser/rss.py`
- `parse_nyaa_rss(site, data, limit=None) -> list[Torrent]`
- Uses `defusedxml` to parse RSS `<item>` elements
- Extracts nyaa namespace fields (`nyaa:seeders`, `nyaa:infoHash`, etc.)
- Builds magnet via `magnet_builder` when `infoHash` is present

### `modules/nyaa/parser/html.py`
- `parse_nyaa(site, data, limit=None) -> list[Torrent]`
- `parse_single(site, data) -> TorrentDetail`
- Uses `BeautifulSoup(data, "lxml")`
- Parses `<tbody><tr>` rows for listing; panel detail page for single torrent

### `modules/nyaa/search.py`
- `search(site, params) -> list[Torrent]` — RSS path (no user); HTML path (with user)
- `get_torrent(site, vid) -> TorrentDetail`
- `last_uploads(site, limit=None) -> list[Torrent]`
- `get_from_user(site, username, limit=None) -> list[Torrent]`

---

## Phase 3 — `modules/animeschedule/` package ✓

Port of `/home/twi/git/animeschedule-hs`. Client for the AnimeSchedule.net v3 API (no auth required for search).

### `modules/animeschedule/types.py`
- `AirStatus` enum: `UPCOMING`, `ONGOING`, `DELAYED`, `FINISHED`, `UNKNOWN`
- `SeasonName` enum: `WINTER`, `SPRING`, `SUMMER`, `FALL`
- `@dataclass AnimeDetail` — title, route, premier, sub_premier, dub_premier, jpn_time, sub_time, dub_time, status, episodes
- `@dataclass EpisodeRecord` — number, raw, sub, dub (all `datetime | None`)
- `ScheduleError(Exception)` base; `HttpError`, `ParseError`, `AuthError`, `NotFoundError` subclasses

### `modules/animeschedule/models.py`
- `AnimeJson` dataclass parsed from API JSON (`title`, `route`, `status`, `premier`, `subPremier`, etc.)
- `NULL_SENTINEL = "0001-01-01T00:00:00Z"` — API's null date representation
- `parse_utc(text) -> datetime | None`
- `to_anime_detail(aj) -> AnimeDetail`
- `AnimePage` dataclass: `page`, `total_amount`, `anime: list[AnimeJson]`

### `modules/animeschedule/endpoints.py`
- `BASE_URL = "https://animeschedule.net/api/v3"`
- `anime_list_url(query=None, seasons=None, airing_status=None, page=1) -> str`
- `anime_slug_url(slug) -> str`

### `modules/animeschedule/http.py`
- `get_json_no_auth(url, params=None) -> dict` — async httpx GET, raises `ScheduleError` on non-2xx

### `modules/animeschedule/episodes.py`
- `episode_utc(premier, jpn_time, n) -> datetime` — premier day + (n-1)*7 days + jpn_time's time-of-day
- `all_episodes(premier, jpn_time, total) -> list[datetime]`
- `feed_episodes(premier, jpn_time, total) -> list[datetime | None]`
- `compute_episodes(detail) -> list[EpisodeRecord]` — builds raw/sub/dub episode lists

### `modules/animeschedule/season.py`
- `current_season(now) -> tuple[SeasonName, int]`
- `season_slug(season, year) -> str` — e.g. `"spring-2025"`

### `modules/animeschedule/schedule.py`
- `search_anime(query) -> list[AnimeJson]`
- `find_best_match(query, candidates) -> AnimeJson | None` — exact then partial title match
- `fetch_by_name(name) -> tuple[AnimeDetail, list[EpisodeRecord]]` — raises `ScheduleError` if not found
- `fetch_current_schedule() -> list[CurrentEntry]` — all ongoing anime this season with next ep time

---

## Phase 4 — `src/lydarr/` daemon ✓

Direct port of the Haskell `App.*` modules.

### `src/lydarr/config.py`
- `@dataclass AppConfig` — `anime_file`, `rtxmlrpc_cmd`, `default_dir`, `default_dir_set`
- `load_config() -> AppConfig` — reads env vars with same defaults as Haskell version
- `read_anime_list(path) -> list[str]` — strips blank lines

### `src/lydarr/rtorrent.py`
- `POLL_INTERVAL = 5` (seconds)
- `is_rtorrent_up(cmd) -> bool` — async subprocess `rtxmlrpc system.listMethods`
- `wait_for_rtorrent(cmd)` — polls until up, prints status
- `add_magnet(cmd, magnet) -> bool` — async subprocess `rtxmlrpc load.start "" <magnet>`

### `src/lydarr/nyaa_search.py`
- `is_hevc(name) -> bool` — checks for "hevc" or "x265" in name (case-insensitive)
- `prefer_hevc(torrents) -> list[Torrent]` — returns HEVC subset if any, else all
- `search_episode(name, ep_num) -> str | None` — tries 4 query variants (`Name - 01`, `Name - 001`, `Name 01`, `Name 001`), returns magnet or None

### `src/lydarr/file_manager.py`
- `AnimeState` class
  - `_lock: asyncio.Lock`
  - `_titles: list[str]`
  - `async remove(path, name)` — removes title under lock, writes updated `anime.txt`

### `src/lydarr/tracker.py`
- `log_info(name, msg)` — `print(f"[{name}] {msg}")`
- `sleep_until(target)` — async sleep until a UTC datetime
- `next_episode_time(episodes, now) -> tuple[int, datetime] | None`
- `wait_and_add(cfg, name, ep_num)` — retry loop every 30min until torrent found and added; warns every 48 attempts (~24h)
- `download_all(cfg, name, total)` — concurrent `wait_and_add` for eps 1..total via `asyncio.gather`
- `track_anime(cfg, state, name)` — main async loop; handles all `AirStatus` cases identically to Haskell

### `src/lydarr/__main__.py`
- Parse `--web-only` flag
- `load_config()`, print env info
- `await wait_for_rtorrent(...)` (skip if `--web-only`)
- `read_anime_list(...)`, validate non-empty
- `await asyncio.gather(track_anime(cfg, state, name) for name in animes)`
- If `LYDARR_WEB=1` or `--web-only`: also start uvicorn alongside the gather

---

## Phase 5 — `src/lydarr/web/` — Web UI ✓

A lightweight local browser interface. Not intended for public exposure.

### Purpose

| Feature | Description |
|---|---|
| Anime search | Type a title → query AnimeSchedule → show results with status, episodes, air time |
| Add to watchlist | Click "Track" → appends title to `anime.txt` |
| Torrent browser | Search Nyaa for a title + optional episode number → results table |
| Torrent filter | Toggle "HEVC/x265 only", filter by type (Trusted/Normal/Remake) |
| Manual add | "Add to rtorrent" button → sends magnet to rtorrent via `add_magnet()` |

### API routes

#### `src/lydarr/web/routes/anime.py`
- `GET /api/anime/search?q=<query>`
  - Calls `animeschedule.schedule.search_anime(q)`
  - Returns `list[AnimeSearchResult]`: `{title, route, status, episodes, next_sub_time}`
- `POST /api/anime/add`
  - Body: `{"title": str}`
  - Appends to `anime.txt` if not already present
  - Returns `{"added": true}` or `{"added": false, "reason": "already tracked"}`

#### `src/lydarr/web/routes/torrents.py`
- `GET /api/torrents/search?q=<query>&ep=<n>&site=nyaa_si&hevc_only=false`
  - Calls `nyaa.search.search(site, params)` using the anime + episode query variants
  - Returns `list[TorrentResult]`: `{id, name, size, date, seeders, leechers, type, magnet, download_url}`
- `POST /api/torrents/add`
  - Body: `{"magnet": str}`
  - Calls `lydarr.rtorrent.add_magnet(cfg.rtxmlrpc_cmd, magnet)`
  - Returns `{"ok": true}` or `{"ok": false, "error": str}`

#### `src/lydarr/web/routes/daemon.py`

Manages the daemon as a live `asyncio.Task` stored in `app.state.daemon_task`.

- `GET /api/daemon/status`
  - Returns: `{running: bool, tracking: list[str], started_at: str | null}`
  - `tracking` is the current contents of `AnimeState` (anime actively being watched)
  - `started_at` is an ISO 8601 timestamp of when the daemon task was last started

- `POST /api/daemon/start`
  - No-op if daemon is already running → `{ok: false, reason: "already running"}`
  - Creates a new `asyncio.Task` for `main_daemon(cfg, state)`, stores it on `app.state`
  - Returns `{ok: true}`

- `POST /api/daemon/stop`
  - Cancels `app.state.daemon_task` and awaits it
  - Returns `{ok: true}` or `{ok: false, reason: "not running"}`

- `GET /api/rtorrent/status`
  - Calls `is_rtorrent_up(cfg.rtxmlrpc_cmd)` via async subprocess
  - Returns `{online: bool}`

### `src/lydarr/web/app.py`

FastAPI app with shared state accessible from all routes:

- `app.state.cfg: AppConfig`
- `app.state.anime_state: AnimeState`
- `app.state.daemon_task: asyncio.Task | None`
- `app.state.daemon_started_at: datetime | None`

On startup (`lifespan` context manager): populate config and anime state; optionally auto-start daemon if `LYDARR_WEB != "only"`.

### `src/lydarr/web/static/index.html`

Single HTML file with embedded CSS and vanilla JS (no build step, no framework). Three sections:

**Top bar — Status & Control**
- rtorrent status indicator: green dot "Online" / red dot "Offline" — polls `GET /api/rtorrent/status` every 10s
- Daemon status indicator: green "Running" / grey "Stopped" + comma-separated list of currently-tracked titles
- "Start" / "Stop" toggle button → POST `/api/daemon/start` or `/api/daemon/stop`; re-fetches status after response
- Last-started timestamp shown when running

**Left panel — Anime Search**
- Text input + "Search" button
- Results list: title, color-coded status badge (Ongoing/Upcoming/Finished/Delayed), episode count, next sub airtime
- "Track" button per result → POST `/api/anime/add`
- Inline feedback: "Added" checkmark or "Already tracked" notice

**Right panel — Torrent Browser**
- Text input for title
- Optional episode number input
- Site selector: Nyaa.si (default) / Sukebei
- "HEVC/x265 only" checkbox (client-side filter on results)
- Type filter: All / Trusted / Normal / Remake
- Results table columns: Name, Size, Seeders, Type (colored badge), [Magnet link] [Add to rtorrent]
- "Add to rtorrent" triggers POST `/api/torrents/add` and shows inline success/failure

---

## Phase 6 — Integration + CLI ✓

- `src/lydarr/__main__.py` wires daemon + web server together with `asyncio.gather`
- Uvicorn is started as an asyncio task (not in a separate thread) using `uvicorn.Server` directly
- `--web-only` flag: skips daemon, only serves web UI
- `KeyboardInterrupt` propagates cleanly through gather

---

## Dependency summary

```toml
[project]
dependencies = [
    "httpx",
    "beautifulsoup4",
    "lxml",
    "defusedxml",
    "fastapi",
    "uvicorn[standard]",
    "pyrosimple",
]
```

---

## Open question (deferred)

**rtorrent interaction:** Currently planned to shell out to `rtxmlrpc` (subprocess) to match the Haskell version exactly. Could alternatively use pyrosimple's Python API directly. Confirm preference before implementing Phase 4.

---

## Implementation order

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
  setup   modules/  modules/  src/lydarr  web UI    wire-up
          nyaa/     anisched/
```

Each phase is independently testable before moving to the next.
