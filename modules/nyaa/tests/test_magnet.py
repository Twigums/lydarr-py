from urllib.parse import unquote
from nyaa.magnet import magnet_builder, MAGNET_TRACKERS


INFO_HASH = "0047E2A3DEADBEEF0047E2A3DEADBEEF0047E2A3"
TITLE = "[SubsPlease] Solo Leveling - 25 (1080p) [0047E2A3].mkv"


def test_magnet_starts_with_correct_prefix():
    result = magnet_builder(INFO_HASH, TITLE)
    assert result.startswith(f"magnet:?xt=urn:btih:{INFO_HASH}")


def test_magnet_contains_encoded_title():
    result = magnet_builder(INFO_HASH, TITLE)
    assert "&dn=" in result
    dn_part = result.split("&dn=")[1].split("&")[0]
    assert unquote(dn_part) == TITLE


def test_magnet_contains_all_trackers():
    result = magnet_builder(INFO_HASH, TITLE)
    for tracker in MAGNET_TRACKERS:
        assert tracker in unquote(result)


def test_magnet_tracker_count():
    result = magnet_builder(INFO_HASH, TITLE)
    tr_count = result.count("&tr=")
    assert tr_count == len(MAGNET_TRACKERS)


def test_magnet_simple_title():
    result = magnet_builder("AABBCCDD", "Simple Title")
    assert "magnet:?xt=urn:btih:AABBCCDD" in result
    assert "Simple%20Title" in result or "Simple+Title" in result or "dn=Simple" in result


def test_magnet_special_chars_encoded():
    result = magnet_builder("HASH123", "[Group] Show - 01 (720p).mkv")
    assert "magnet:?xt=urn:btih:HASH123" in result
    assert "&dn=" in result


def test_magnet_trackers_list():
    assert len(MAGNET_TRACKERS) >= 5
    assert any("nyaa" in t for t in MAGNET_TRACKERS)
    assert any("opentrackr" in t for t in MAGNET_TRACKERS)
