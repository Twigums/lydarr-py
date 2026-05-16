"""Torrent search and add routes."""
from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator

from nyaa.search import search as nyaa_search
from nyaa.types import SearchParams, SortField, SortOrder, TorrentSite
from lydarr.nyaa_search import prefer_hevc
from lydarr.torrent_client import add_magnet

router = APIRouter(prefix = "/api")

_SITE_MAP: dict[str, TorrentSite] = {
    "nyaa_si": TorrentSite.NYAA_SI,
    "sukebei": TorrentSite.SUKEBEI_NYAA_SI,
    "nyaa_land": TorrentSite.NYAA_LAND,
}


@router.get("/torrents/search")
async def search_torrents(
    q: str,
    ep: int | None = None,
    site: str = "nyaa_si",
    hevc_only: bool = False,
):
    query = f"{q} - {ep:02d}" if ep is not None else q
    torrent_site = _SITE_MAP.get(site, TorrentSite.NYAA_SI)
    params = SearchParams(
        keyword = query,
        filters = 0,
        category = 1,
        subcategory = 2,
        sort = SortField.SEEDERS,
        order = SortOrder.DESC,
    )
    results = await nyaa_search(torrent_site, params)
    if hevc_only:
        results = prefer_hevc(results)
    return [
        {
            "id": t.id,
            "name": t.name,
            "size": t.size,
            "date": t.date,
            "seeders": t.seeders,
            "leechers": t.leechers,
            "type": t.type.value,
            "magnet": t.magnet,
            "download_url": t.download_url,
        }
        for t in results
    ]


class AddMagnetBody(BaseModel):
    magnet: str

    @field_validator("magnet")
    @classmethod
    def must_be_magnet(cls, v: str) -> str:
        if not v.startswith("magnet:?xt=urn:btih:"):
            raise ValueError("magnet must start with magnet:?xt=urn:btih:")
        return v


@router.post("/torrents/add")
async def add_torrent(body: AddMagnetBody, request: Request):
    cfg = request.app.state.cfg
    ok = await add_magnet(
        cfg.transmission_url, cfg.transmission_user,
        cfg.transmission_pass, body.magnet, cfg.default_dir,
    )
    if ok:
        return {"ok": True}
    return {"ok": False, "error": "Transmission rejected the magnet"}
