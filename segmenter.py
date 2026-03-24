from __future__ import annotations

import re
from typing import Iterable

from schemas import RawBlock


SECTION_PATTERNS = [
    re.compile(p)
    for p in [
        r"^סמסטר\s+[א-ת]",
        r"^סמסטר\s+קיץ",
        r"^אין\s+לשבץ\s+בחינות",
        r"^חגים\s+ומועדים\s+נוספים",
        r"^תקופת\s+בחינות",
    ]
]


def _clean_lines(text: str) -> Iterable[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for line in text.split("\n"):
        yield line.strip()


def _is_section_header(line: str) -> bool:
    if not line:
        return False
    if any(pattern.search(line) for pattern in SECTION_PATTERNS):
        return True
    if len(line) <= 40 and line.endswith(":"):
        return True
    return False


def _is_hard_separator(line: str) -> bool:
    return bool(re.fullmatch(r"[-_=]{3,}", line))


def segment_text_to_blocks(text: str) -> list[RawBlock]:
    lines = list(_clean_lines(text))
    blocks: list[RawBlock] = []
    current_section = "general"
    current_lines: list[str] = []
    block_counter = 1

    def flush() -> None:
        nonlocal block_counter, current_lines
        if not current_lines:
            return
        source = "\n".join(current_lines).strip()
        if source:
            blocks.append(
                RawBlock(
                    block_id=f"B{block_counter:04d}",
                    section_context=current_section,
                    source_text=source,
                )
            )
            block_counter += 1
        current_lines = []

    for line in lines:
        if _is_section_header(line):
            flush()
            current_section = line.rstrip(":")
            continue

        if not line or _is_hard_separator(line):
            flush()
            continue

        current_lines.append(line)

    flush()
    return blocks
