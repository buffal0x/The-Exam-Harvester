from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from urllib.parse import urljoin

import yaml
from playwright.async_api import async_playwright
from tqdm import tqdm

from app.extractor import extract_page
from app.markdown_builder import build_content_markdown
from app.router import detect_page_type
from app.rules import (
    contains_allowed_text,
    contains_blacklisted_text,
    is_allowed_url,
    normalize_url,
)
from app.storage import ensure_dir, slugify_url, write_json, write_text


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_page_outputs(
    *,
    html: str,
    url: str,
    page,
    page_type: str,
    page_title: str,
    is_blacklisted_page: bool,
    raw_dir: Path,
    parsed_dir: Path,
    manifest: list[dict],
) -> None:
    page_id = slugify_url(url)

    raw_html_path = Path(raw_dir) / page_id / "raw.html"
    screenshot_path = Path(raw_dir) / page_id / "screenshot.png"
    parsed_json_path = Path(parsed_dir) / page_id / "metadata.json"
    parsed_md_path = Path(parsed_dir) / page_id / "content.md"

    raw_html_path.parent.mkdir(parents=True, exist_ok=True)
    parsed_json_path.parent.mkdir(parents=True, exist_ok=True)

    write_text(raw_html_path, html)

    data = {
        "url": url,
        "page_type": page_type,
        "fields": {},
        "blacklisted": is_blacklisted_page,
        "page_title": page_title,
    }

    if page_type != "unknown":
        extracted = extract_page(html, url, page_type, extractor_config)
        extracted["blacklisted"] = is_blacklisted_page
        extracted["page_title"] = page_title
        data = extracted

    write_json(parsed_json_path, data)
    write_text(parsed_md_path, build_content_markdown(data))

    manifest.append(
        {
            "id": page_id,
            "url": url,
            "page_type": page_type,
            "page_title": page_title,
            "blacklisted": is_blacklisted_page,
            "raw_html": str(raw_html_path),
            "screenshot": str(screenshot_path),
            "metadata": str(parsed_json_path),
            "markdown": str(parsed_md_path),
        }
    )

    return raw_html_path, screenshot_path


