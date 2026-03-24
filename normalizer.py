from __future__ import annotations

import re
from datetime import date
from typing import Optional

from schemas import ParsedBlock, RawBlock


DATE_RANGE_INLINE = re.compile(r"(?P<d1>\d{1,2})-(?P<d2>\d{1,2})\.(?P<m>\d{1,2})\.(?P<y>\d{2,4})")
DATE_RANGE_WORDS = re.compile(
    r"מ[-\s]*(?P<d1>\d{1,2}\.\d{1,2}\.\d{2,4})\s*עד\s*(?P<d2>\d{1,2}\.\d{1,2}\.\d{2,4})"
)
DATE_SINGLE = re.compile(r"(?<!\d)(?P<d>\d{1,2})\.(?P<m>\d{1,2})\.(?P<y>\d{2,4})(?!\d)")
TIME_RANGE = re.compile(r"(?P<t1>\d{1,2}:\d{2})\s*(?:עד|\-|–)\s*(?P<t2>\d{1,2}:\d{2})")
TIME_START_ONLY = re.compile(r"(?:משעה|מ[-\s]*|בשעה\s*)(?P<t1>\d{1,2}:\d{2})")


def _normalize_year(y: int) -> int:
    return y + 2000 if y < 100 else y


def _to_date(d: int, m: int, y: int) -> Optional[date]:
    try:
        return date(_normalize_year(y), m, d)
    except ValueError:
        return None


def _parse_dmy(token: str) -> Optional[date]:
    m = DATE_SINGLE.search(token)
    if not m:
        return None
    return _to_date(int(m.group("d")), int(m.group("m")), int(m.group("y")))


def normalize_block(block: RawBlock) -> ParsedBlock:
    text = block.source_text

    start_date = None
    end_date = None

    m_range_words = DATE_RANGE_WORDS.search(text)
    if m_range_words:
        start_date = _parse_dmy(m_range_words.group("d1"))
        end_date = _parse_dmy(m_range_words.group("d2"))
    else:
        m_range_inline = DATE_RANGE_INLINE.search(text)
        if m_range_inline:
            d1 = int(m_range_inline.group("d1"))
            d2 = int(m_range_inline.group("d2"))
            month = int(m_range_inline.group("m"))
            year = int(m_range_inline.group("y"))
            start_date = _to_date(d1, month, year)
            end_date = _to_date(d2, month, year)

    if not start_date:
        singles = [
            _to_date(int(m.group("d")), int(m.group("m")), int(m.group("y")))
            for m in DATE_SINGLE.finditer(text)
        ]
        singles = [d for d in singles if d is not None]
        if singles:
            start_date = singles[0]
            end_date = singles[-1] if len(singles) > 1 else singles[0]

    time_start = None
    time_end = None

    m_time_range = TIME_RANGE.search(text)
    if m_time_range:
        time_start = m_time_range.group("t1")
        time_end = m_time_range.group("t2")
    else:
        m_time_start = TIME_START_ONLY.search(text)
        if m_time_start:
            time_start = m_time_start.group("t1")

    return ParsedBlock(
        block_id=block.block_id,
        section_context=block.section_context,
        source_text=text,
        detected_date_start=start_date,
        detected_date_end=end_date,
        detected_time_start=time_start,
        detected_time_end=time_end,
    )


def normalize_blocks(blocks: list[RawBlock]) -> list[ParsedBlock]:
    return [normalize_block(block) for block in blocks]
