"""HTTP client for the AniList GraphQL API."""
import httpx

from anilist.types import AnilistError

_URL = "https://graphql.anilist.co"


async def graphql(query: str, variables: dict) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(_URL, json = {"query": query, "variables": variables}, timeout = 15)
    if r.status_code != 200:
        raise AnilistError(f"HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    if "errors" in data:
        raise AnilistError(data["errors"][0].get("message", str(data["errors"])))
    return data["data"]
