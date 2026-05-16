import pytest
from unittest.mock import AsyncMock, patch
from nyaa.types import Torrent, TorrentType
from lydarr.nyaa_search import (
    filter_submitters, prefer_hevc, is_hevc,
    search_episode, search_chapter, _anime_params, _manga_params,
)


def _make_torrent(name: str, magnet: str = "magnet:?xt=urn:btih:AABB") -> Torrent:
    return Torrent(
        id = "123",
        category = "Anime - English-translated",
        url = "https://nyaa.si/view/123",
        name = name,
        download_url = "https://nyaa.si/download/123.torrent",
        magnet = magnet,
        size = "1.37 GiB",
        date = "2025-03-29",
        seeders = 847,
        leechers = 23,
        completed = None,
        type = TorrentType.TRUSTED,
    )


SOLO_LEVELING_TORRENT = _make_torrent(
    "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv",
    magnet = "magnet:?xt=urn:btih:0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3",
)

ERAI_TORRENT = _make_torrent("[Erai-raws] Solo Leveling - 25 [720p].mkv")
HEVC_TORRENT = _make_torrent("[SubsPlease] Solo Leveling - 25 (1080p) [HEVC].mkv")
X265_TORRENT = _make_torrent("[SubsPlease] Solo Leveling - 25 (1080p) [x265].mkv")


def test_is_hevc_with_hevc():
    assert is_hevc("[Group] Show - 01 (1080p) [HEVC].mkv") is True
    assert is_hevc("[Group] Show - 01 (1080p) [hevc].mkv") is True


def test_is_hevc_with_x265():
    assert is_hevc("[Group] Show - 01 (1080p) [x265].mkv") is True
    assert is_hevc("[Group] Show - 01 (1080p) [X265].mkv") is True


def test_is_hevc_false():
    assert is_hevc("[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv") is False
    assert is_hevc("[Group] Show - 01 (720p).mkv") is False


def test_filter_submitters_subsplease_matches():
    torrents = [SOLO_LEVELING_TORRENT, ERAI_TORRENT]
    result = filter_submitters(torrents, ["SubsPlease"])
    assert len(result) == 1
    assert result[0].name == "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"


def test_filter_submitters_erai_not_match_subsplease():
    torrents = [SOLO_LEVELING_TORRENT, ERAI_TORRENT]
    result = filter_submitters(torrents, ["SubsPlease"])
    names = [t.name for t in result]
    assert not any("erai-raws" in n.lower() for n in names)


def test_filter_submitters_case_insensitive():
    torrents = [SOLO_LEVELING_TORRENT, ERAI_TORRENT]
    result = filter_submitters(torrents, ["subsplease"])
    assert len(result) == 1


def test_filter_submitters_erai_raws():
    torrents = [SOLO_LEVELING_TORRENT, ERAI_TORRENT]
    result = filter_submitters(torrents, ["erai-raws"])
    assert len(result) == 1
    assert "Erai-raws" in result[0].name


def test_filter_submitters_empty_submitters_returns_all():
    torrents = [SOLO_LEVELING_TORRENT, ERAI_TORRENT]
    result = filter_submitters(torrents, [])
    assert result == torrents


def test_filter_submitters_no_match_returns_all():
    torrents = [SOLO_LEVELING_TORRENT, ERAI_TORRENT]
    result = filter_submitters(torrents, ["NonexistentGroup"])
    assert result == torrents


def test_prefer_hevc_returns_hevc_when_present():
    torrents = [SOLO_LEVELING_TORRENT, HEVC_TORRENT]
    result = prefer_hevc(torrents)
    assert result == [HEVC_TORRENT]


def test_prefer_hevc_x265_preferred():
    torrents = [SOLO_LEVELING_TORRENT, X265_TORRENT]
    result = prefer_hevc(torrents)
    assert result == [X265_TORRENT]


def test_prefer_hevc_returns_all_when_no_hevc():
    torrents = [SOLO_LEVELING_TORRENT, ERAI_TORRENT]
    result = prefer_hevc(torrents)
    assert result == torrents


def test_prefer_hevc_empty_list():
    assert prefer_hevc([]) == []


def test_anime_params_correct_category():
    p = _anime_params("Solo Leveling - 25")
    assert p.category == 1
    assert p.subcategory == 2
    assert p.filters == 0
    assert p.keyword == "Solo Leveling - 25"


def test_manga_params_correct_category():
    p = _manga_params("One Piece - Chapter 001")
    assert p.category == 3
    assert p.subcategory == 1
    assert p.keyword == "One Piece - Chapter 001"


@pytest.mark.asyncio
async def test_search_episode_returns_magnet():
    fake_magnet = "magnet:?xt=urn:btih:0047E2A3DEADBEEF"
    fake_torrents = [_make_torrent("[SubsPlease] Solo Leveling - 25 (1080p).mkv", fake_magnet)]

    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, return_value = fake_torrents):
        result = await search_episode("Solo Leveling", 25, ["SubsPlease"])

    assert result == fake_magnet


@pytest.mark.asyncio
async def test_search_episode_no_results_returns_none():
    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, return_value = []):
        result = await search_episode("Solo Leveling", 25)

    assert result is None


@pytest.mark.asyncio
async def test_search_episode_pads_episode_number():
    captured_keywords = []

    async def mock_search(site, params):
        captured_keywords.append(params.keyword)
        return []

    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, side_effect = mock_search):
        await search_episode("Solo Leveling", 5)

    assert any("05" in kw for kw in captured_keywords)


@pytest.mark.asyncio
async def test_search_episode_tries_multiple_queries():
    call_count = 0

    async def mock_search(site, params):
        nonlocal call_count
        call_count += 1
        return []

    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, side_effect = mock_search):
        await search_episode("Solo Leveling", 25)

    assert call_count == 4


@pytest.mark.asyncio
async def test_search_episode_stops_on_first_result():
    fake_torrent = _make_torrent("[SubsPlease] Solo Leveling - 25 (1080p).mkv", "magnet:?xt=test")
    call_count = 0

    async def mock_search(site, params):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [fake_torrent]
        return []

    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, side_effect = mock_search):
        result = await search_episode("Solo Leveling", 25)

    assert call_count == 1
    assert result == "magnet:?xt=test"


@pytest.mark.asyncio
async def test_search_chapter_returns_magnet():
    fake_magnet = "magnet:?xt=urn:btih:CHAPTER001"
    fake_torrents = [_make_torrent("[Group] One Piece - Chapter 001.cbz", fake_magnet)]

    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, return_value = fake_torrents):
        result = await search_chapter("One Piece", 1)

    assert result == fake_magnet


@pytest.mark.asyncio
async def test_search_chapter_no_results_returns_none():
    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, return_value = []):
        result = await search_chapter("One Piece", 1100)

    assert result is None


@pytest.mark.asyncio
async def test_search_episode_exception_continues():
    import httpx
    fake_torrent = _make_torrent("[SubsPlease] Solo Leveling - 25 (1080p).mkv", "magnet:?xt=second")
    call_count = 0

    async def mock_search(site, params):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Network error")
        return [fake_torrent]

    with patch("lydarr.nyaa_search.search", new_callable = AsyncMock, side_effect = mock_search):
        result = await search_episode("Solo Leveling", 25)

    assert result == "magnet:?xt=second"
