from __future__ import annotations

from collections import defaultdict

from schemas import ClassifiedRecord


POLICY_PRIORITY = {
    "no_exams": 1,
    "manual_review": 2,
    "morning_only": 3,
    "time_window_only": 4,
    "allowed": 5,
}


def build_core_calendar_events(records: list[ClassifiedRecord]) -> list[dict]:
    return [
        {
            "block_id": r.block_id,
            "event_name": r.event_name,
            "event_type": r.event_type,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "notes": r.notes,
            "classification_reason": r.classification_reason,
            "source_text": r.source_text,
        }
        for r in records
    ]


def build_exam_constraints_calendar(records: list[ClassifiedRecord]) -> list[dict]:
    grouped: dict[tuple, list[ClassifiedRecord]] = defaultdict(list)
    for r in records:
        key = (r.start_date, r.end_date, r.event_name)
        grouped[key].append(r)

    merged: list[dict] = []
    for (_start, _end, _name), items in grouped.items():
        items_sorted = sorted(items, key=lambda r: POLICY_PRIORITY.get(r.exam_policy, 99))
        strongest = items_sorted[0]

        merged.append(
            {
                "event_name": strongest.event_name,
                "start_date": strongest.start_date,
                "end_date": strongest.end_date,
                "is_estimated": any(i.is_estimated for i in items),
                "exam_policy": strongest.exam_policy,
                "allowed_start_time": strongest.allowed_start_time,
                "allowed_end_time": strongest.allowed_end_time,
                "requires_manual_review": any(i.requires_manual_review for i in items),
                "notes": "; ".join(dict.fromkeys(i.notes for i in items)),
                "classification_reason": " || ".join(i.classification_reason for i in items),
                "source_text": "\n---\n".join(i.source_text for i in items),
            }
        )

    merged.sort(key=lambda row: (row["start_date"] is None, row["start_date"], row["event_name"]))
    return merged


def build_tables(records: list[ClassifiedRecord]) -> tuple[list[dict], list[dict]]:
    return build_core_calendar_events(records), build_exam_constraints_calendar(records)
