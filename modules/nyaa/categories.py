"""Category lookup tables for nyaa.si and sukebei.nyaa.si."""
from nyaa.types import TorrentSite

NYAA_CATEGORIES: dict[tuple[str, str], str] = {
    ("1", "1"): "Anime - Anime Music Video",
    ("1", "2"): "Anime - English-translated",
    ("1", "3"): "Anime - Non-English-translated",
    ("1", "4"): "Anime - Raw",
    ("2", "1"): "Audio - Lossless",
    ("2", "2"): "Audio - Lossy",
    ("3", "1"): "Literature - English-translated",
    ("3", "2"): "Literature - Non-English-translated",
    ("3", "3"): "Literature - Raw",
    ("4", "1"): "Live Action - English-translated",
    ("4", "2"): "Live Action - Idol/Promotional Video",
    ("4", "3"): "Live Action - Non-English-translated",
    ("4", "4"): "Live Action - Raw",
    ("5", "1"): "Pictures - Graphics",
    ("5", "2"): "Pictures - Photos",
    ("6", "1"): "Software - Applications",
    ("6", "2"): "Software - Games",
}

SUKEBEI_CATEGORIES: dict[tuple[str, str], str] = {
    ("1", "1"): "Art - Anime",
    ("1", "2"): "Art - Doujinshi",
    ("1", "3"): "Art - Games",
    ("1", "4"): "Art - Manga",
    ("1", "5"): "Art - Pictures",
    ("2", "1"): "Real Life - Photobooks & Pictures",
    ("2", "2"): "Real Life - Videos",
}


def _lookup_category(categories: dict[tuple[str, str], str], raw: str) -> str:
    code = raw.split("=")[-1] if "=" in raw else raw
    parts = code.split("_")
    if len(parts) == 2:
        return categories.get((parts[0], parts[1]), "Unknown")
    return "Unknown"


def category_for_site(site: TorrentSite, raw: str) -> str:
    cats = SUKEBEI_CATEGORIES if site == TorrentSite.SUKEBEI_NYAA_SI else NYAA_CATEGORIES
    return _lookup_category(cats, raw)
