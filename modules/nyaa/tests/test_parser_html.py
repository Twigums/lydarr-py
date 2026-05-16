import pytest
from nyaa.types import TorrentSite, TorrentType
from nyaa.parser.html import parse_nyaa, parse_single, _class_to_type
from nyaa.parser._utils import read_int as _read_int


def _make_listing_html(rows: list[dict]) -> bytes:
    row_html = ""
    for r in rows:
        css_class = r.get("class", "")
        class_attr = f' class="{css_class}"' if css_class else ""
        row_html += f"""
        <tr{class_attr}>
          <td><a href="/c/{r.get('cat', '1_2')}"><img/></a></td>
          <td>
            <a href="/view/{r['id']}" title="{r['name']}">{r['name']}</a>
          </td>
          <td>
            <a href="/download/{r['id']}.torrent">DL</a>
            <a href="{r.get('magnet', 'magnet:?xt=urn:btih:AABB')}">Magnet</a>
          </td>
          <td>{r.get('size', '1.0 GiB')}</td>
          <td>{r.get('date', '2025-03-29')}</td>
          <td>{r.get('seeders', '100')}</td>
          <td>{r.get('leechers', '5')}</td>
          <td>{r.get('completed', '500')}</td>
        </tr>
        """
    return f"""
    <html><body>
    <table class="torrent-list">
      <tbody>
        {row_html}
      </tbody>
    </table>
    </body></html>
    """.encode()


SOLO_LEVELING_ROW = {
    "id": "1234567",
    "name": "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv",
    "cat": "1_2",
    "magnet": "magnet:?xt=urn:btih:0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3",
    "size": "1.37 GiB",
    "date": "2025-03-29 12:00",
    "seeders": "847",
    "leechers": "23",
    "completed": "5000",
    "class": "success",
}


def test_parse_listing_returns_torrents():
    html = _make_listing_html([SOLO_LEVELING_ROW])
    results = parse_nyaa(TorrentSite.NYAA_SI, html)
    assert len(results) == 1


def test_parse_listing_torrent_fields():
    html = _make_listing_html([SOLO_LEVELING_ROW])
    t = parse_nyaa(TorrentSite.NYAA_SI, html)[0]
    assert t.id == "1234567"
    assert t.name == "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"
    assert t.seeders == 847
    assert t.leechers == 23
    assert t.size == "1.37 GiB"
    assert t.type == TorrentType.TRUSTED
    assert t.url == "https://nyaa.si/view/1234567"


def test_parse_listing_magnet():
    html = _make_listing_html([SOLO_LEVELING_ROW])
    t = parse_nyaa(TorrentSite.NYAA_SI, html)[0]
    assert t.magnet.startswith("magnet:")


def test_parse_listing_download_url():
    html = _make_listing_html([SOLO_LEVELING_ROW])
    t = parse_nyaa(TorrentSite.NYAA_SI, html)[0]
    assert t.download_url == "https://nyaa.si/download/1234567.torrent"


def test_parse_listing_remake_type():
    row = dict(SOLO_LEVELING_ROW)
    row["class"] = "danger"
    html = _make_listing_html([row])
    t = parse_nyaa(TorrentSite.NYAA_SI, html)[0]
    assert t.type == TorrentType.REMAKE


def test_parse_listing_normal_type():
    row = dict(SOLO_LEVELING_ROW)
    row["class"] = ""
    html = _make_listing_html([row])
    t = parse_nyaa(TorrentSite.NYAA_SI, html)[0]
    assert t.type == TorrentType.NORMAL


def test_parse_listing_limit():
    rows = [
        dict(SOLO_LEVELING_ROW, id = "111", name = "First"),
        dict(SOLO_LEVELING_ROW, id = "222", name = "Second"),
    ]
    html = _make_listing_html(rows)
    results = parse_nyaa(TorrentSite.NYAA_SI, html, limit = 1)
    assert len(results) == 1
    assert results[0].id == "111"


def test_parse_listing_empty_html():
    html = b"<html><body></body></html>"
    results = parse_nyaa(TorrentSite.NYAA_SI, html)
    assert results == []


