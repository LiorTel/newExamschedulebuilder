from __future__ import annotations

import re

from schemas import ClassifiedRecord, ParsedBlock


def _event_name(text: str) -> str:
    first_line = text.splitlines()[0].strip()
    return first_line[:120] if first_line else "Unnamed event"


def classify_block(block: ParsedBlock) -> ClassifiedRecord:
    text = block.source_text
    normalized = re.sub(r"\s+", " ", text)

    event_type = "academic_event"
    exam_policy = "allowed"
    allowed_start_time = None
    allowed_end_time = None
    requires_review = False
    is_estimated = "*" in text
    reasons: list[str] = []

    if "האוניברסיטה סגורה" in normalized:
        event_type = "university_closed"
        exam_policy = "no_exams"
        reasons.append("Matched rule: האוניברסיטה סגורה -> no_exams")

    if "אין לשבץ בחינות" in normalized:
        event_type = "no_exam_scheduling"
        exam_policy = "no_exams"
        reasons.append("Matched rule: אין לשבץ בחינות -> no_exams")

    if "אין לימודים" in normalized:
        event_type = "no_classes"
        reasons.append("Matched rule: אין לימודים -> no_classes")

    if "תקופת בחינות" in normalized:
        event_type = "exam_period"
        reasons.append("Matched rule: תקופת בחינות -> exam_period")

    if "יום השלמה" in normalized:
        event_type = "makeup_day"
        reasons.append("Matched rule: יום השלמה -> makeup_day")

    if "הפסקת לימודים" in normalized and (block.detected_time_start or block.detected_time_end):
        event_type = "midday_break"
        exam_policy = "time_window_only"
        allowed_start_time = block.detected_time_end or "13:00"
        allowed_end_time = "20:00"
        reasons.append("Matched rule: הפסקת לימודים with time -> midday_break")

    if "הלימודים יסתיימו בשעה" in normalized:
        event_type = "shortened_day"
        exam_policy = "time_window_only"
        allowed_start_time = "08:00"
        allowed_end_time = "13:00"
        reasons.append("Matched rule: early closing -> exams until 13:00")

    if any(token in normalized for token in ["רמדאן", "רמאדן", "Ramadan"]):
        exam_policy = "morning_only"
        allowed_start_time = "08:00"
        allowed_end_time = "13:00"
        reasons.append("Matched rule: Ramadan -> morning_only 08:00-13:00")
        if block.detected_date_start is None or block.detected_date_end is None:
            requires_review = True
            reasons.append("Date uncertain for Ramadan block")

    if is_estimated:
        requires_review = True
        reasons.append("Contains '*' marker -> estimated date and manual review")

    if block.detected_date_start is None:
        requires_review = True
        reasons.append("Missing start date")

    if not reasons:
        event_type = "manual_review"
        exam_policy = "manual_review"
        requires_review = True
        reasons.append("No deterministic rule matched")

    return ClassifiedRecord(
        block_id=block.block_id,
        event_name=_event_name(text),
        event_type=event_type,  # type: ignore[arg-type]
        start_date=block.detected_date_start,
        end_date=block.detected_date_end,
        exam_policy=exam_policy,  # type: ignore[arg-type]
        allowed_start_time=allowed_start_time,
        allowed_end_time=allowed_end_time,
        requires_manual_review=requires_review,
        is_estimated=is_estimated,
        classification_reason=" | ".join(reasons),
        notes=f"section={block.section_context}",
        source_text=block.source_text,
    )


def classify_blocks(blocks: list[ParsedBlock]) -> list[ClassifiedRecord]:
    return [classify_block(block) for block in blocks]
