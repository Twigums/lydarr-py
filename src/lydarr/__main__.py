"""Start the daemon and optional web server; handles CLI args."""
import argparse
import asyncio
import logging
import os
import sys
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import Any

from lydarr.config import AppConfig, load_config
from lydarr.file_manager import MediaState, read_entries
from lydarr.torrent_client import wait_for_client
from lydarr.tracker import track_media

_logger = logging.getLogger("lydarr")


def _setup_logging(log_file: str | None) -> None:
    fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    _logger.addHandler(sh)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        _logger.addHandler(fh)


def _fmt_utc(dt: datetime) -> str:
    off = dt.utcoffset()
    hours = int(off.total_seconds() // 3600) if off is not None else 0
    sign = "+" if hours >= 0 else "-"
    return f"{dt.strftime('%Y-%m-%d %H:%M')} UTC{sign}{abs(hours)}"


async def _nyaa_has_results(nyaa_name: str) -> bool:
    from nyaa.search import search
    from nyaa.types import TorrentSite, SearchParams, SortField, SortOrder
    try:
        results = await search(TorrentSite.NYAA_SI, SearchParams(
            keyword = nyaa_name,
            filters = 0,
            category = 1,
            subcategory = 2,
            sort = SortField.SEEDERS,
            order = SortOrder.DESC,
        ))
        return bool(results)
    except Exception:
        return True


async def _debug_report(cfg: AppConfig) -> None:
    from anilist.search import find_by_title
    from anilist.types import MediaType, MediaStatus

    entries = [e for e in read_entries(cfg.anime_file) if e.media_type == "anime" and not e.deprecated]
    if not entries:
        print("No active anime entries.")
        return

    for entry in entries:
        try:
            search_name = entry.search_name or entry.title
            info = await find_by_title(search_name, MediaType.ANIME)
            if info is None:
                print(f"  {entry.title}: not found on AniList")
                continue
            if info.status == MediaStatus.RELEASING:
                if info.next_airing_at and info.next_airing_episode:
                    air_time = datetime.fromtimestamp(info.next_airing_at, tz = timezone.utc)
                    print(f"  {entry.title}: ep {info.next_airing_episode:02d} at {_fmt_utc(air_time)}")
                    if not await _nyaa_has_results(search_name):
                        print(f"    ! No Nyaa results for \"{search_name}\"")
                        if not entry.search_name:
                            print(f"    -> Use the web UI to search and set a search name")
                else:
                    print(f"  {entry.title}: Releasing (no next episode scheduled)")
            else:
                print(f"  {entry.title}: {info.status.value}")
        except Exception as exc:
            print(f"  {entry.title}: error — {exc}")


async def _run(web_only: bool, host: str, port: int, debug: bool) -> None:
    cfg = load_config()

    if debug:
        await _debug_report(cfg)
        return

    if cfg.default_dir_set:
        _logger.info("Downloads will go to: $LYDARR_DEFAULT_DIR = %s", cfg.default_dir)
    else:
        _logger.info("$LYDARR_DEFAULT_DIR unset. Defaulting to %s", cfg.default_dir)

    if web_only:
        from lydarr.web.app import create_app
        import uvicorn

        state = MediaState(read_entries(cfg.anime_file))
        app = create_app(cfg, state)
        server = uvicorn.Server(uvicorn.Config(app, host = host, port = port, log_config = None))
        await server.serve()
        return

    await wait_for_client(cfg.transmission_url, cfg.transmission_user, cfg.transmission_pass)

    entries = read_entries(cfg.anime_file)
    if not entries:
        _logger.info("`anime.toml` is empty — add [[media]] entries or use --web-only")
        return

    titles = ", ".join(e.title for e in entries)
    _logger.info("Tracking %d title(s): %s", len(entries), titles)
    state = MediaState(entries)

    tasks: list[Coroutine[Any, Any, None]] = [track_media(cfg, state, entry) for entry in entries]

    if os.environ.get("LYDARR_WEB") == "1":
        from lydarr.web.app import create_app
        import uvicorn

        app = create_app(cfg, state)
        server = uvicorn.Server(uvicorn.Config(app, host = host, port = port, log_config = None))
        tasks.append(server.serve())

    await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description = "lydarr — anime/manga torrent tracker daemon")
    parser.add_argument("--web-only", action = "store_true",
                        help = "start web UI only without daemon tracking")
    parser.add_argument("--host", default = None,
                        help = "web UI bind address (default: 0.0.0.0, or $LYDARR_WEB_HOST)")
    parser.add_argument("--port", type = int, default = None,
                        help = "web UI port (default: 8080, or $LYDARR_WEB_PORT)")
    parser.add_argument("--debug", action = "store_true",
                        help = "print each tracked anime's next episode time (UTC) and exit")
    parser.add_argument("--log", metavar = "FILE", default = None,
                        help = "write daemon logs to FILE in addition to stdout")
    args = parser.parse_args()

    host = args.host if args.host is not None else os.environ.get("LYDARR_WEB_HOST", "0.0.0.0")
    port = args.port if args.port is not None else int(os.environ.get("LYDARR_WEB_PORT", "8080"))

    _setup_logging(args.log)

    try:
        asyncio.run(_run(web_only = args.web_only, host = host, port = port, debug = args.debug))
    except KeyboardInterrupt:
        print("\nShutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
