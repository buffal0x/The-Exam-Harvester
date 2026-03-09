from __future__ import annotations

import re

from bs4 import BeautifulSoup
from markdownify import markdownify as md


def clean_container_html(html: str, keep_tags: list[str]) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.name not in keep_tags:
            tag.unwrap()

    return str(soup)


def extract_links(container, selector: str) -> list[dict]:
    links = []
    for tag in container.select(selector):
        href = tag.get("href")
        text = tag.get_text(" ", strip=True)
        if href:
            links.append({"text": text, "href": href})
    return links


def clean_title(text: str | None) -> str | None:
    if not text:
        return text

    cleaned = re.sub(r"\s+", " ", text).strip()

    stop_markers = [
        " Dator- och kommunikationsteknik nivå 3",
        " Tillbaka till kursen",
    ]

    for marker in stop_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker)[0].strip()

    return cleaned


def extract_question_blocks(container, selector: str, keep_tags: list[str]) -> list[dict]:
    blocks = []

    for index, block in enumerate(container.select(selector), start=1):
        question_node = block.select_one("div[client-type] .ql-editor")
        answer_node = block.select_one(".exam-revisioned-component .ql-editor")
        rubric_node = block.select_one(".col-sm-3 .ql-editor, h4 + .quill .ql-editor")
        score_node = block.select_one(".eq-score")

        question_html = None
        question_markdown = None
        question_text = None

        if question_node:
            question_html = clean_container_html(str(question_node), keep_tags)
            question_markdown = md(question_html).strip() or None
            question_text = question_node.get_text(" ", strip=True) or None

        answer_html = None
        answer_markdown = None
        answer_text = None

        if answer_node:
            answer_html = clean_container_html(str(answer_node), keep_tags)
            answer_markdown = md(answer_html).strip() or None
            answer_text = answer_node.get_text(" ", strip=True) or None

        rubric_html = None
        rubric_markdown = None
        rubric_text = None

        if rubric_node:
            rubric_html = clean_container_html(str(rubric_node), keep_tags)
            rubric_markdown = md(rubric_html).strip() or None
            rubric_text = rubric_node.get_text(" ", strip=True) or None

        score_text = score_node.get_text(" ", strip=True) if score_node else None

        blocks.append(
            {
                "index": index,
                "question_html": question_html,
                "question_markdown": question_markdown,
                "question_text": question_text,
                "answer_html": answer_html,
                "answer_markdown": answer_markdown,
                "answer_text": answer_text,
                "rubric_html": rubric_html,
                "rubric_markdown": rubric_markdown,
                "rubric_text": rubric_text,
                "score_text": score_text,
            }
        )

    return blocks


def extract_page(html: str, url: str, page_type: str, extractor_config: dict) -> dict:
    soup = BeautifulSoup(html, "lxml")
    page_cfg = extractor_config["page_types"][page_type]
    container_selector = page_cfg.get("container")
    keep_tags = page_cfg.get("keep_tags", [])

    container = None
    if container_selector:
        selectors = [s.strip() for s in container_selector.split(",")]
        for selector in selectors:
            container = soup.select_one(selector)
            if container is not None:
                break

    if container is None:
        container = soup.body or soup

    fields_out = {}

    for field_name, field_cfg in page_cfg.get("fields", {}).items():
        selector = field_cfg.get("selector")
        field_type = field_cfg.get("type", "text")

        search_root = container
        node = search_root.select_one(selector) if selector and field_type not in {"links", "multi_question_blocks"} else None

        if node is None and soup is not search_root and selector and field_type not in {"links", "multi_question_blocks"}:
            node = soup.select_one(selector)

        if field_type == "text":
            value = node.get_text(" ", strip=True) if node else None
            if field_name == "title":
                value = clean_title(value)
            fields_out[field_name] = value

        elif field_type == "html":
            if node:
                cleaned_html = clean_container_html(str(node), keep_tags)
                fields_out[field_name] = cleaned_html
                markdown_value = md(cleaned_html).strip()
                fields_out[f"{field_name}_markdown"] = markdown_value if markdown_value else None
            else:
                fields_out[field_name] = None
                fields_out[f"{field_name}_markdown"] = None

        elif field_type == "links":
            links = extract_links(search_root, selector) if selector else []
            if not links and soup is not search_root and selector:
                links = extract_links(soup, selector)
            fields_out[field_name] = links

        elif field_type == "multi_question_blocks":
            blocks = extract_question_blocks(search_root, selector, keep_tags) if selector else []
            if not blocks and soup is not search_root and selector:
                blocks = extract_question_blocks(soup, selector, keep_tags)
            fields_out[field_name] = blocks

        else:
            fields_out[field_name] = None

    return {
        "url": url,
        "page_type": page_type,
        "fields": fields_out,
    }