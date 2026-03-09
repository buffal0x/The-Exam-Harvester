from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    parsed = urlparse(url)

    path = parsed.path.rstrip("/")
    if not path:
        path = "/"

    normalized = parsed._replace(
        params="",
        query="",
        fragment="",
        path=path,
    )
    return urlunparse(normalized)


def is_allowed_url(
    url: str,
    allowed_domains: list[str],
    allowed_patterns: list[str],
    denied_patterns: list[str],
) -> bool:
    url = normalize_url(url)
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    netloc = parsed.netloc.lower()
    if allowed_domains and not any(domain.lower() in netloc for domain in allowed_domains):
        return False

    path = parsed.path or "/"

    if denied_patterns and any(pattern in path for pattern in denied_patterns):
        return False

    if allowed_patterns and not any(pattern in path for pattern in allowed_patterns):
        return False

    return True


def contains_blacklisted_text(text: str | None, blacklist: list[str]) -> bool:
    if not text:
        return False

    normalized = text.strip().lower()
    for item in blacklist:
        if item.strip().lower() in normalized:
            return True

    return False


def contains_allowed_text(text: str | None, allowlist: list[str]) -> bool:
    if not text:
        return False

    normalized = text.strip().lower()
    for item in allowlist:
        if item.strip().lower() in normalized:
            return True

    return False