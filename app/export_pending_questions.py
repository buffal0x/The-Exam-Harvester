from __future__ import annotations

import json
import re
from pathlib import Path


INDEX_PATH = Path("data/index/course_index.json")
OUTPUT_PATH = Path("data/index/pending_questions.md")


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_questions_from_content_md(content: str) -> list[str]:
    """
    Extract question blocks from content.md.

    Expected format example:
    ## Fråga 1
    <text>

    ## Fråga 2
    <text>
    """
    pattern = r"^##\s+Fråga\s+\d+\s*$"
    lines = content.splitlines()

    questions: list[str] = []
    current_block: list[str] = []
    inside_question = False

    for line in lines:
        if re.match(pattern, line.strip(), flags=re.IGNORECASE):
            if current_block:
                questions.append("\n".join(current_block).strip())
                current_block = []

            inside_question = True
            current_block.append(line.rstrip())
            continue

        if inside_question:
            if line.strip().startswith("**URL:**"):
                continue
            current_block.append(line.rstrip())

    if current_block:
        questions.append("\n".join(current_block).strip())

    return [q for q in questions if q.strip()]


def build_pending_markdown(index_data: dict) -> str:
    entries = index_data.get("entries", [])

    lines: list[str] = []
    lines.append("# Oklarade uppgifter")
    lines.append("")

    total_pending = 0

    for entry in entries:
        if entry.get("status") != "started_no_answer":
            continue

        content_path_value = entry.get("content_path")
        if not content_path_value:
            continue

        content_path = Path(content_path_value)
        if not content_path.exists():
            continue

        order = str(entry["order"]).zfill(3)
        title = entry.get("title", "Untitled")
        url = entry.get("url", "")
        content = read_text(content_path)

        questions = extract_questions_from_content_md(content)
        if not questions:
            continue

        total_pending += 1

        lines.append(f"# {order} — {title}")
        lines.append("")

        for idx, question_block in enumerate(questions, start=1):
            # Remove duplicated heading from source block if present
            cleaned_block = re.sub(
                r"^##\s+Fråga\s+\d+\s*$",
                "",
                question_block.strip(),
                flags=re.IGNORECASE | re.MULTILINE,
            ).strip()

            lines.append(f"## Fråga {idx}")
            lines.append("")
            lines.append(cleaned_block)
            lines.append("")

        lines.append(f"**URL:** {url}")
        lines.append("")
        lines.append("---")
        lines.append("")

    if total_pending == 0:
        lines.append("Inga uppgifter med status `started_no_answer` hittades.")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    if not INDEX_PATH.exists():
        raise RuntimeError(f"Missing index file: {INDEX_PATH}")

    index_data = load_json(INDEX_PATH)
    output = build_pending_markdown(index_data)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")

    print(f"Created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()