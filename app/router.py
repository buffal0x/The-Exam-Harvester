from __future__ import annotations

from typing import Any
from bs4 import BeautifulSoup


def detect_page_type(html: str, extractor_config: dict[str, Any]) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    page_types = extractor_config.get("page_types", {})

    for page_type, config in page_types.items():
        match_selectors = config.get("match", [])
        for selector in match_selectors:
            try:
                if soup.select_one(selector):
                    return page_type
            except Exception:
                continue

    return None