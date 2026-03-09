from __future__ import annotations


def build_content_markdown(data: dict) -> str:
    fields = data.get("fields", {})
    page_type = data.get("page_type")
    title = fields.get("title") or data.get("page_title") or "Untitled"
    url = data.get("url", "")

    lines: list[str] = [f"# {title}", ""]

    if page_type == "exam_active":
        question_blocks = fields.get("question_blocks", [])

        if question_blocks:
            for block in question_blocks:
                index = block.get("index")
                question = (block.get("question_markdown") or block.get("question_text") or "").strip()
                answer = (block.get("answer_markdown") or block.get("answer_text") or "").strip()
                rubric = (block.get("rubric_markdown") or block.get("rubric_text") or "").strip()
                score = (block.get("score_text") or "").strip()

                lines.append(f"## Fråga {index}")
                lines.append("")
                if question:
                    lines.append(question)
                    lines.append("")

                if answer:
                    lines.append("### Svar")
                    lines.append("")
                    lines.append(answer)
                    lines.append("")

                if rubric:
                    lines.append("### Rättningsmall")
                    lines.append("")
                    lines.append(rubric)
                    lines.append("")

                if score:
                    lines.append("### Poäng")
                    lines.append("")
                    lines.append(score)
                    lines.append("")
        else:
            question = (
                fields.get("question_html_markdown")
                or fields.get("first_question_paragraph")
                or ""
            ).strip()

            if question:
                lines.append("## Fråga")
                lines.append("")
                lines.append(question)
                lines.append("")

        lines.append(f"**URL:** {url}")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    if page_type == "exam_preview":
        preview = (
            fields.get("preview_html_markdown")
            or fields.get("first_paragraph")
            or ""
        ).strip()

        if preview:
            lines.append("## Innehåll")
            lines.append("")
            lines.append(preview)
            lines.append("")

        lines.append(f"**URL:** {url}")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    if page_type == "exams_list":
        links = fields.get("exam_links", [])
        if links:
            lines.append("## Uppgifter")
            lines.append("")
            for item in links:
                text = item.get("text", "").strip()
                href = item.get("href", "").strip()
                if text and href:
                    lines.append(f"- [{text}]({href})")
                elif text:
                    lines.append(f"- {text}")
            lines.append("")

        lines.append(f"**URL:** {url}")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    added_content = False

    for key, value in fields.items():
        if key == "title" or value is None:
            continue

        if isinstance(value, str) and value.strip():
            heading = key.replace("_markdown", "").replace("_", " ").strip().title()
            lines.append(f"## {heading}")
            lines.append("")
            lines.append(value.strip())
            lines.append("")
            added_content = True

        elif isinstance(value, list) and value:
            heading = key.replace("_", " ").strip().title()
            lines.append(f"## {heading}")
            lines.append("")
            for item in value:
                lines.append(f"- {str(item).strip()}")
            lines.append("")
            added_content = True

    if not added_content:
        lines.append("No structured content extracted.")
        lines.append("")

    lines.append(f"**URL:** {url}")
    lines.append("")

    return "\n".join(lines).strip() + "\n"