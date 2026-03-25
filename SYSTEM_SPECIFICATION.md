# Hebrew Academic Exam Scheduling System — Full Product, UX, Architecture, Delivery, and QA Specification

## 1) Product Specification

### 1.1 Purpose

This system solves a high-risk manual planning problem: converting a Hebrew academic calendar (often text-heavy, ambiguous, and full of exceptions) into a defensible, auditable exam schedule.

Without this system, scheduling teams typically rely on spreadsheet logic and manual interpretation, causing:
- inconsistent interpretation of closures/holidays,
- missed implicit constraints,
- last-minute conflicts,
- weak auditability.

The system delivers:
1. **Structured calendar constraints** extracted from Hebrew source text.
2. **Human-reviewed interpretation** of ambiguous or low-confidence items.
3. **Constraint-compliant draft exam schedule** from validated courses input.
4. **Explainable decisions and conflict flags** for trust and governance.
5. **Final approved export + audit log** for downstream academic operations.

### 1.2 Primary Users and Roles

#### A) Academic Administrator (Primary)
- Uploads calendar and courses files.
- Reviews extracted constraints.
- Resolves flagged ambiguities.
- Generates draft schedule.
- Approves and exports final output.

#### B) Reviewer / Approver (Future Role)
- Reviews administrator decisions.
- Approves/rejects final schedule.
- Adds formal notes for compliance and traceability.

### 1.3 Inputs

1. **Academic Calendar File (Hebrew)**
   - Supported types: PDF, DOCX, TXT (phase 1), optional OCR for scanned PDFs (phase 2).
   - Contains semester dates, exam windows, holidays, closures, exceptional days.

2. **Courses File**
   - CSV/XLSX with course metadata and exam constraints.
   - Required columns defined in section 7.5.

3. **Manual Overrides**
   - User-set edits on extracted events.
   - Explicit rule exceptions (e.g., holiday is full block this year).
   - Final scheduling directives (hard constraints).

### 1.4 Outputs

1. **Structured Calendar Constraints** (machine-readable JSON + table view).
2. **Draft Exam Schedule** (per course: date, start/end time, room-set placeholder).
3. **Validation Flags** (data/logic issues requiring fix or acknowledgement).
4. **Review Notes** (who changed what and why).
5. **Final Approved Schedule** (CSV/XLSX/PDF + audit package).

---

## 2) Event Classification Model

Every extracted calendar event must be assigned one class:
- `semester_start`
- `semester_end`
- `exam_period`
- `exam_preparation_days`
- `university_closed`
- `partial_closure`
- `holiday`
- `limited_exam_window`
- `external_exam_block`
- `special_event`
- `manual_review_required`

### 2.1 Classification Semantics

- **semester_start / semester_end**: boundary anchors for academic periods.
- **exam_period**: date or date range where exams are generally allowed, including open-ended ranges.
- **exam_preparation_days**: pedagogic preparation periods, may constrain exam intensity.
- **university_closed**: full-day block (no exams).
- **partial_closure**: operating hours reduced (derive allowed exam window).
- **holiday**: cultural/religious holidays; defaults may apply (e.g., morning-only).
- **limited_exam_window**: explicit exam time restriction independent of full closure.
- **external_exam_block**: days/hours blocked due to external commitments (e.g., national events).
- **special_event**: important event with potential but uncertain effect.
- **manual_review_required**: unresolved ambiguity, unsupported pattern, or low-confidence extraction.

### 2.2 Multi-Label Handling

An item can map to one primary `event_type` plus secondary tags:
- Example: a holiday with explicit closure ⇒ primary `university_closed`, secondary tags `[holiday]`.
- The rule engine uses strongest constraint precedence (section 6).

---

## 3) Canonical Data Model

Use Python `pydantic` models (v2) for strict validation.

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date, time

class CalendarEvent(BaseModel):
    event_id: str
    event_name: str
    source_text: str
    source_section: Optional[str] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_range: bool = False
    is_open_ended: bool = False

    event_type: Literal[
        "semester_start", "semester_end", "exam_period", "exam_preparation_days",
        "university_closed", "partial_closure", "holiday", "limited_exam_window",
        "external_exam_block", "special_event", "manual_review_required"
    ]

    semester: Optional[Literal["A", "B", "Summer", "Unknown"]] = "Unknown"
    constraint_type: Literal["block", "limit", "informational", "review"]
    scheduling_relevance: Literal["high", "medium", "low"]

    block_scope: Literal["full", "partial", "none"] = "none"
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    allowed_exam_window: Optional[str] = None  # e.g. "08:00-13:00"

    affected_population: Optional[str] = "all"
    notes: Optional[str] = None

    requires_manual_review: bool = False
    confidence_score: float = Field(ge=0.0, le=1.0)

    # traceability
    parser_version: str
    classifier_version: str
    created_by: str = "system"
    updated_by: Optional[str] = None