def test_parse_listing_multiple_rows():
    rows = [
        dict(SOLO_LEVELING_ROW, id = "111"),
        dict(SOLO_LEVELING_ROW, id = "222"),
        dict(SOLO_LEVELING_ROW, id = "333"),
    ]
    html = _make_listing_html(rows)
    results = parse_nyaa(TorrentSite.NYAA_SI, html)
    assert len(results) == 3


def test_class_to_type_trusted():
    assert _class_to_type("success") == TorrentType.TRUSTED
    assert _class_to_type("row success") == TorrentType.TRUSTED


def test_class_to_type_remake():
    assert _class_to_type("danger") == TorrentType.REMAKE
    assert _class_to_type("row danger") == TorrentType.REMAKE


def test_class_to_type_normal():
    assert _class_to_type(None) == TorrentType.NORMAL
    assert _class_to_type("") == TorrentType.NORMAL
    assert _class_to_type("default") == TorrentType.NORMAL


def test_read_int_valid():
    assert _read_int("847") == 847
    assert _read_int("  100  ") == 100
    assert _read_int("1,234") == 1234


def test_read_int_invalid():
    assert _read_int("n/a") == 0
    assert _read_int("") == 0


DETAIL_HTML = b"""
<html><body>
  <div class="panel panel-success">
    <div class="panel-heading">
      <h3 class="panel-title">[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv</h3>
    </div>
    <div class="panel-body">
      <div class="row">
        <div class="col-md-1">Category:</div>
        <div class="col-md-5">Anime - English-translated</div>
        <div class="col-md-1">Date:</div>
        <div class="col-md-5">2025-03-29 12:00</div>
      </div>
      <div class="row">
        <div class="col-md-1">Submitter:</div>
        <div class="col-md-5">SubsPlease</div>
        <div class="col-md-1">Seeders:</div>
        <div class="col-md-5">847</div>
      </div>
      <div class="row">
        <div class="col-md-1">Info hash:</div>
        <div class="col-md-5">0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3</div>
        <div class="col-md-1">Leechers:</div>
        <div class="col-md-5">23</div>
      </div>
      <div class="row">
        <div class="col-md-1">File size:</div>
        <div class="col-md-5">1.37 GiB</div>
        <div class="col-md-1">Completed:</div>
        <div class="col-md-5">5000</div>
      </div>
      <div class="row">
        <div class="col-md-1">Information:</div>
        <div class="col-md-5">https://subsplease.org</div>
      </div>
    </div>
  </div>
  <div class="card">
    <a class="card-footer-item" href="/download/1234567.torrent">Download</a>
    <a href="magnet:?xt=urn:btih:0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3&dn=test">Magnet</a>
  </div>
  <div class="torrent-file-list">
    <ul><li>[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv</li></ul>
  </div>
  <div id="torrent-description">Some description text.</div>
</body></html>
"""


def test_parse_single_title():
    td = parse_single(TorrentSite.NYAA_SI, DETAIL_HTML)
    assert td.title == "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"


def test_parse_single_fields():
    td = parse_single(TorrentSite.NYAA_SI, DETAIL_HTML)
    assert td.uploader == "SubsPlease"
    assert td.info_hash == "0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3"
    assert td.seeders == 847
    assert td.leechers == 23
    assert td.size == "1.37 GiB"
    assert td.completed == 5000
    assert td.type == TorrentType.TRUSTED
    assert td.website == "https://subsplease.org"


def test_parse_single_files():
    td = parse_single(TorrentSite.NYAA_SI, DETAIL_HTML)
    assert len(td.files) == 1
    assert td.files[0].name == "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"


def test_parse_single_description():
    td = parse_single(TorrentSite.NYAA_SI, DETAIL_HTML)
    assert "Some description text." in td.description


def test_parse_single_missing_title_raises():
    from nyaa.types import ParseError
    html = b"<html><body><p>No title here</p></body></html>"
    with pytest.raises(ParseError, match = "missing title"):
        parse_single(TorrentSite.NYAA_SI, html)


def test_parse_single_magnet():
    td = parse_single(TorrentSite.NYAA_SI, DETAIL_HTML)
    assert td.magnet.startswith("magnet:")
