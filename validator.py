from __future__ import annotations

from schemas import ClassifiedRecord, ValidationIssue


def validate_records(records: list[ClassifiedRecord]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for record in records:
        if record.start_date is None:
            issues.append(
                ValidationIssue(
                    block_id=record.block_id,
                    issue_type="missing_data",
                    severity="high",
                    message="Missing start_date",
                    source_text=record.source_text,
                )
            )

        if record.start_date and record.end_date and record.start_date > record.end_date:
            issues.append(
                ValidationIssue(
                    block_id=record.block_id,
                    issue_type="invalid_range",
                    severity="high",
                    message="start_date is after end_date",
                    source_text=record.source_text,
                )
            )

        if record.event_type == "exam_period" and record.end_date is None:
            issues.append(
                ValidationIssue(
                    block_id=record.block_id,
                    issue_type="missing_data",
                    severity="high",
                    message="Exam period missing end_date",
                    source_text=record.source_text,
                )
            )

        if record.is_estimated:
            issues.append(
                ValidationIssue(
                    block_id=record.block_id,
                    issue_type="estimated_dates",
                    severity="medium",
                    message="Estimated date marker (*) detected",
                    source_text=record.source_text,
                )
            )

        if record.exam_policy == "manual_review" or record.event_type == "manual_review":
            issues.append(
                ValidationIssue(
                    block_id=record.block_id,
                    issue_type="unclear_record",
                    severity="medium",
                    message="Ambiguous record classified as manual_review",
                    source_text=record.source_text,
                )
            )

        if record.requires_manual_review:
            issues.append(
                ValidationIssue(
                    block_id=record.block_id,
                    issue_type="manual_review",
                    severity="medium",
                    message="Record explicitly requires manual review",
                    source_text=record.source_text,
                )
            )

    # Conflict check by block_id: multiple contradictory policies are modeled upstream,
    # here we flag severe policy + allowed windows together as suspicious.
    for record in records:
        if record.exam_policy == "no_exams" and (
            record.allowed_start_time is not None or record.allowed_end_time is not None
        ):
            issues.append(
                ValidationIssue(
                    block_id=record.block_id,
                    issue_type="conflicts",
                    severity="high",
                    message="no_exams policy conflicts with allowed time window",
                    source_text=record.source_text,
                )
            )

    return issues
