"""Parse Nyaa HTML listing and detail pages into Torrent records."""

from bs4 import BeautifulSoup, Tag

from nyaa.types import (
    TorrentSite, Torrent, TorrentDetail, TorrentType, FileEntry, ParseError,
)
from nyaa.categories import category_for_site
from nyaa.parser._utils import last_segment, read_int


def _class_to_type(cls: str | None) -> TorrentType:
    if not cls:
        return TorrentType.NORMAL
    if "danger" in cls:
        return TorrentType.REMAKE
    if "success" in cls:
        return TorrentType.TRUSTED
    return TorrentType.NORMAL


def _is_comment_link(tag: Tag) -> bool:
    return str(tag.get("href", "")).endswith("#comments")


def _is_magnet_link(tag: Tag) -> bool:
    return str(tag.get("href", "")).startswith("magnet:")


def _row_to_torrent(site: TorrentSite, row: Tag) -> Torrent | None:
    tds = row.find_all("td", recursive = False)
    if len(tds) < 7:
        return None

    base = site.base_url

    cat_link = tds[0].find("a")
    if not cat_link:
        return None
    category = category_for_site(site, str(cat_link.get("href", "")))

    view_links = [a for a in tds[1].find_all("a") if not _is_comment_link(a)]
    if not view_links:
        return None
    name_link = view_links[0]
    view_href = str(name_link.get("href", ""))
    tor_name = str(name_link.get("title") or name_link.get_text(strip = True))
    view_id = last_segment(view_href)

    all_links = tds[2].find_all("a")
    dl_links = [a for a in all_links if not _is_magnet_link(a)]
    mag_links = [a for a in all_links if _is_magnet_link(a)]
    dl_href = str(dl_links[0].get("href", "")) if dl_links else ""
    mag_href = str(mag_links[0].get("href", "")) if mag_links else ""

    row_cls = row.get("class")
    tor_type = _class_to_type(" ".join(row_cls) if row_cls else None)

    return Torrent(
        id = view_id,
        category = category,
        url = f"{base}/view/{view_id}",
        name = tor_name,
        download_url = f"{base}{dl_href}",
        magnet = mag_href,
        size = tds[3].get_text(strip = True),
        date = tds[4].get_text(strip = True),
        seeders = read_int(tds[5].get_text(strip = True)),
        leechers = read_int(tds[6].get_text(strip = True)),
        completed = read_int(tds[7].get_text(strip = True)) if len(tds) >= 8 else None,
        type = tor_type,
    )


def parse_nyaa(site: TorrentSite, data: bytes, limit: int | None = None) -> list[Torrent]:
    soup = BeautifulSoup(data, "lxml")
    rows = []
    for tbody in soup.find_all("tbody"):
        rows.extend(tbody.find_all("tr", recursive = False))
    if limit is not None:
        rows = rows[:limit]
    return [t for row in rows if (t := _row_to_torrent(site, row)) is not None]


def _build_field_map(soup: BeautifulSoup) -> dict[str, str]:
    fields: dict[str, str] = {}
    for row in soup.find_all("div", class_ = "row"):
        labels = row.find_all("div", class_ = "col-md-1")
        values = row.find_all("div", class_ = "col-md-5")
        for label, value in zip(labels, values):
            key = label.get_text(strip = True).rstrip(":")
            fields[key] = value.get_text(strip = True)
    return fields


def parse_single(site: TorrentSite, data: bytes) -> TorrentDetail:
    soup = BeautifulSoup(data, "lxml")
    base = site.base_url

    title_tag = soup.find("h3", class_ = "panel-title")
    if not title_tag:
        raise ParseError("Failed to parse torrent detail page: missing title")
    title = title_tag.get_text(strip = True)

    fields = _build_field_map(soup)

    uploader = fields.get("Submitter", "")
    info_hash = fields.get("Info hash", "")
    website_raw = fields.get("Information", "").strip()

    footer_links = soup.find_all("a", class_ = "card-footer-item")
    dl_href = str(footer_links[0].get("href", "")) if footer_links else ""
    view_id = last_segment(dl_href) if dl_href else ""

    magnet_href = next(
        (str(a.get("href", "")) for a in soup.find_all("a")
         if str(a.get("href", "")).startswith("magnet:")),
        ""
    )

    file_list_div = soup.find("div", class_ = "torrent-file-list")
    files = []
    if file_list_div:
        for li in file_list_div.find_all("li"):
            name = li.get_text(strip = True)
            if name:
                files.append(FileEntry(name = name))

    desc_div = soup.find("div", id = "torrent-description")
    description = desc_div.get_text() if desc_div else ""

    panel = soup.find("div", class_ = "panel")
    panel_cls = " ".join(panel.get("class", [])) if panel else None
    tor_type = _class_to_type(panel_cls)

    return TorrentDetail(
        id = view_id,
        title = title,
        category = fields.get("Category", ""),
        url = f"{base}/view/{view_id}",
        download_url = f"{base}{dl_href}" if dl_href else "",
        magnet = magnet_href,
        size = fields.get("File size", ""),
        date = fields.get("Date", ""),
        seeders = read_int(fields.get("Seeders", "0")),
        leechers = read_int(fields.get("Leechers", "0")),
        completed = read_int(fields.get("Completed", "0")),
        type = tor_type,
        uploader = uploader,
        uploader_profile = f"{base}/user/{uploader}",
        website = website_raw or None,
        info_hash = info_hash,
        files = files,
        description = description,
    )
