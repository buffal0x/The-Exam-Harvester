from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.storage import ensure_dir


MANIFEST_PATH = Path("data/manifests/manifest.json")
INDEX_DIR = Path("data/index")
ORDERED_DIR = Path("data/ordered")

OUTPUT_JSON = INDEX_DIR / "course_index.json"
OUTPUT_MD = INDEX_DIR / "course_index.md"


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def normalize_title(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def slugify_title(text: str | None, max_length: int = 80) -> str:
    text = normalize_title(text).lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:max_length] if text else "untitled"


def extract_exam_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"/exam/(\d+)", url)
    return match.group(1) if match else None


def extract_course_listing_entry(manifest: list[dict]) -> dict | None:
    for item in manifest:
        url = item.get("url", "")
        if "/studentcourses/" in url and url.endswith("/exams"):
            return item
    return None


def determine_status(metadata: dict) -> str:
    if metadata.get("blacklisted") is True:
        return "blacklisted"

    page_type = metadata.get("page_type")
    fields = metadata.get("fields", {})

    if page_type == "exam_preview":
        return "not_started"

    if page_type == "exam_active":
        question_blocks = fields.get("question_blocks") or []

        if question_blocks:
            for block in question_blocks:
                answer_text = (block.get("answer_text") or "").strip()
                answer_markdown = (block.get("answer_markdown") or "").strip()
                if answer_text or answer_markdown:
                    return "answered"
            return "started_no_answer"

        for key in ("answer_text", "answer_markdown", "student_answer", "student_answer_markdown"):
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                return "answered"

        return "started_no_answer"

    if page_type == "unknown":
        return "missing"

    return "started_no_answer"


def copy_if_exists(src: str | None, dst: Path) -> bool:
    if not src:
        return False

    src_path = Path(src)
    if not src_path.exists():
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dst)
    return True


def build_ordered_view(entries: list[dict]) -> None:
    if ORDERED_DIR.exists():
        shutil.rmtree(ORDERED_DIR)

    ORDERED_DIR.mkdir(parents=True, exist_ok=True)

    summary_lines: list[str] = []
    summary_lines.append("# Ordered view")
    summary_lines.append("")

    for entry in entries:
        order_str = str(entry["order"]).zfill(3)
        title_slug = slugify_title(entry["title"])
        folder_name = f"{order_str}-{title_slug}"
        folder_path = ORDERED_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        copied_content = copy_if_exists(entry.get("content_path"), folder_path / "content.md")
        copied_metadata = copy_if_exists(entry.get("metadata_path"), folder_path / "metadata.json")
        copied_raw = copy_if_exists(entry.get("raw_html_path"), folder_path / "raw.html")
        copied_screenshot = copy_if_exists(entry.get("screenshot_path"), folder_path / "screenshot.png")

        info = {
            "order": entry["order"],
            "exam_id": entry["exam_id"],
            "title": entry["title"],
            "listing_text": entry["listing_text"],
            "url": entry["url"],
            "page_type": entry["page_type"],
            "status": entry["status"],
            "blacklisted": entry["blacklisted"],
            "hash_id": entry["hash_id"],
            "copied": {
                "content_md": copied_content,
                "metadata_json": copied_metadata,
                "raw_html": copied_raw,
                "screenshot_png": copied_screenshot,
            },
            "source_paths": {
                "content_path": entry.get("content_path"),
                "metadata_path": entry.get("metadata_path"),
                "raw_html_path": entry.get("raw_html_path"),
                "screenshot_path": entry.get("screenshot_path"),
            },
        }
        write_json(folder_path / "info.json", info)

        summary_lines.append(f"- {order_str} | {entry['status']} | {entry['title']}")

    write_text(ORDERED_DIR / "README.md", "\n".join(summary_lines) + "\n")


