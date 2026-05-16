"""AnimeSchedule API endpoint URL builders."""
BASE_URL = "https://animeschedule.net/api/v3"


def anime_list_url() -> str:
    return f"{BASE_URL}/anime"


def anime_slug_url(slug: str) -> str:
    return f"{BASE_URL}/anime/{slug}"
