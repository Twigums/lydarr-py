import pytest
from unittest.mock import AsyncMock, patch
from anilist.types import AnilistMedia, MediaType, MediaStatus, AnilistError
from anilist.search import _parse, search, find_by_title


SOLO_LEVELING_MEDIA = {
    "id": 153406,
    "type": "ANIME",
    "title": {
        "romaji": "Solo Leveling Season 2 -Arise from the Shadow-",
        "english": "Solo Leveling Season 2",
    },
    "status": "FINISHED",
    "episodes": 25,
    "chapters": None,
    "nextAiringEpisode": None,
}

ONGOING_MEDIA = {
    "id": 999,
    "type": "ANIME",
    "title": {"romaji": "New Anime", "english": None},
    "status": "RELEASING",
    "episodes": None,
    "chapters": None,
    "nextAiringEpisode": {"airingAt": 1700000000, "episode": 5},
}

MANGA_MEDIA = {
    "id": 42,
    "type": "MANGA",
    "title": {"romaji": "Some Manga", "english": "Some Manga EN"},
    "status": "RELEASING",
    "episodes": None,
    "chapters": 120,
    "nextAiringEpisode": None,
}


def test_parse_finished_anime():
    m = _parse(SOLO_LEVELING_MEDIA)
    assert m.id == 153406
    assert m.title_romaji == "Solo Leveling Season 2 -Arise from the Shadow-"
    assert m.title_english == "Solo Leveling Season 2"
    assert m.media_type == MediaType.ANIME
    assert m.status == MediaStatus.FINISHED
    assert m.episodes == 25
    assert m.chapters is None
    assert m.next_airing_at is None
    assert m.next_airing_episode is None


def test_parse_ongoing_anime_with_next_episode():
    m = _parse(ONGOING_MEDIA)
    assert m.status == MediaStatus.RELEASING
    assert m.next_airing_at == 1700000000
    assert m.next_airing_episode == 5


def test_parse_manga():
    m = _parse(MANGA_MEDIA)
    assert m.media_type == MediaType.MANGA
    assert m.chapters == 120
    assert m.episodes is None


def test_parse_unknown_status():
    d = {**SOLO_LEVELING_MEDIA, "status": "MYSTERY_STATUS"}
    m = _parse(d)
    assert m.status == MediaStatus.UNKNOWN


def test_display_title_english_preferred():
    m = _parse(SOLO_LEVELING_MEDIA)
    assert m.display_title() == "Solo Leveling Season 2"


def test_display_title_romaji_fallback():
    d = {**SOLO_LEVELING_MEDIA, "title": {"romaji": "Solo Leveling S2", "english": None}}
    m = _parse(d)
    assert m.display_title() == "Solo Leveling S2"


def test_display_title_id_fallback():
    d = {**SOLO_LEVELING_MEDIA, "title": {"romaji": None, "english": None}}
    m = _parse(d)
    assert m.display_title() == f"ID:{SOLO_LEVELING_MEDIA['id']}"


@pytest.mark.asyncio
async def test_search_returns_list():
    graphql_response = {
        "Page": {
            "media": [SOLO_LEVELING_MEDIA, ONGOING_MEDIA],
        }
    }
    with patch("anilist.search.graphql", new_callable = AsyncMock, return_value = graphql_response):
        results = await search("Solo Leveling", MediaType.ANIME)

    assert len(results) == 2
    assert results[0].id == 153406


@pytest.mark.asyncio
async def test_search_empty():
    graphql_response = {"Page": {"media": []}}
    with patch("anilist.search.graphql", new_callable = AsyncMock, return_value = graphql_response):
        results = await search("Nonexistent", MediaType.ANIME)

    assert results == []


@pytest.mark.asyncio
async def test_find_by_title_exact_english_match():
    graphql_response = {"Page": {"media": [SOLO_LEVELING_MEDIA]}}
    with patch("anilist.search.graphql", new_callable = AsyncMock, return_value = graphql_response):
        result = await find_by_title("Solo Leveling Season 2", MediaType.ANIME)

    assert result is not None
    assert result.id == 153406


@pytest.mark.asyncio
async def test_find_by_title_exact_romaji_match():
    graphql_response = {"Page": {"media": [SOLO_LEVELING_MEDIA]}}
    with patch("anilist.search.graphql", new_callable = AsyncMock, return_value = graphql_response):
        result = await find_by_title(
            "Solo Leveling Season 2 -Arise from the Shadow-", MediaType.ANIME
        )

    assert result is not None


@pytest.mark.asyncio
async def test_find_by_title_partial_match():
    graphql_response = {"Page": {"media": [SOLO_LEVELING_MEDIA]}}
    with patch("anilist.search.graphql", new_callable = AsyncMock, return_value = graphql_response):
        result = await find_by_title("Solo Leveling", MediaType.ANIME)

    assert result is not None


@pytest.mark.asyncio
async def test_find_by_title_no_match_returns_first():
    graphql_response = {"Page": {"media": [SOLO_LEVELING_MEDIA]}}
    with patch("anilist.search.graphql", new_callable = AsyncMock, return_value = graphql_response):
        result = await find_by_title("Completely Different", MediaType.ANIME)

    assert result is not None
    assert result.id == 153406


@pytest.mark.asyncio
async def test_find_by_title_empty_results():
    graphql_response = {"Page": {"media": []}}
    with patch("anilist.search.graphql", new_callable = AsyncMock, return_value = graphql_response):
        result = await find_by_title("Nonexistent", MediaType.ANIME)

    assert result is None


@pytest.mark.asyncio
async def test_find_by_title_colon_strip_fallback():
    """Full colon-subtitle query returns nothing; retry with pre-colon portion succeeds."""
    empty = {"Page": {"media": []}}
    hit = {"Page": {"media": [SOLO_LEVELING_MEDIA]}}
    call_count = 0

    async def mock_graphql(query, variables):
        nonlocal call_count
        call_count += 1
        return empty if call_count == 1 else hit

    with patch("anilist.search.graphql", side_effect = mock_graphql):
        result = await find_by_title(
            "Solo Leveling Season 2: Arise from the Shadow", MediaType.ANIME
        )

    assert call_count == 2
    assert result is not None
    assert result.id == 153406


@pytest.mark.asyncio
async def test_find_by_title_no_colon_no_retry():
    """Titles without a colon do not trigger a second query."""
    empty = {"Page": {"media": []}}
    call_count = 0

    async def mock_graphql(query, variables):
        nonlocal call_count
        call_count += 1
        return empty

    with patch("anilist.search.graphql", side_effect = mock_graphql):
        result = await find_by_title("Nonexistent Title", MediaType.ANIME)

    assert call_count == 1
    assert result is None


@pytest.mark.asyncio
async def test_graphql_http_error():
    with patch("anilist.http.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value = mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value = False)
        mock_resp = AsyncMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server Error"
        mock_client.post = AsyncMock(return_value = mock_resp)

        from anilist.http import graphql as graphql_fn
        with pytest.raises(AnilistError, match = "HTTP 500"):
            await graphql_fn("query {}", {})


@pytest.mark.asyncio
async def test_graphql_errors_in_response():
    with patch("anilist.http.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value = mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value = False)
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value = {"errors": [{"message": "Not found"}], "data": None})
        mock_client.post = AsyncMock(return_value = mock_resp)

        from anilist.http import graphql as graphql_fn
        with pytest.raises(AnilistError, match = "Not found"):
            await graphql_fn("query {}", {})


from unittest.mock import MagicMock
