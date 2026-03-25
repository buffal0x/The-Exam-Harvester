from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from app.cli_ui import HarvesterUI
from app.course_context import build_course_context, load_yaml
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


def upsert_manifest_entry(manifest: list[dict], entry: dict) -> None:
    for idx, existing in enumerate(manifest):
        if existing.get("id") == entry.get("id"):
            manifest[idx] = entry
            return
    manifest.append(entry)


async def save_page_outputs(
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
    extractor_config: dict,
    ui: HarvesterUI | None = None,
) -> tuple[Path, Path]:
    page_id = slugify_url(url)

    raw_html_path = raw_dir / page_id / "raw.html"
    screenshot_path = raw_dir / page_id / "screenshot.png"
    parsed_json_path = parsed_dir / page_id / "metadata.json"
    parsed_md_path = parsed_dir / page_id / "content.md"

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

    upsert_manifest_entry(
        manifest,
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
        },
    )

    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception as exc:
        if ui:
            ui.warn(f"Screenshot failed for {url}: {exc}")

    return raw_html_path, screenshot_path


async def run_crawler(course_ref: str | None = None) -> None:
    context = build_course_context(course_ref)
    site_config = context["site_config"]
    extractor_config = load_yaml("config/extractors.yaml")

    course_id = context["course_id"]
    start_url = context["start_url"]
    allowed_domains = context["allowed_domains"]
    allowed_url_patterns = context["allowed_url_patterns"]
    denied_url_patterns = context["denied_url_patterns"]

    auth = site_config["auth"]
    crawler_cfg = site_config["crawler"]
    storage_cfg = context["storage"]

    state_file = auth["state_file"]
    if not Path(state_file).exists():
        raise RuntimeError(f"Missing Playwright state file: {state_file}")

    raw_dir = Path(ensure_dir(storage_cfg["raw_dir"]))
    parsed_dir = Path(ensure_dir(storage_cfg["parsed_dir"]))
    manifest_dir = Path(ensure_dir(storage_cfg["manifest_dir"]))

    manifest_path = manifest_dir / "manifest.json"
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
    queue: deque[str] = deque([start_url])
    queued.add(start_url)

    stats = {
        "processed": 0,
        "blacklisted": 0,
        "errors": 0,
        "saved": 0,
        "started": 0,
    }

    ui = HarvesterUI(
        course_id=course_id,
        start_url=start_url,
        output_base=storage_cfg["base_dir"],
    )
    ui.start()
    ui.info(f"Initialized crawler for course {course_id}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_browser = await browser.new_context(storage_state=state_file)
        page = await context_browser.new_page()

        try:
            while queue:
                loop_started = time.perf_counter()
                url = normalize_url(queue.popleft())

                if url in visited:
                    ui.update(
                        processed=stats["processed"],
                        total=max(len(visited) + len(queue), 1),
                        queued=len(queue),
                        blacklisted=stats["blacklisted"],
                        started=stats["started"],
                        saved=stats["saved"],
                        errors=stats["errors"],
                        rate="-",
                    )
                    continue

                visited.add(url)

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(2000)
                except Exception as exc:
                    stats["errors"] += 1
                    stats["processed"] += 1

                    elapsed = max(time.perf_counter() - loop_started, 0.001)
                    ui.error(f"Failed to open {url}: {exc}")
                    ui.update(
                        processed=stats["processed"],
                        total=max(len(visited) + len(queue), 1),
                        queued=len(queue),
                        blacklisted=stats["blacklisted"],
                        started=stats["started"],
                        saved=stats["saved"],
                        errors=stats["errors"],
                        rate=f"{elapsed:.2f}s/page",
                    )
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

                is_blacklisted_title = contains_blacklisted_text(page_title, blacklist_title_contains)

                is_exam_page = "/exam/" in url
                is_blacklisted_page_text = False

                # Only apply page-text blacklist to exam pages that look restricted,
                # not to ordinary previews just because they contain generic status text.
                if is_exam_page and page_type != "exam_preview":
                    is_blacklisted_page_text = contains_blacklisted_text(page_text, blacklist_page_text_contains)

                is_blacklisted_page = is_blacklisted_title or is_blacklisted_page_text

                await save_page_outputs(
                    html=html,
                    url=url,
                    page=page,
                    page_type=page_type,
                    page_title=page_title,
                    is_blacklisted_page=is_blacklisted_page,
                    raw_dir=raw_dir,
                    parsed_dir=parsed_dir,
                    manifest=manifest,
                    extractor_config=extractor_config,
                    ui=ui,
                )

                stats["saved"] += 1

                start_form_exists = await page.locator(start_form_selector).count() > 0
                start_button_exists = await page.locator(start_button_selector).count() > 0
                title_allowed = contains_allowed_text(page_title, allowed_start_title_contains)

                should_try_start = (
                    page_type == "exam_preview"
                    and not is_blacklisted_page
                    and start_form_exists
                    and start_button_exists
                )
                
                if page_type == "exam_preview":
                    ui.info(
                        f"Preview detected: title={page_title!r} "
                        f"blacklisted={is_blacklisted_page} "
                        f"title_allowed={title_allowed} "
                        f"start_form={start_form_exists} "
                        f"start_button={start_button_exists}"
                    )
                    
                    ui.info(f"Processed page_type={page_type} title={page_title!r}")
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
                            ui.info(f"Starting assignment: {page_title}")
                            ui.success(f"Started successfully: {started_title}")
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
                            started_is_blacklisted_page_text = (
                                contains_blacklisted_text(started_text, blacklist_page_text_contains)
                                if "/exam/" in started_url
                                else False
                            )

                            started_is_blacklisted_page = (
                                started_is_blacklisted_title or started_is_blacklisted_page_text
                            )

                            await save_page_outputs(
                                html=started_html,
                                url=started_url,
                                page=page,
                                page_type=started_page_type,
                                page_title=started_title,
                                is_blacklisted_page=started_is_blacklisted_page,
                                raw_dir=raw_dir,
                                parsed_dir=parsed_dir,
                                manifest=manifest,
                                extractor_config=extractor_config,
                                ui=ui,
                            )

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
                        ui.warn(f"Failed to start assignment on {url}: {exc}")

                if is_blacklisted_page:
                    stats["blacklisted"] += 1
                    ui.warn(f"Blacklisted page skipped: {page_title} ({url})")
                    stats["processed"] += 1

                    elapsed = max(time.perf_counter() - loop_started, 0.001)
                    ui.update(
                        processed=stats["processed"],
                        total=max(len(visited) + len(queue), 1),
                        queued=len(queue),
                        blacklisted=stats["blacklisted"],
                        started=stats["started"],
                        saved=stats["saved"],
                        errors=stats["errors"],
                        rate=f"{elapsed:.2f}s/page",
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

                    elapsed = max(time.perf_counter() - loop_started, 0.001)
                    ui.warn(f"Could not collect links on {url}: {exc}")
                    ui.update(
                        processed=stats["processed"],
                        total=max(len(visited) + len(queue), 1),
                        queued=len(queue),
                        blacklisted=stats["blacklisted"],
                        started=stats["started"],
                        saved=stats["saved"],
                        errors=stats["errors"],
                        rate=f"{elapsed:.2f}s/page",
                    )
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
                        allowed_domains,
                        allowed_url_patterns,
                        denied_url_patterns,
                    ):
                        next_urls.append(full_url)

                for next_url in dict.fromkeys(next_urls):
                    if next_url not in visited and next_url not in queued:
                        queue.append(next_url)
                        queued.add(next_url)

                stats["processed"] += 1

                elapsed = max(time.perf_counter() - loop_started, 0.001)
                ui.update(
                    processed=stats["processed"],
                    total=max(len(visited) + len(queue), 1),
                    queued=len(queue),
                    blacklisted=stats["blacklisted"],
                    started=stats["started"],
                    saved=stats["saved"],
                    errors=stats["errors"],
                    rate=f"{elapsed:.2f}s/page",
                )

        finally:
            await context_browser.close()
            await browser.close()

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ui.success(f"Saved manifest to: {manifest_path}")
    ui.success(
        f"Done. course_id={course_id} "
        f"Processed={stats['processed']} "
        f"Saved={stats['saved']} "
        f"Blacklisted={stats['blacklisted']} "
        f"Started={stats['started']} "
        f"Errors={stats['errors']}"
    )
    ui.stop()