async def run_crawler() -> None:
    global extractor_config

    site_config = load_yaml("config/site.yaml")
    extractor_config = load_yaml("config/extractors.yaml")

    site = site_config["site"]
    auth = site_config["auth"]
    crawler_cfg = site_config["crawler"]
    storage_cfg = site_config["storage"]

    state_file = auth["state_file"]
    if not Path(state_file).exists():
        raise RuntimeError(f"Missing Playwright state file: {state_file}")

    raw_dir = ensure_dir(storage_cfg["raw_dir"])
    parsed_dir = ensure_dir(storage_cfg["parsed_dir"])
    manifest_dir = ensure_dir(storage_cfg["manifest_dir"])

    manifest_path = Path(manifest_dir) / "manifest.json"
    manifest: list[dict] = []

    blacklist_title_contains = crawler_cfg.get("blacklist_title_contains", [])
    blacklist_link_text_contains = crawler_cfg.get("blacklist_link_text_contains", [])
    blacklist_page_text_contains = crawler_cfg.get("blacklist_page_text_contains", [])

    allowed_start_title_contains = crawler_cfg.get("allowed_start_title_contains", [])
    start_button_selector = crawler_cfg.get("start_button_selector", ".exam-start-buttons button.btn-primary")
    start_form_selector = crawler_cfg.get("start_form_selector", "form.exam-start-buttons")
    submit_blocklist_text_contains = crawler_cfg.get("submit_blocklist_text_contains", ["Lämna in uppgift"])

    visited: set[str] = set()
    queued: set[str] = set()
    queue: deque[str] = deque([site["start_url"]])
    queued.add(site["start_url"])

    stats = {
        "processed": 0,
        "blacklisted": 0,
        "errors": 0,
        "saved": 0,
        "started": 0,
    }

    progress = tqdm(
        total=len(queue),
        desc="Scraping",
        unit="page",
        dynamic_ncols=True,
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=state_file)
        page = await context.new_page()

        while queue:
            url = normalize_url(queue.popleft())

            if url in visited:
                progress.set_postfix(
                    processed=stats["processed"],
                    queued=len(queue),
                    blacklisted=stats["blacklisted"],
                    started=stats["started"],
                    errors=stats["errors"],
                )
                continue

            visited.add(url)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
            except Exception as exc:
                stats["errors"] += 1
                stats["processed"] += 1
                progress.update(1)
                progress.set_postfix(
                    processed=stats["processed"],
                    queued=len(queue),
                    blacklisted=stats["blacklisted"],
                    started=stats["started"],
                    errors=stats["errors"],
                )
                print(f"[ERROR] Failed to open {url}: {exc}")
                continue

            html = await page.content()
            page_type = detect_page_type(html, extractor_config) or "unknown"

            page_title = ""
            try:
                page_title = (await page.locator("h1").first.text_content() or "").strip()
            except Exception:
                page_title = ""

            page_text = ""
            try:
                page_text = (await page.locator("body").inner_text()).strip()
            except Exception:
                page_text = ""

            is_blacklisted_title = contains_blacklisted_text(
                page_title,
                blacklist_title_contains,
            )

            is_exam_page = "/exam/" in url
            is_blacklisted_page_text = False

            if is_exam_page:
                is_blacklisted_page_text = contains_blacklisted_text(
                    page_text,
                    blacklist_page_text_contains,
                )

            is_blacklisted_page = is_blacklisted_title or is_blacklisted_page_text

            raw_html_path, screenshot_path = save_page_outputs(
                html=html,
                url=url,
                page=page,
                page_type=page_type,
                page_title=page_title,
                is_blacklisted_page=is_blacklisted_page,
                raw_dir=Path(raw_dir),
                parsed_dir=Path(parsed_dir),
                manifest=manifest,
            )

            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception as exc:
                print(f"[WARN] Screenshot failed for {url}: {exc}")

            stats["saved"] += 1

            should_try_start = (
                page_type == "exam_preview"
                and not is_blacklisted_page
                and contains_allowed_text(page_title, allowed_start_title_contains)
            )

            if should_try_start:
                try:
                    submit_buttons = page.locator("button")
                    submit_count = await submit_buttons.count()

                    blocked_submit_present = False
                    for i in range(submit_count):
                        text = (await submit_buttons.nth(i).text_content() or "").strip()
                        if contains_blacklisted_text(text, submit_blocklist_text_contains):
                            blocked_submit_present = True
                            break

                    start_form_exists = await page.locator(start_form_selector).count() > 0
                    start_button = page.locator(start_button_selector)

                    if start_form_exists and await start_button.count() > 0 and not blocked_submit_present:
                        print(f"[START] Starting allowed assignment: {page_title} ({url})")
                        await start_button.first.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await page.wait_for_timeout(2500)

                        started_url = normalize_url(page.url)
                        started_html = await page.content()
                        started_page_type = detect_page_type(started_html, extractor_config) or "unknown"

                        started_title = ""
                        try:
                            started_title = (await page.locator("h1").first.text_content() or "").strip()
                        except Exception:
                            started_title = page_title

                        started_text = ""
                        try:
                            started_text = (await page.locator("body").inner_text() or "").strip()
                        except Exception:
                            started_text = ""

                        started_is_blacklisted_title = contains_blacklisted_text(
                            started_title,
                            blacklist_title_contains,
                        )
                        started_is_blacklisted_page_text = contains_blacklisted_text(
                            started_text,
                            blacklist_page_text_contains,
                        ) if "/exam/" in started_url else False

                        started_is_blacklisted_page = (
                            started_is_blacklisted_title or started_is_blacklisted_page_text
                        )

                        _, started_screenshot_path = save_page_outputs(
                            html=started_html,
                            url=started_url,
                            page=page,
                            page_type=started_page_type,
                            page_title=started_title,
                            is_blacklisted_page=started_is_blacklisted_page,
                            raw_dir=Path(raw_dir),
                            parsed_dir=Path(parsed_dir),
                            manifest=manifest,
                        )

                        try:
                            await page.screenshot(path=str(started_screenshot_path), full_page=True)
                        except Exception as exc:
                            print(f"[WARN] Screenshot failed after start for {started_url}: {exc}")

                        stats["saved"] += 1
                        stats["started"] += 1

                        html = started_html
                        url = started_url
                        page_type = started_page_type
                        page_title = started_title
                        page_text = started_text
                        is_blacklisted_page = started_is_blacklisted_page

                except Exception as exc:
                    stats["errors"] += 1
                    print(f"[WARN] Failed to start assignment on {url}: {exc}")

            if is_blacklisted_page:
                stats["blacklisted"] += 1
                print(f"[BLACKLIST] Skipping blacklisted page: {page_title} ({url})")
                stats["processed"] += 1
                progress.update(1)
                progress.set_postfix(
                    processed=stats["processed"],
                    queued=len(queue),
                    blacklisted=stats["blacklisted"],
                    started=stats["started"],
                    errors=stats["errors"],
                )
                continue

            try:
                anchors_data = await page.locator("a").evaluate_all(
                    """
                    elements => elements.map(el => ({
                        href: el.href,
                        text: (el.innerText || el.textContent || '').trim()
                    })).filter(x => x.href)
                    """
                )
            except Exception as exc:
                stats["errors"] += 1
                stats["processed"] += 1
                progress.update(1)
                progress.set_postfix(
                    processed=stats["processed"],
                    queued=len(queue),
                    blacklisted=stats["blacklisted"],
                    started=stats["started"],
                    errors=stats["errors"],
                )
                print(f"[WARN] Could not collect links on {url}: {exc}")
                continue

            next_urls: list[str] = []

            for item in anchors_data:
                href = item.get("href", "")
                text = item.get("text", "")

                if not href:
                    continue

                if contains_blacklisted_text(text, blacklist_link_text_contains):
                    continue

                full_url = normalize_url(urljoin(url, href))

                if is_allowed_url(
                    full_url,
                    crawler_cfg.get("allowed_domains", []),
                    crawler_cfg.get("allowed_url_patterns", []),
                    crawler_cfg.get("denied_url_patterns", []),
                ):
                    next_urls.append(full_url)

            for next_url in dict.fromkeys(next_urls):
                if next_url not in visited and next_url not in queued:
                    queue.append(next_url)
                    queued.add(next_url)

            stats["processed"] += 1

            progress.total = max(progress.total, len(visited) + len(queue))
            progress.update(1)
            progress.set_postfix(
                processed=stats["processed"],
                queued=len(queue),
                blacklisted=stats["blacklisted"],
                started=stats["started"],
                errors=stats["errors"],
            )

        progress.close()
        await context.close()
        await browser.close()

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved manifest to: {manifest_path}")
    print(
        f"Done. Processed={stats['processed']} Saved={stats['saved']} "
        f"Blacklisted={stats['blacklisted']} Started={stats['started']} Errors={stats['errors']}"
    )