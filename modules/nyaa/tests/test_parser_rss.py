import pytest
from nyaa.types import TorrentSite, TorrentType
from nyaa.parser.rss import parse_nyaa_rss

_NYAA_NS = "https://nyaa.si/xmlns/nyaa"

SOLO_LEVELING_RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:nyaa="{_NYAA_NS}">
  <channel>
    <title>Nyaa</title>
    <item>
      <title>[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv</title>
      <link>https://nyaa.si/download/1234567.torrent</link>
      <guid>https://nyaa.si/view/1234567</guid>
      <pubDate>Sat, 29 Mar 2025 12:00:00 +0000</pubDate>
      <nyaa:seeders>847</nyaa:seeders>
      <nyaa:leechers>23</nyaa:leechers>
      <nyaa:downloads>5000</nyaa:downloads>
      <nyaa:infoHash>0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3</nyaa:infoHash>
      <nyaa:category>Anime - English-translated</nyaa:category>
      <nyaa:categoryId>1_2</nyaa:categoryId>
      <nyaa:size>1.37 GiB</nyaa:size>
      <nyaa:trusted>Yes</nyaa:trusted>
      <nyaa:remake>No</nyaa:remake>
    </item>
    <item>
      <title>[Erai-raws] Solo Leveling Season 2 - 25 [720p].mkv</title>
      <link>https://nyaa.si/download/7654321.torrent</link>
      <guid>https://nyaa.si/view/7654321</guid>
      <pubDate>Sat, 29 Mar 2025 13:00:00 +0000</pubDate>
      <nyaa:seeders>120</nyaa:seeders>
      <nyaa:leechers>5</nyaa:leechers>
      <nyaa:downloads>800</nyaa:downloads>
      <nyaa:infoHash>AABBCCDDEEFF00112233445566778899AABBCCDD</nyaa:infoHash>
      <nyaa:category>Anime - English-translated</nyaa:category>
      <nyaa:categoryId>1_2</nyaa:categoryId>
      <nyaa:size>512.0 MiB</nyaa:size>
      <nyaa:trusted>No</nyaa:trusted>
      <nyaa:remake>No</nyaa:remake>
    </item>
  </channel>
</rss>
"""

REMAKE_RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:nyaa="{_NYAA_NS}">
  <channel>
    <item>
      <title>[BadGroup] Show - 01 (1080p).mkv</title>
      <guid>https://nyaa.si/view/99999</guid>
      <nyaa:seeders>1</nyaa:seeders>
      <nyaa:leechers>0</nyaa:leechers>
      <nyaa:infoHash>DEADBEEF</nyaa:infoHash>
      <nyaa:trusted>No</nyaa:trusted>
      <nyaa:remake>Yes</nyaa:remake>
      <nyaa:size>700 MiB</nyaa:size>
      <nyaa:category>Anime - English-translated</nyaa:category>
    </item>
  </channel>
</rss>
"""

MISSING_FIELDS_RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:nyaa="{_NYAA_NS}">
  <channel>
    <item>
      <title></title>
      <guid>https://nyaa.si/view/11111</guid>
    </item>
    <item>
      <title>Valid Title</title>
    </item>
  </channel>
</rss>
"""

INVALID_XML = b"not xml at all <<<"


def test_parse_rss_returns_torrents():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, SOLO_LEVELING_RSS.encode())
    assert len(results) == 2


def test_parse_rss_first_torrent_fields():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, SOLO_LEVELING_RSS.encode())
    t = results[0]
    assert t.name == "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"
    assert t.id == "1234567"
    assert t.url == "https://nyaa.si/view/1234567"
    assert t.seeders == 847
    assert t.leechers == 23
    assert t.size == "1.37 GiB"
    assert t.type == TorrentType.TRUSTED
    assert t.category == "Anime - English-translated"


def test_parse_rss_magnet_built_from_hash():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, SOLO_LEVELING_RSS.encode())
    t = results[0]
    assert "magnet:?xt=urn:btih:0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3" in t.magnet


def test_parse_rss_second_torrent_normal_type():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, SOLO_LEVELING_RSS.encode())
    t = results[1]
    assert t.type == TorrentType.NORMAL
    assert t.seeders == 120


def test_parse_rss_remake_type():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, REMAKE_RSS.encode())
    assert len(results) == 1
    assert results[0].type == TorrentType.REMAKE


def test_parse_rss_limit():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, SOLO_LEVELING_RSS.encode(), limit = 1)
    assert len(results) == 1
    assert results[0].name == "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"


def test_parse_rss_skips_empty_title():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, MISSING_FIELDS_RSS.encode())
    assert len(results) == 0


def test_parse_rss_invalid_xml_raises():
    from nyaa.types import ParseError
    with pytest.raises(ParseError):
        parse_nyaa_rss(TorrentSite.NYAA_SI, INVALID_XML)


def test_parse_rss_download_url():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, SOLO_LEVELING_RSS.encode())
    assert results[0].download_url == "https://nyaa.si/download/1234567.torrent"


def test_parse_rss_completed_is_none():
    results = parse_nyaa_rss(TorrentSite.NYAA_SI, SOLO_LEVELING_RSS.encode())
    assert results[0].completed is None
