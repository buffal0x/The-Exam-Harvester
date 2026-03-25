from __future__ import annotations

import re
from pathlib import Path

import yaml


COURSE_ID_PATTERN = re.compile(r"(\d{6,})")
COURSE_URL_PATTERN = re.compile(r"/studentcourses/(\d+)/exams/?$")


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_course_id(course_ref: str | None, site_config: dict) -> str:
    """
    Accepts:
    - None -> uses site.default_course_id
    - plain numeric course id, e.g. 3207192
    - full exams url, e.g. https://studier.nti.se/studentcourses/3207192/exams
    """
    if course_ref:
        course_ref = course_ref.strip()

        url_match = COURSE_URL_PATTERN.search(course_ref)
        if url_match:
            return url_match.group(1)

        id_match = COURSE_ID_PATTERN.fullmatch(course_ref)
        if id_match:
            return id_match.group(1)

        id_match = COURSE_ID_PATTERN.search(course_ref)
        if id_match:
            return id_match.group(1)

        raise ValueError(f"Could not resolve course id from input: {course_ref}")

    default_course_id = str(site_config["site"].get("default_course_id", "")).strip()
    if not default_course_id:
        raise ValueError("Missing site.default_course_id in config/site.yaml")

    return default_course_id


def build_course_context(course_ref: str | None = None) -> dict:
    site_config = load_yaml("config/site.yaml")

    site = site_config["site"]
    crawler = site_config["crawler"]
    storage = site_config["storage"]

    course_id = resolve_course_id(course_ref, site_config)
    base_url = site["base_url"].rstrip("/")
    start_url = f"{base_url}/studentcourses/{course_id}/exams"

    denied_global_patterns = list(crawler.get("denied_global_patterns", []))
    denied_course_tabs = list(crawler.get("denied_course_tabs", []))
    denied_url_patterns = denied_global_patterns + [
        f"/studentcourses/{course_id}/{tab}" for tab in denied_course_tabs
    ]

    base_dir = Path(storage["base_dir"]) / f"course_{course_id}"

    context = {
        "site_config": site_config,
        "course_id": course_id,
        "start_url": start_url,
        "allowed_domains": ["studier.nti.se"],
        "allowed_url_patterns": [
            f"/studentcourses/{course_id}/exams",
            "/exam/",
        ],
        "denied_url_patterns": denied_url_patterns,
        "storage": {
            "base_dir": str(base_dir),
            "raw_dir": str(base_dir / "raw"),
            "parsed_dir": str(base_dir / "parsed"),
            "manifest_dir": str(base_dir / "manifests"),
            "index_dir": str(base_dir / "index"),
            "ordered_dir": str(base_dir / "ordered"),
        },
    }

    return context