```

### 3.1 Additional Operational Models

- `ManualOverride` (field, old_value, new_value, reason, user_id, timestamp)
- `CourseRecord`
- `ScheduleAssignment`
- `ConstraintViolation`
- `ApprovalRecord`
- `AuditEvent`

---

## 4) Business Rules (Mandatory Logic)

Implement as deterministic rules in `rule_engine` with priority order.

### 4.1 Rule Priorities

1. **Explicit override (human or explicit text)**
2. **Explicit full block in source**
3. **Explicit partial closure / limited window**
4. **Holiday defaults**
5. **General exam period defaults**

### 4.2 Required Rules

1. **Open-ended exam period support**
   - If end date missing and text implies continuation, set `is_open_ended=True`.
   - Allow overlap with next semester unless explicitly prohibited.

2. **Full block days**
   - `block_scope=full` => no exam slot generated.

3. **Partial block days**
   - Only slots inside computed `allowed_exam_window` remain.

4. **Closure at 18:00 implies exams until 13:00**
   - Map text like "האוניברסיטה תיסגר בשעה 18:00" to `allowed_exam_window=08:00-13:00`.

5. **Makeup teaching days**
   - If event classified as makeup/teaching compensation day: `allowed_exam_window=16:00-22:00`.

6. **Christian and Muslim holidays default**
   - Morning-only unless explicit override: default `08:00-13:00`.

7. **Ramadan default**
   - Morning-only `08:00-13:00`.

8. **Specific exceptions override defaults**
   - Example: if a holiday explicitly marked "no studies / no exams" then full block.
   - Override record must capture rationale and source line.

9. **Ambiguous cases**
   - If date/time semantics not resolved confidently, set `requires_manual_review=True`, `event_type=manual_review_required`, and exclude from automatic finalization until resolved.

### 4.3 Time Boundary Conventions

- Slot granularity: 30 minutes (configurable).
- Default exam durations: 2h / 3h, from course input.
- End boundary is exclusive (`[start, end)`).
- All timestamps in local campus timezone (Asia/Jerusalem).

---

## 5) UX Design Specification

## 5.1 Global UX Principles

- **Simple**: minimal steps, clear next action.
- **Transparent**: source Hebrew text always visible next to interpretation.
- **High trust**: explain "why" for every derived rule and placement.
- **Audit-first**: every edit leaves trace.

## 5.2 Screen 1 — Upload Calendar

### Purpose
Collect Hebrew calendar source and initiate extraction.

### Components
- Header: "Upload Academic Calendar (Hebrew)"
- Guidance text: accepted formats + Hebrew requirement.
- Drag-drop upload zone + browse button.
- CTA: `Extract Calendar Constraints`.
- Status area: upload progress, parse status, failure reasons.
- Preview panel placeholder (first extracted rows after success).

### States
- Empty
- Uploading
- Parse success (shows quick stats)
- Parse error (actionable error code + retry)

## 5.3 Screen 2 — Extraction Review

### Purpose
Human validation of semantic extraction before scheduling.

### Main table columns
- event_name
- event_type
- dates
- restriction type
- allowed hours
- notes
- confidence
- review flag

### Required features
- Inline editing for all mutable fields.
- Bulk actions (e.g., mark selected as full block).
- Filters: low confidence, unresolved reviews, semester, event type.
- Conflict highlighting (same date contradictory rules).
- Side drawer with source Hebrew text and parser/classifier rationale.
- Save as Draft / Mark Reviewed actions.

## 5.4 Screen 3 — Upload Courses

### Purpose
Validate course dataset before scheduling.

### Components
- Upload area for CSV/XLSX.
- Schema validator summary.
- Error grid: row number, column, issue, suggested fix.
- CTA: `Generate Draft Schedule` (disabled until no blocking errors).

## 5.5 Screen 4 — Draft Schedule

### Purpose
Present generated schedule with explainability.

### Components
- Calendar/timetable view and tabular list.
- Per exam row:
  - assigned date/time
  - applied constraints summary
  - "Why this slot" explanation
  - conflict indicator
- Filters by department/semester/date range.
- Actions: re-run with options, lock assignment, export draft.

## 5.6 Screen 5 — Approval & Export

### Purpose
Finalize schedule and produce outputs with audit trail.

### Components
- Final validation checklist.
- Approval action with digital signature fields (name/time/comment).
- Export options: CSV, XLSX, PDF, JSON.
- Audit timeline: extraction edits, rule overrides, schedule reruns, approvals.

---

## 6) Technical Architecture (Python)

## 6.1 High-Level Components

- `file_upload`: file intake, storage, type detection.
- `hebrew_text_normalizer`: Unicode normalization, punctuation/date token cleanup.
- `calendar_parser`: structure extraction (sections, lines, date/time entities).
- `semantic_classifier`: event type + confidence using rules + ML/NLP hybrid.
- `rule_engine`: converts events into executable scheduling constraints.
- `validation_engine`: checks data integrity and logical consistency.
- `review_editor`: CRUD for human edits and overrides.
- `course_ingestion`: parses/validates course data.
- `schedule_generator`: builds feasible slots and assigns exams.
- `export_module`: formatted outputs + audit package.

## 6.2 Suggested Stack

- Backend: FastAPI
- Data models: Pydantic
- DB: PostgreSQL (JSONB for traceable source fragments)
- Task queue: Celery + Redis (for heavy parsing/scheduling jobs)
- Frontend: React + TypeScript + MUI/Ant
- Auth: JWT/OIDC (institution SSO optional)
- Observability: structured logs + OpenTelemetry traces

## 6.3 API Endpoints (Minimum)

- `POST /calendar/upload`
- `POST /calendar/extract`
- `GET /calendar/events`
- `PATCH /calendar/events/{id}`
- `POST /calendar/overrides`
- `POST /courses/upload`
- `GET /courses/validation`
- `POST /schedule/generate`
- `GET /schedule/draft`
- `POST /schedule/approve`
- `GET /schedule/export?format=csv|xlsx|pdf|json`
- `GET /audit/logs`

## 6.4 Processing Flow

1. Upload calendar file.
2. Extract text + sections.
3. Normalize Hebrew + detect entities.
4. Classify events with confidence.
5. Validate + flag ambiguities.
6. Human review edits/overrides.
7. Upload/validate courses.
8. Generate candidate slots.
9. Apply constraints and assign exams.
10. Present draft with explanations/conflicts.
11. Approve + export + archive audit.

---

## 7) Parsing and Semantic Extraction Strategy

## 7.1 Hebrew Text Extraction

- PDF text layer extraction first (PyMuPDF/pdfplumber).
- OCR fallback (Tesseract Hebrew model) for scanned PDFs.
- Preserve line order and section hierarchy.

## 7.2 Hebrew Normalization Rules

- Unicode normalize (NFKC).
- Standardize punctuation and hyphen variants.
- Normalize Hebrew month names and abbreviations.
- Normalize numerals (Hebrew letters ↔ Arabic numerals when inferable).
- Standardize time format (`18:00`, `18.00`, `18` => canonical).

## 7.3 Entity Detection

Detect and link:
- single dates,
- date ranges,
- open-ended ranges (e.g., "עד להודעה"),
- times and time ranges,
- event descriptors,
- section labels (semester/holiday/exams context).

## 7.4 Semantic Classifier Design

Hybrid approach:
1. **Rule-based layer** for deterministic patterns and known phrases.
2. **Contextual NLP model** (Hebrew transformer or multilingual model) for ambiguous semantics.
3. **Confidence aggregator** combining:
   - phrase certainty,
   - date/time extraction quality,
   - section-context match,
   - historical correction similarity.

If confidence < threshold (e.g., 0.75) ⇒ `requires_manual_review=True`.

## 7.5 Courses File Schema (Required Columns)

- `course_id`
- `course_name`
- `department`
- `enrolled_count`
- `exam_duration_minutes`
- `exam_type` (written/oral/lab)
- `semester`
- `preferred_date_from` (optional)
- `preferred_date_to` (optional)
- `hard_blackout_dates` (optional list)
- `shared_students_group` (for clash prevention)
- `instructor_id` (optional for constraints)

Validation rules:
- unique `course_id`,
- positive duration,
- realistic enrollment,
- valid date formats,
- semester consistency with calendar year.

---

## 8) Rule Engine and Constraint Resolution

## 8.1 Constraint Object

Each event maps to one or more normalized constraints:
- `date_scope`
- `time_scope`
- `effect` (`allow_only`, `block`, `prefer`, `informational`)
- `precedence`
- `source_event_id`

## 8.2 Conflict Resolution

If constraints collide on same date:
1. explicit override
2. full block
3. partial window
4. morning-only default
5. permissive default

Generate conflict records when two equal-priority explicit constraints disagree.

## 8.3 Output to Scheduler

Rule engine produces an **availability matrix**:
- rows: date
- columns: time slots
- values: allowed/blocked/limited + reason codes.

---

## 9) Scheduling Engine Specification

## 9.1 Objectives

Hard constraints:
- no blocked slots,
- no student-group clashes,
- no instructor clashes (if provided),
- honor course hard blackout dates.

Soft constraints:
- spread exams for shared cohorts,
- avoid back-to-back heavy exams,
- respect preferred windows where possible.

## 9.2 Algorithm

Phase 1: generate feasible candidate slots per course.

Phase 2: assignment heuristic (recommended)
- sort courses by difficulty (largest enrollment + fewest feasible slots first),
- assign greedily with backtracking,
- if unresolved, run CP-SAT (OR-Tools) optimization fallback.

Phase 3: explanation generation
- attach top applied constraints and rejected alternatives.

## 9.3 Conflict Handling

When no feasible slot exists:
- mark `unscheduled`,
- provide blocking reasons ranked by impact,
- suggest minimal override candidates (e.g., extend one day to 16:00-18:00).

---

## 10) Validation Engine

## 10.1 Calendar Validation Checks

- missing start/end dates,
- invalid date ranges (end < start),
- open-ended without anchor context,
- contradictory overlap (full block and explicit allow-only),
- ambiguous language markers,
- unsupported patterns requiring parser extension.

## 10.2 Schedule Validation Checks

- exam outside allowed windows,
- overlap for shared student groups,
- excessive load per day (configurable),
- missing explanation metadata,
- unscheduled mandatory courses.

Severity levels:
- `error` (blocks approval),
- `warning` (approval allowed with acknowledgement),
- `info`.

---

## 11) Review, Approval, and Audit Trail

## 11.1 Review Workflow

1. System extraction complete.
2. Admin reviews flagged items first.
3. Admin edits and annotates decisions.
4. Re-validation must pass before scheduling.

## 11.2 Approval Controls

- Approval allowed only if no blocking errors.
- Approval record captures user, timestamp, summary hash.

## 11.3 Audit Requirements

Log every meaningful action:
- file upload,
- extraction run,
- event edit,
- override creation,
- schedule generation,
- approval/export.

Store immutable audit entries for compliance.

---

## 12) Development Plan (Milestones)

## Milestone 1 — App Scaffold + Upload

Deliverables:
- FastAPI service skeleton.
- React app with Screen 1.
- file storage and metadata table.
- basic healthcheck and auth stub.

Acceptance:
- Upload Hebrew PDF/TXT/DOCX.
- Job status visible.

## Milestone 2 — Calendar Parsing

Deliverables:
- text extraction pipeline,
- section detection,
- date/time entity extraction,
- normalized event candidates.

Acceptance:
- parses real sample calendar,
- >90% date extraction recall on benchmark set.

## Milestone 3 — Semantic Classification

Deliverables:
- classifier module,
- confidence scoring,
- manual-review flagging,
- event-type mapping.

Acceptance:
- correct event type for core patterns,
- low-confidence cases flagged.

## Milestone 4 — Review UI

Deliverables:
- Screen 2 full table,
- inline edits,
- conflict highlighting,
- override persistence.

Acceptance:
- edited records revalidate and persist.

## Milestone 5 — Course Ingestion

Deliverables:
- Screen 3,
- schema validator,
- row-level error UX.

Acceptance:
- invalid files rejected with actionable messages.

## Milestone 6 — Schedule Generator

Deliverables:
- rule engine + availability matrix,
- assignment engine,
- Screen 4 explanations,
- unscheduled conflict reporting.

Acceptance:
- schedules valid test dataset with zero hard violations.

## Milestone 7 — Approval, Export, QA Hardening

Deliverables:
- Screen 5,
- export module,
- end-to-end audit,
- regression suite and performance tuning.

Acceptance:
- full flow works from calendar upload to approved export.

---

## 13) Testing Strategy

## 13.1 Automated Tests

### Unit tests
- Hebrew normalization transformations.
- date range parsing incl. Hebrew formats.
- rule precedence behavior.
- business rules listed in section 4.

### Integration tests
- upload → parse → classify → review edit → schedule.
- exception overrides change slot availability.

### Property tests
- random overlapping constraints never allow blocked slot.

### Regression corpus
- real historical calendars,
- known ambiguous phrases,
- holiday exceptions.

## 13.2 Required Test Scenarios

1. Hebrew parsing edge forms (abbrev months, mixed numerals).
2. Ambiguous text needing manual review.
3. Overlapping constraints with precedence.
4. Christian/Muslim holiday default vs explicit full-block override.
5. Ramadan morning-only enforcement.
6. Open-ended exam period crossing semester boundary.

## 13.3 Non-Functional Tests

- Performance: schedule generation under 5 min for N=2,000 courses.
- Reliability: retryable parsing jobs and idempotent runs.
- Security: file type enforcement, malware scan hook, access control.
- Observability: trace coverage for each pipeline stage.

---

## 14) Risks, Hidden Assumptions, Missing Requirements, and Improvements (QA Critique)

## 14.1 Key Risks

1. **Hebrew OCR quality risk** on scanned/low-quality PDFs.
2. **Semantic ambiguity risk** where source text is policy-like rather than explicit.
3. **Policy drift risk** when institution changes rules mid-year.
4. **Data quality risk** in courses file (missing groups or bad dates).
5. **Optimization complexity risk** with many clashes and few available slots.

## 14.2 Hidden Assumptions to Surface

- Single campus timezone and operating hours.
- Uniform exam slot length assumptions.
- Holiday defaults apply universally unless overridden.
- Course file includes enough student-group data to prevent clashes.
- Semester identifiers in calendar and courses are aligned.

## 14.3 Missing Requirements (Should Be Added)

1. Room/resource constraints (capacity, accessibility, labs).
2. Multiple exam sessions (first call / second call / makeup exam cycles).
3. Faculty-level blackout windows.
4. Versioning and rollback for approved schedules.
5. Notification workflow to stakeholders after approval.
6. API contract for SIS/LMS integration.

## 14.4 Additional Validation Rules

- Disallow approval if any event has `requires_manual_review=true` unresolved.
- Validate no exam starts before campus opening or ends after closure.
- Detect suspiciously long exams (e.g., >6h) unless explicitly allowed.
- Detect same course assigned multiple overlapping exams.
- Verify exception overrides have mandatory reason text.

## 14.5 Critical Edge Cases

- Event text contains two separate dates in one sentence with different constraints.
- Date ranges spanning Gregorian year boundary.
- Holidays beginning at sunset with next-day effects.
- Partial closure overlapping morning-only holiday.
- Open-ended exam period revoked later by addendum document.
- Duplicated or contradictory entries across calendar sections.

## 14.6 Practical Improvements

- Add "policy templates" per institution/year.
- Add active-learning loop: user corrections improve classifier.
- Add "impact simulator" for manual overrides before apply.
- Add bilingual display (Hebrew source + English interpretation).
- Add deterministic replay mode for audits.

---

## 15) Implementation Blueprint (Concrete Package Layout)

```text
exam_scheduler/
  app/
    main.py
    api/
      calendar.py
      courses.py
      schedule.py
      approval.py
    core/
      config.py
      logging.py
    models/
      calendar_event.py
      course.py
      schedule.py
      audit.py
    services/
      file_upload.py
      hebrew_text_normalizer.py
      calendar_parser.py
      semantic_classifier.py
      rule_engine.py
      validation_engine.py
      review_editor.py
      course_ingestion.py
      schedule_generator.py
      export_module.py
    repositories/
      calendar_repo.py
      course_repo.py
      schedule_repo.py
      audit_repo.py
  tests/
    unit/
    integration/
    regression/
  web/
    src/
      screens/
        UploadCalendar.tsx
        ExtractionReview.tsx
        UploadCourses.tsx
        DraftSchedule.tsx
        Approval.tsx
```

---

## 16) Done Criteria (Production Readiness)

System is considered production-ready only when:
1. End-to-end flow is operational with real Hebrew calendar files.
2. All mandatory business rules in section 4 are test-covered and passing.
3. Manual review loop is fully functional with auditable changes.
4. Schedule explanations are visible for each assignment.
5. Approval/export/audit pipeline passes UAT with administrators.
6. Monitoring and rollback procedures are documented.

This specification is intentionally implementation-oriented and can be directly converted into backlog epics, engineering tasks, and QA test plans.
