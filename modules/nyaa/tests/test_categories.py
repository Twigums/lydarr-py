import pytest
from nyaa.types import TorrentSite
from nyaa.categories import (
    NYAA_CATEGORIES, SUKEBEI_CATEGORIES,
    _lookup_category, category_for_site,
)


def test_nyaa_categories_populated():
    assert ("1", "2") in NYAA_CATEGORIES
    assert NYAA_CATEGORIES[("1", "2")] == "Anime - English-translated"
    assert NYAA_CATEGORIES[("1", "4")] == "Anime - Raw"


def test_sukebei_categories_populated():
    assert ("1", "1") in SUKEBEI_CATEGORIES
    assert SUKEBEI_CATEGORIES[("1", "1")] == "Art - Anime"
    assert SUKEBEI_CATEGORIES[("2", "2")] == "Real Life - Videos"


def test_lookup_category_plain_code():
    result = _lookup_category(NYAA_CATEGORIES, "1_2")
    assert result == "Anime - English-translated"


def test_lookup_category_with_equals():
    result = _lookup_category(NYAA_CATEGORIES, "c=1_2")
    assert result == "Anime - English-translated"


def test_lookup_category_unknown():
    result = _lookup_category(NYAA_CATEGORIES, "9_9")
    assert result == "Unknown"


def test_lookup_category_malformed():
    result = _lookup_category(NYAA_CATEGORIES, "badcode")
    assert result == "Unknown"


def test_category_for_site_nyaa():
    result = category_for_site(TorrentSite.NYAA_SI, "1_2")
    assert result == "Anime - English-translated"


def test_category_for_site_sukebei():
    result = category_for_site(TorrentSite.SUKEBEI_NYAA_SI, "1_1")
    assert result == "Art - Anime"


def test_category_for_site_nyaa_land_uses_nyaa_categories():
    result = category_for_site(TorrentSite.NYAA_LAND, "1_2")
    assert result == "Anime - English-translated"


def test_category_for_site_unknown_code():
    result = category_for_site(TorrentSite.NYAA_SI, "9_9")
    assert result == "Unknown"


def test_all_nyaa_categories():
    expected_keys = [
        ("1", "1"), ("1", "2"), ("1", "3"), ("1", "4"),
        ("2", "1"), ("2", "2"),
        ("3", "1"), ("3", "2"), ("3", "3"),
        ("4", "1"), ("4", "2"), ("4", "3"), ("4", "4"),
        ("5", "1"), ("5", "2"),
        ("6", "1"), ("6", "2"),
    ]
    for key in expected_keys:
        assert key in NYAA_CATEGORIES


def test_all_sukebei_categories():
    expected_keys = [
        ("1", "1"), ("1", "2"), ("1", "3"), ("1", "4"), ("1", "5"),
        ("2", "1"), ("2", "2"),
    ]
    for key in expected_keys:
        assert key in SUKEBEI_CATEGORIES
