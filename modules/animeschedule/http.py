"""HTTP client for the AnimeSchedule API."""
import httpx

from animeschedule.types import HttpError, ParseError, AuthError


async def get_json_no_auth(url: str, params: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout = httpx.Timeout(10, read = 30)) as client:
            response = await client.get(url, params = params)
    except httpx.HTTPError as exc:
        raise HttpError(str(exc)) from exc

    if response.status_code in (401, 403):
        raise AuthError("Invalid/missing API key.")
    if not (200 <= response.status_code < 300):
        raise HttpError(f"HTTP {response.status_code}")

    try:
        return response.json()
    except Exception as exc:
        raise ParseError(str(exc)) from exc
