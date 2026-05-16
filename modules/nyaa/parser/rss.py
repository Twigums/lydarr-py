"""Parse Nyaa RSS feeds into Torrent records."""

import defusedxml.ElementTree as ET
from xml.etree.ElementTree import ParseError as XMLParseError

from nyaa.types import TorrentSite, Torrent, TorrentType, ParseError
from nyaa.categories import category_for_site
from nyaa.magnet import magnet_builder
from nyaa.parser._utils import last_segment, read_int

_NYAA_NS = "https://nyaa.si/xmlns/nyaa"


def _ns(tag: str) -> str:
    return f"{{{_NYAA_NS}}}{tag}"


def _text(elem, tag: str, default: str = "") -> str:
    child = elem.find(tag)
    return (child.text or default) if child is not None else default


def _nyaa_text(elem, tag: str, default: str = "") -> str:
    child = elem.find(_ns(tag))
    return (child.text or default) if child is not None else default


def _torrent_type(remake: str, trusted: str) -> TorrentType:
    if remake == "Yes":
        return TorrentType.REMAKE
    if trusted == "Yes":
        return TorrentType.TRUSTED
    return TorrentType.NORMAL


def _item_to_torrent(site: TorrentSite, item) -> Torrent | None:
    title = _text(item, "title")
    guid = _text(item, "guid")
    if not title or not guid:
        return None

    link = _text(item, "link")
    info_hash = _nyaa_text(item, "infoHash")
    cat_name = _nyaa_text(item, "category")
    cat_id = _nyaa_text(item, "categoryId")
    seeders = read_int(_nyaa_text(item, "seeders", "0"))
    leechers = read_int(_nyaa_text(item, "leechers", "0"))
    trusted = _nyaa_text(item, "trusted", "No")
    remake = _nyaa_text(item, "remake", "No")

    category = cat_name if cat_name else category_for_site(site, cat_id)
    magnet = magnet_builder(info_hash, title) if info_hash else ""

    return Torrent(
        id = last_segment(guid),
        category = category,
        url = guid,
        name = title,
        download_url = link,
        magnet = magnet,
        size = _nyaa_text(item, "size"),
        date = _text(item, "pubDate"),
        seeders = seeders,
        leechers = leechers,
        completed = None,
        type = _torrent_type(remake, trusted),
    )


def parse_nyaa_rss(site: TorrentSite, data: bytes, limit: int | None = None) -> list[Torrent]:
    try:
        root = ET.fromstring(data)
    except XMLParseError as exc:
        raise ParseError(str(exc)) from exc

    items = root.findall(".//item")
    if limit is not None:
        items = items[:limit]

    return [t for item in items if (t := _item_to_torrent(site, item)) is not None]
