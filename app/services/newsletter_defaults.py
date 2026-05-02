"""Newsletter defaults and helper utilities."""

from typing import List

DEFAULT_NEWSLETTER_THEMES = [
    "videogames",
    "tecnologia",
    "esportes",
]
MAX_NEWSLETTER_THEMES = 5


def normalize_themes(themes: List[str]) -> List[str]:
    """Normalize, deduplicate and validate theme list."""
    cleaned: List[str] = []
    for raw_theme in themes:
        theme = raw_theme.strip()
        if not theme:
            continue
        if theme not in cleaned:
            cleaned.append(theme)

    if not cleaned:
        raise ValueError("At least one theme is required.")
    if len(cleaned) > MAX_NEWSLETTER_THEMES:
        raise ValueError(
            f"You can provide at most {MAX_NEWSLETTER_THEMES} themes per newsletter."
        )

    return cleaned
