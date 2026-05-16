import pytest
from nyaa.types import (
    TorrentSite, TorrentType, SortField, SortOrder,
    Torrent, TorrentDetail, FileEntry, SearchParams,
    NyaaError, HttpError, ParseError, NotFound,
    default_search_params,
)


def test_torrent_site_base_url():
    assert TorrentSite.NYAA_SI.base_url == "https://nyaa.si"
    assert TorrentSite.SUKEBEI_NYAA_SI.base_url == "https://sukebei.nyaa.si"
    assert TorrentSite.NYAA_LAND.base_url == "https://nyaa.land"


def test_torrent_site_values():
    assert TorrentSite.NYAA_SI.value == "nyaa.si"
    assert TorrentSite.SUKEBEI_NYAA_SI.value == "sukebei.nyaa.si"


def test_torrent_type_values():
    assert TorrentType.NORMAL.value == "normal"
    assert TorrentType.REMAKE.value == "remake"
    assert TorrentType.TRUSTED.value == "trusted"


def test_sort_field_values():
    assert SortField.ID.value == "id"
    assert SortField.SEEDERS.value == "seeders"
    assert SortField.LEECHERS.value == "leechers"
    assert SortField.SIZE.value == "size"
    assert SortField.DOWNLOADS.value == "downloads"


def test_sort_order_values():
    assert SortOrder.ASC.value == "asc"
    assert SortOrder.DESC.value == "desc"


def test_torrent_frozen():
    t = Torrent(
        id = "123",
        category = "Anime - English-translated",
        url = "https://nyaa.si/view/123",
        name = "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv",
        download_url = "https://nyaa.si/download/123.torrent",
        magnet = "magnet:?xt=urn:btih:0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3",
        size = "1.37 GiB",
        date = "2024-03-30",
        seeders = 847,
        leechers = 23,
        completed = None,
        type = TorrentType.TRUSTED,
    )
    assert t.id == "123"
    assert t.seeders == 847
    assert t.leechers == 23
    assert t.type == TorrentType.TRUSTED
    with pytest.raises(Exception):
        t.id = "456"


def test_file_entry_frozen():
    fe = FileEntry(name = "episode.mkv")
    assert fe.name == "episode.mkv"
    with pytest.raises(Exception):
        fe.name = "other.mkv"


def test_torrent_detail_mutable():
    td = TorrentDetail(
        id = "456",
        title = "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv",
        category = "Anime - English-translated",
        url = "https://nyaa.si/view/456",
        download_url = "https://nyaa.si/download/456.torrent",
        magnet = "magnet:?xt=urn:btih:0047E2A3DEADBEEF",
        size = "1.37 GiB",
        date = "2024-03-30",
        seeders = 847,
        leechers = 23,
        completed = 5000,
        type = TorrentType.TRUSTED,
        uploader = "SubsPlease",
        uploader_profile = "https://nyaa.si/user/SubsPlease",
        website = None,
        info_hash = "0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3",
    )
    td.seeders = 900
    assert td.seeders == 900
    assert td.files == []
    assert td.description == ""


def test_search_params_defaults():
    p = SearchParams(keyword = "Solo Leveling")
    assert p.user is None
    assert p.category == 0
    assert p.subcategory == 0
    assert p.filters == 2
    assert p.page == 0
    assert p.sort == SortField.ID
    assert p.order == SortOrder.DESC


def test_search_params_category_param():
    p = SearchParams(keyword = "test", category = 1, subcategory = 2)
    assert p.category_param == "1_2"

    p2 = SearchParams(keyword = "test", category = 0, subcategory = 0)
    assert p2.category_param == "0_0"


def test_default_search_params():
    p = default_search_params("Solo Leveling")
    assert p.keyword == "Solo Leveling"
    assert p.category == 0


def test_error_hierarchy():
    assert issubclass(HttpError, NyaaError)
    assert issubclass(ParseError, NyaaError)
    assert issubclass(NotFound, NyaaError)

    e = NyaaError("base")
    assert str(e) == "base"

    he = HttpError("http failed")
    assert isinstance(he, NyaaError)

    pe = ParseError("parse failed")
    assert isinstance(pe, NyaaError)

    nfe = NotFound("not found")
    assert isinstance(nfe, NyaaError)
