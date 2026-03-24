from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Literal, Optional


ExamPolicy = Literal["no_exams", "morning_only", "time_window_only", "allowed", "manual_review"]
EventType = Literal[
    "semester_start",
    "semester_end",
    "exam_period",
    "no_classes",
    "university_closed",
    "shortened_day",
    "midday_break",
    "makeup_day",
    "no_exam_scheduling",
    "academic_event",
    "manual_review",
]


@dataclass
class ExtractionResult:
    text: str
    status: str
    filename: str


@dataclass
class RawBlock:
    block_id: str
    section_context: str
    source_text: str


@dataclass
class ParsedBlock:
    block_id: str
    section_context: str
    source_text: str
    detected_date_start: Optional[date]
    detected_date_end: Optional[date]
    detected_time_start: Optional[str]
    detected_time_end: Optional[str]


@dataclass
class ClassifiedRecord:
    block_id: str
    event_name: str
    event_type: EventType
    start_date: Optional[date]
    end_date: Optional[date]
    exam_policy: ExamPolicy
    allowed_start_time: Optional[str]
    allowed_end_time: Optional[str]
    requires_manual_review: bool
    is_estimated: bool
    classification_reason: str
    notes: str
    source_text: str


@dataclass
class ValidationIssue:
    block_id: str
    issue_type: str
    severity: str
    message: str
    source_text: str



def as_record(obj: object) -> dict:
    return asdict(obj)
