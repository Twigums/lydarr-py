"""Anime and manga watchlist management routes."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from anilist.search import search as anilist_search, find_by_title
from anilist.types import MediaType
from lydarr.file_manager import MediaEntry

router = APIRouter(prefix = "/api")


@router.get("/anime/search")
async def search(q: str, type: str = "anime"):
    media_type = MediaType.MANGA if type == "manga" else MediaType.ANIME
    results = await anilist_search(q, media_type)
    return [
        {
            "id": m.id,
            "title": m.display_title(),
            "type": m.media_type.value.lower(),
            "status": m.status.value,
            "episodes": m.episodes,
            "chapters": m.chapters,
            "next_airing_at": m.next_airing_at,
            "next_airing_episode": m.next_airing_episode,
            "cover_image": m.cover_image,
        }
        for m in results
    ]


@router.get("/anime/list")
async def list_media(request: Request):
    return [
        {
            "title": e.title,
            "type": e.media_type,
            "submitters": e.submitters,
            "last_chapter": e.last_chapter,
            "search_name": e.search_name,
            "deprecated": e.deprecated,
        }
        for e in request.app.state.anime_state.entries()
    ]


class AddBody(BaseModel):
    title: str
    type: Literal["anime", "manga"] = "anime"
    submitters: list[str] = []


class TitleBody(BaseModel):
    title: str


class SubmittersBody(BaseModel):
    title: str
    submitters: list[str]
    search_name: str = ""


@router.post("/anime/add")
async def add_media(body: AddBody, request: Request):
    cfg = request.app.state.cfg
    state = request.app.state.anime_state
    if body.title in state.titles():
        return {"added": False, "reason": "already tracked"}
    await state.add(cfg.anime_file, MediaEntry(
        title = body.title,
        media_type = body.type,
        submitters = body.submitters,
    ))
    return {"added": True}


@router.post("/anime/remove")
async def remove_media(body: TitleBody, request: Request):
    cfg = request.app.state.cfg
    state = request.app.state.anime_state
    if body.title not in state.titles():
        return {"removed": False, "reason": "not tracked"}
    await state.remove(cfg.anime_file, body.title)
    return {"removed": True}


@router.post("/anime/deprecate")
async def deprecate_media(body: TitleBody, request: Request):
    cfg = request.app.state.cfg
    state = request.app.state.anime_state
    if body.title not in state.titles():
        return {"ok": False, "reason": "not tracked"}
    await state.set_deprecated(cfg.anime_file, body.title, True)
    return {"ok": True}


@router.post("/anime/reactivate")
async def reactivate_media(body: TitleBody, request: Request):
    cfg = request.app.state.cfg
    state = request.app.state.anime_state
    if body.title not in state.titles():
        return {"ok": False, "reason": "not tracked"}
    await state.set_deprecated(cfg.anime_file, body.title, False)
    return {"ok": True}


@router.post("/anime/submitters")
async def update_submitters(body: SubmittersBody, request: Request):
    cfg = request.app.state.cfg
    state = request.app.state.anime_state
    if body.title not in state.titles():
        return {"ok": False, "reason": "not tracked"}
    await state.update_entry(cfg.anime_file, body.title, body.submitters, body.search_name)
    return {"ok": True}


@router.get("/anime/status")
async def get_status(title: str, type: str = "anime"):
    media_type = MediaType.MANGA if type == "manga" else MediaType.ANIME
    info = await find_by_title(title, media_type)
    if info is None:
        return {"status": None, "next_airing_at": None, "next_airing_episode": None}
    return {
        "status": info.status.value,
        "next_airing_at": info.next_airing_at,
        "next_airing_episode": info.next_airing_episode,
    }