def build_index() -> None:
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"Missing manifest file: {MANIFEST_PATH}")

    ensure_dir(INDEX_DIR)

    manifest = load_json(MANIFEST_PATH)
    listing_entry = extract_course_listing_entry(manifest)
    if not listing_entry:
        raise RuntimeError("Could not find exams listing page in manifest.")

    listing_metadata_path = Path(listing_entry["metadata"])
    if not listing_metadata_path.exists():
        raise RuntimeError(f"Missing listing metadata file: {listing_metadata_path}")

    listing_metadata = load_json(listing_metadata_path)
    listing_fields = listing_metadata.get("fields", {})
    exam_links = listing_fields.get("exam_links", [])

    scraped_by_exam_id: dict[str, dict] = {}

    for item in manifest:
        url = item.get("url", "")
        exam_id = extract_exam_id(url)
        if not exam_id:
            continue

        metadata_path = Path(item["metadata"])
        if not metadata_path.exists():
            continue

        metadata = load_json(metadata_path)
        page_type = metadata.get("page_type")

        current = scraped_by_exam_id.get(exam_id)

        priority = {"exam_active": 3, "exam_preview": 2, "unknown": 1}
        new_priority = priority.get(page_type, 0)
        old_priority = priority.get(current["metadata"].get("page_type"), 0) if current else -1

        if current is None or new_priority >= old_priority:
            scraped_by_exam_id[exam_id] = {
                "manifest": item,
                "metadata": metadata,
            }

    seen_exam_ids: set[str] = set()
    ordered_entries: list[dict] = []

    for link in exam_links:
        href = link.get("href", "")
        text = normalize_title(link.get("text", ""))
        exam_id = extract_exam_id(href)

        if not exam_id:
            continue

        if exam_id in seen_exam_ids:
            continue

        seen_exam_ids.add(exam_id)

        scraped = scraped_by_exam_id.get(exam_id)
        if scraped:
            manifest_item = scraped["manifest"]
            metadata = scraped["metadata"]
            status = determine_status(metadata)

            ordered_entries.append(
                {
                    "order": len(ordered_entries) + 1,
                    "exam_id": exam_id,
                    "title": normalize_title(metadata.get("fields", {}).get("title") or text),
                    "listing_text": text,
                    "url": manifest_item.get("url"),
                    "page_type": metadata.get("page_type"),
                    "status": status,
                    "blacklisted": bool(metadata.get("blacklisted")),
                    "hash_id": manifest_item.get("id"),
                    "content_path": manifest_item.get("markdown"),
                    "metadata_path": manifest_item.get("metadata"),
                    "raw_html_path": manifest_item.get("raw_html"),
                    "screenshot_path": manifest_item.get("screenshot"),
                }
            )
        else:
            ordered_entries.append(
                {
                    "order": len(ordered_entries) + 1,
                    "exam_id": exam_id,
                    "title": text,
                    "listing_text": text,
                    "url": href,
                    "page_type": "missing",
                    "status": "missing",
                    "blacklisted": False,
                    "hash_id": None,
                    "content_path": None,
                    "metadata_path": None,
                    "raw_html_path": None,
                    "screenshot_path": None,
                }
            )

    summary = {
        "total": len(ordered_entries),
        "answered": sum(1 for x in ordered_entries if x["status"] == "answered"),
        "started_no_answer": sum(1 for x in ordered_entries if x["status"] == "started_no_answer"),
        "not_started": sum(1 for x in ordered_entries if x["status"] == "not_started"),
        "blacklisted": sum(1 for x in ordered_entries if x["status"] == "blacklisted"),
        "missing": sum(1 for x in ordered_entries if x["status"] == "missing"),
    }

    output = {
        "source_listing_url": listing_entry.get("url"),
        "summary": summary,
        "entries": ordered_entries,
    }

    write_json(OUTPUT_JSON, output)
    write_text(OUTPUT_MD, build_markdown(output))
    build_ordered_view(ordered_entries)

    print(f"Built course index: {OUTPUT_JSON}")
    print(f"Built course index markdown: {OUTPUT_MD}")
    print(f"Built ordered view: {ORDERED_DIR}")
    print(
        "Summary: "
        f"total={summary['total']} "
        f"answered={summary['answered']} "
        f"started_no_answer={summary['started_no_answer']} "
        f"not_started={summary['not_started']} "
        f"blacklisted={summary['blacklisted']} "
        f"missing={summary['missing']}"
    )


def build_markdown(data: dict) -> str:
    summary = data["summary"]
    entries = data["entries"]

    lines: list[str] = []
    lines.append("# Kursindex")
    lines.append("")
    lines.append(f"**Källa:** {data['source_listing_url']}")
    lines.append("")
    lines.append("## Sammanfattning")
    lines.append("")
    lines.append(f"- Totalt: {summary['total']}")
    lines.append(f"- Besvarade: {summary['answered']}")
    lines.append(f"- Startade utan svar: {summary['started_no_answer']}")
    lines.append(f"- Ej startade: {summary['not_started']}")
    lines.append(f"- Blacklistade: {summary['blacklisted']}")
    lines.append(f"- Saknas: {summary['missing']}")
    lines.append("")
    lines.append("## Uppgifter i kursordning")
    lines.append("")

    for entry in entries:
        order = str(entry["order"]).zfill(3)
        title = entry["title"]
        status = entry["status"]
        page_type = entry["page_type"]
        url = entry["url"]

        lines.append(f"- {order} | {status} | {page_type} | {title}")
        lines.append(f"  - URL: {url}")

        if entry.get("content_path"):
            lines.append(f"  - content.md: `{entry['content_path']}`")
        if entry.get("metadata_path"):
            lines.append(f"  - metadata.json: `{entry['metadata_path']}`")

    lines.append("")
    return "\n".join(lines)