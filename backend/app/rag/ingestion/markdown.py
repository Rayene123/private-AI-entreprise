from __future__ import annotations

import re
from collections.abc import Iterable

from .parsers import ContentBlock


def blocks_to_markdown(blocks: Iterable[ContentBlock]) -> str:
    output: list[str] = []
    current_page: int | None = None
    for block in blocks:
        if block.page_number != current_page and block.page_number is not None:
            if output:
                output.append("")
            output.append(f"<!-- Page {block.page_number} -->")
            current_page = block.page_number
        text = block.content
        if block.kind == "table":
            output.extend(_table_to_markdown(text))
        else:
            normalized = _normalize_text(str(text))
            if normalized:
                output.append(normalized)
        if output and output[-1] != "":
            output.append("")
    return _normalize_markdown("\n".join(output))


def _table_to_markdown(table: object) -> list[str]:
    rows = [list(row) for row in table]  # type: ignore[union-attr]
    if not rows:
        return []
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(escape(cell) for cell in padded[0]) + " |"]
    lines.append("|" + "|".join("---" for _ in range(width)) + "|")
    lines.extend(
        "| " + " | ".join(escape(cell) for cell in row) + " |"
        for row in padded[1:]
    )
    return lines


def _normalize_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def _normalize_markdown(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()
