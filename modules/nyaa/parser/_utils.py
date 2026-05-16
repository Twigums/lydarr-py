"""Shared helpers for the nyaa parser sub-package."""


def last_segment(text: str) -> str:
    return text.rstrip("/").rsplit("/", 1)[-1]


def read_int(text: str) -> int:
    try:
        return int(text.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return 0
