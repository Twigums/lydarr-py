import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nyaa.types import TorrentSite, TorrentType, Torrent, SearchParams, SortField, SortOrder


def _make_torrent(id = "123", name = "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"):
    return Torrent(
        id = id,
        category = "Anime - English-translated",
        url = f"https://nyaa.si/view/{id}",
        name = name,
        download_url = f"https://nyaa.si/download/{id}.torrent",
        magnet = "magnet:?xt=urn:btih:0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3",
        size = "1.37 GiB",
        date = "2025-03-29",
        seeders = 847,
        leechers = 23,
        completed = None,
        type = TorrentType.TRUSTED,
    )


@pytest.mark.asyncio
async def test_search_without_user_uses_rss():
    params = SearchParams(keyword = "Solo Leveling - 25")
    fake_torrents = [_make_torrent()]
    fake_bytes = b"<rss/>"

    with patch("nyaa.search.fetch_search_rss", new_callable = AsyncMock, return_value = fake_bytes) as mock_rss, \
         patch("nyaa.search.parse_nyaa_rss", return_value = fake_torrents) as mock_parse:
        from nyaa.search import search
        result = await search(TorrentSite.NYAA_SI, params)

    mock_rss.assert_called_once_with(TorrentSite.NYAA_SI, params)
    mock_parse.assert_called_once_with(TorrentSite.NYAA_SI, fake_bytes)
    assert result == fake_torrents


@pytest.mark.asyncio
async def test_search_with_user_uses_html():
    params = SearchParams(keyword = "Solo Leveling - 25", user = "SubsPlease")
    fake_torrents = [_make_torrent()]
    fake_bytes = b"<html/>"

    with patch("nyaa.search.fetch_search_html", new_callable = AsyncMock, return_value = fake_bytes) as mock_html, \
         patch("nyaa.search.parse_nyaa", return_value = fake_torrents) as mock_parse:
        from nyaa.search import search
        result = await search(TorrentSite.NYAA_SI, params)

    mock_html.assert_called_once_with(TorrentSite.NYAA_SI, params)
    mock_parse.assert_called_once_with(TorrentSite.NYAA_SI, fake_bytes)
    assert result == fake_torrents


@pytest.mark.asyncio
async def test_last_uploads():
    fake_torrents = [_make_torrent()]
    fake_bytes = b"<html/>"

    with patch("nyaa.search.fetch_listing", new_callable = AsyncMock, return_value = fake_bytes), \
         patch("nyaa.search.parse_nyaa", return_value = fake_torrents):
        from nyaa.search import last_uploads
        result = await last_uploads(TorrentSite.NYAA_SI, limit = 10)

    assert result == fake_torrents


@pytest.mark.asyncio
async def test_last_uploads_no_limit():
    fake_torrents = [_make_torrent()]
    fake_bytes = b"<html/>"

    with patch("nyaa.search.fetch_listing", new_callable = AsyncMock, return_value = fake_bytes), \
         patch("nyaa.search.parse_nyaa", return_value = fake_torrents) as mock_parse:
        from nyaa.search import last_uploads
        result = await last_uploads(TorrentSite.NYAA_SI)

    mock_parse.assert_called_once_with(TorrentSite.NYAA_SI, fake_bytes, None)


@pytest.mark.asyncio
async def test_get_torrent():
    from nyaa.types import TorrentDetail, FileEntry
    fake_detail = MagicMock(spec = TorrentDetail)
    fake_bytes = b"<html/>"

    with patch("nyaa.search.fetch_view", new_callable = AsyncMock, return_value = fake_bytes), \
         patch("nyaa.search.parse_single", return_value = fake_detail):
        from nyaa.search import get_torrent
        result = await get_torrent(TorrentSite.NYAA_SI, 1234567)

    assert result is fake_detail


@pytest.mark.asyncio
async def test_get_from_user():
    fake_torrents = [_make_torrent()]
    fake_bytes = b"<html/>"

    with patch("nyaa.search.fetch_user_page", new_callable = AsyncMock, return_value = fake_bytes), \
         patch("nyaa.search.parse_nyaa", return_value = fake_torrents):
        from nyaa.search import get_from_user
        result = await get_from_user(TorrentSite.NYAA_SI, "SubsPlease", limit = 5)

    assert result == fake_torrents
