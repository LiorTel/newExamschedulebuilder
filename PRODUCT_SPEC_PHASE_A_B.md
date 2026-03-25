# Academic Exam Scheduling System — Product Specification (Phase A & Phase B)

## 1) Product Purpose

### 1.1 Why this system exists
Universities and colleges often manage exam scheduling with fragmented processes: manual interpretation of academic calendars, spreadsheet-based planning, and ad hoc exception handling. This system exists to transform that workflow into a structured, auditable, and semi-automated pipeline.

### 1.2 Pain points solved
- **Manual interpretation of Hebrew calendar text** causes inconsistency and delays.
- **Hidden constraints** (partial closures, special events, religious holidays, Ramadan windows) are easy to miss.
- **Ambiguity in policy meaning** leads to scheduling disputes and late corrections.
- **Lack of transparent traceability** makes it hard to justify why a date/time was or was not used.

### 1.3 Expected output
The system produces:
1. A **structured, reviewable calendar constraints model** extracted from the Hebrew academic calendar.
2. A **draft exam schedule** generated from course metadata + approved calendar constraints.
3. **Validation flags and review notes** for uncertain or conflicting cases.
4. An **approved final schedule** with auditable decision history.

---

## 2) User Roles

### 2.1 Primary role (MVP)
- **Academic Administrator / Exam Coordinator**
  - Uploads files
  - Reviews extracted constraints
  - Edits classifications/interpretations
  - Approves calendar constraints
  - Triggers schedule generation
  - Reviews and finalizes schedule

### 2.2 Optional future roles
- **Reviewer**: can comment and propose corrections; cannot approve final output.
- **Approver**: can sign off approved constraints/schedule.
- **Department Admin**: can view/filter only department-relevant courses and constraints.

---

## 3) Inputs

### 3.1 Academic calendar file (Phase A)
- Primary source document in Hebrew.
- Supported formats (target): PDF, DOCX, XLSX, CSV, TXT (implementation may start with subset).
- Contains dates, date ranges, times, period labels, holidays, and operational notes.

### 3.2 Courses file (Phase B)
- Structured file (CSV/XLSX/API payload).
- Contains course metadata and exam requirements.

### 3.3 Optional manual overrides
- Administrator-entered edits/additions:
  - Add missing event
  - Adjust interpretation
  - Override default policy for specific date/event
  - Lock decisions prior to scheduling

---

## 4) Outputs

1. **Structured extracted calendar constraints** (machine-readable records).
2. **Exam schedule draft** (course-to-date/time assignment proposal).
3. **Validation flags** (ambiguity, missing data, conflicts, impossible ranges).
4. **Review notes** (human annotations and rationale).
5. **Approved final schedule** (exportable and auditable).

---

## 5) Functional Requirements

### 5.1 File ingestion
- Upload academic calendar file.
- Upload courses file.
- Validate file type, encoding, and parse readiness.

### 5.2 Hebrew parsing and extraction
- Parse Hebrew right-to-left text.
- Detect Hebrew dates (including Hebrew month/day expressions where present).
- Detect date ranges and open-ended periods.
- Detect times and time windows.
- Detect event descriptions and qualifying clauses.

### 5.3 Semantic classification
- Classify each extracted item into event categories (Section 6).
- Infer scheduling meaning (full block / partial block / limited window / informational).
- Distinguish default policy vs explicit exception.

### 5.4 Structured storage
- Persist each extracted event in structured schema (Section 7).
- Preserve source evidence (exact source text).
- Track confidence and review status.

### 5.5 Validation and flagging
- Run validation checks (Section 9).
- Generate warnings/errors and review flags.
- Route uncertain items to manual review queue.

### 5.6 Review and approval workflow
- Show review table with source text + interpreted constraint.
- Allow edits before approval.
- Require explicit approval of Phase A output before enabling Phase B scheduling.

### 5.7 Schedule generation (Phase B)
- Match course exam requirements to approved allowed windows.
- Apply blocked dates and partial-day restrictions.
- Generate schedule draft with conflict checks.
- Flag unresolved/unschedulable courses.

### 5.8 Export
- Export extracted constraints, review logs, and final schedule (CSV/XLSX/PDF/API JSON).

---

## 6) Event Classification Model

Each extracted item must map to one of the following categories (or be flagged for manual review):

- `semester_start`
- `semester_end`
- `exam_period`
- `exam_preparation_days`
- `no_classes`
- `university_closed`
- `partial_closure`
- `holiday`
- `external_exam_block`
- `limited_exam_window`
- `special_academic_event`
- `manual_review_required`

### 6.1 Classification behavior
- One source sentence may yield **multiple classified events**.
- A classified event may include both category and operational constraint tags.
- If category confidence is below threshold, assign provisional class and mark `manual_review_required`.

---

## 7) Required Data Model for Extracted Events

Each extracted event record must include:

- `event_id` (system-generated)
- `event_name`
- `source_text`
- `source_location` (page/row/section where available)
- `start_date`
- `end_date`
- `is_range` (boolean)
- `is_open_ended` (boolean)
- `event_type` (from classification model)
- `semester` (e.g., A/B/Summer/Unknown)
- `constraint_type` (e.g., block_full, block_partial, allow_limited, info_only)
- `scheduling_relevance` (high/medium/low + reason)
- `block_scope` (full_day, partial_day, specific_window, population_specific)
- `start_time`
- `end_time`
- `allowed_exam_window` (e.g., 08:00-13:00, 16:00-21:00)
- `affected_population` (all students / faculty / specific groups)
- `notes`
- `requires_manual_review` (boolean)
- `confidence_score` (0.0–1.0)
- `rule_origin` (deterministic_rule / semantic_inference / manual_override)
- `created_at`, `updated_at`, `approved_at`
- `approved_by`

### 7.1 Derived fields for scheduling engine
- `effective_constraint_priority`
- `exception_of_event_id` (for overrides)
- `normalized_date_key` (calendar system normalization)

---

## 8) Business Rules and Semantic Rules

### 8.1 Core policy rules (mandatory)
1. **Exam periods may be open-ended** and may overlap beginning of next semester.
2. Some dates **fully block exams**.
3. Some dates **partially block exams**.
4. If university closes at **18:00**, exams may only be scheduled **until 13:00**.
5. On **makeup teaching days**, exams may only be scheduled from **16:00 onward**.
6. On holidays of other religious communities (e.g., Christianity/Islam), exams are **morning-only by default**.
7. Specific exceptions (e.g., Christmas / Sigd / explicitly defined dates) may be **full block** or have unique rules.
8. During **Ramadan**, exams are **morning-only**.
9. System must distinguish **defaults** vs **explicit exceptions**.
10. Ambiguous meanings must preserve explanatory **notes**.
11. Low semantic certainty must set `requires_manual_review = true`.

### 8.2 Rule precedence
From highest to lowest:
1. Manual override approved by authorized user.
2. Explicit date-level exception in source.
3. Explicit period-level rule in source.
4. Institutional default rule set.
5. Semantic inference fallback.

### 8.3 Constraint interpretation logic
- If an event states closure or inability to hold exams → `block_full` unless specific hours provided.
- If closure/end-of-activity time exists (e.g., 18:00) → translate into exam-allowed cutoff rule per policy.
- If “no classes” is declared, do **not** automatically block exams; classify based on policy mapping and mark uncertain cases for review.
- If multiple constraints appear in same sentence, split into separate event records linked by shared source pointer.

---

## 9) Validation Requirements

System must detect and flag:

1. **Missing dates**
   - Event name exists but no parseable date.
2. **Conflicting interpretations**
   - Same date marked both full block and allowed full-day.
3. **Impossible/incomplete ranges**
   - End date before start date.
   - Range marker without end date and without open-ended marker.
4. **Ambiguous Hebrew phrases**
   - Terms with multiple policy interpretations.
5. **Partially classified scheduling-impact items**
   - Date extracted but missing `constraint_type`.
6. **Temporal overlap contradictions**
   - Exception rule not mapped over parent default.

### 9.1 Validation output model
- `validation_id`
- `severity` (error/warning/info)
- `event_id` (nullable)
- `message`
- `suggested_resolution`
- `requires_manual_review`
- `resolved_by`, `resolved_at`

---

## 10) UX Requirements

### 10.1 Phase A review experience
- Review table with columns:
  - Source text (Hebrew)
  - Extracted dates/times
  - Classification
  - Scheduling meaning
  - Confidence
  - Validation flags
  - Review status
- Side-by-side visibility: **original source vs interpreted record**.
- Inline editing for classification and constraint fields.
- Ability to add review notes and rationale.

### 10.2 Approval gating
- “Approve Calendar Constraints” action is blocked until all errors resolved or explicitly accepted.
- Phase B scheduling is disabled until Phase A is approved.

### 10.3 Traceability UX
- Every schedule decision should be drill-downable to underlying constraints and source evidence.

---

## 11) Phase B Scheduling Requirements

### 11.1 Inputs to scheduling engine
- Approved constraints from Phase A:
  - Allowed exam dates
  - Blocked dates
  - Partial-day restrictions
  - Exceptions/default policies
- Course metadata from courses file.

### 11.2 Minimum required course metadata
- `course_id`
- `course_name`
- `department`
- `student_count` (or size band)
- `exam_type` (regular/makeup/final/etc.)
- `preferred_period` (if provided)
- `duration_minutes`
- `special_requirements` (if any)
- `population_constraints` (if cross-listed / program-specific)

### 11.3 Scheduling algorithm behavior (functional)
1. Build candidate slots from allowed dates + allowed windows.
2. Remove full-block dates and disallowed windows.
3. Apply partial restrictions and exception precedence.
4. Rank feasible slots by policy/objective function (e.g., fairness, load balancing, spacing).
5. Assign courses iteratively with conflict checks.
6. Mark unassigned courses with reason codes.

### 11.4 Conflict checks
- Course-level conflicts (same cohort, same instructor if available).
- Capacity/time-window conflicts.
- Violations of partial-day limits.
- Violations of holiday/Ramadan/special-event constraints.

### 11.5 Output of Phase B
- Draft schedule table.
- Conflict/exception report.
- Confidence and constraint provenance for each assignment.
- Editable schedule prior to final approval.

---

## 12) Non-Functional Requirements

### 12.1 Hebrew reliability
- Robust UTF-8 handling.
- RTL-aware parsing/display.
- Hebrew date tokenization and normalization.

### 12.2 Auditability
- Full trace from schedule entry → constraint record → source text.
- Immutable audit log for approvals and overrides.

### 12.3 Hybrid reasoning architecture
- **Deterministic rule layer** for policy enforcement.
- **Semantic interpretation layer** for extracting meaning from natural language.
- Deterministic layer always enforces final legality constraints.

### 12.4 Transparency and reviewability
- Explainable classification outcomes.
- Confidence score visibility.
- Manual-review workflow for uncertain interpretations.

### 12.5 Extensibility
- Add new event types without schema breakage.
- Add institution-specific policies via configuration.
- Multi-language expansion support in future.

---

## 13) Edge Cases

System must explicitly handle:

1. **Date range without explicit end meaning**
   - e.g., starts on date X with “until further notice” semantics.
2. **One sentence containing multiple constraints**
   - e.g., closure + makeup instruction + limited exam window.
3. **Events that stop classes but do not fully block exams**
   - maintain separate interpretation path.
4. **Holidays affecting only certain time windows**
   - e.g., morning-only or afternoon-only rules.
5. **Overlap between holiday periods and exam periods**
   - apply precedence and exception logic.
6. **Ambiguous section headers in source file**
   - classify with low confidence + manual review flag.
7. **Cross-semester overlaps**
   - exam period extending into next semester.
8. **Population-specific constraints**
   - constraints applying only to subset of students.

---

## 14) Phase Scope Definition

### 14.1 Phase A (Ingestion → Approved constraints)
In scope:
- Academic calendar upload
- Hebrew extraction and normalization
- Semantic classification
- Validation and flagging
- Manual review/edit
- Approval workflow
- Export of approved constraints

Out of scope:
- Final automated course scheduling decisions
- Resource/room optimization (unless added later)

### 14.2 Phase B (Courses ingestion → Draft schedule)
In scope:
- Course file upload/validation
- Constraint-aware exam slot generation
- Draft schedule + conflict reporting
- Manual adjustment and final approval
- Export final schedule

Out of scope (initially):
- Advanced optimization across rooms/proctors/campuses (future extension)

---

## 15) End-to-End System Logic (Explicit)

1. User uploads Hebrew academic calendar.
2. System parses text and extracts candidate events.
3. System normalizes dates/times and builds event records.
4. System classifies event type + scheduling meaning.
5. Rule engine applies defaults/exceptions and builds effective constraints.
6. Validator flags missing/conflicting/ambiguous items.
7. User reviews, edits, and approves Phase A constraints.
8. User uploads course file.
9. Scheduler generates feasible slots and assigns exams.
10. System surfaces conflicts, exceptions, and unscheduled items.
11. User reviews/edits and approves final schedule.
12. System exports final outputs and audit logs.

---

## 16) Acceptance Criteria (High-Level)

### Phase A acceptance
- ≥95% of clearly stated calendar dates are extracted into structured records.
- All low-confidence items are flagged for manual review.
- No Phase B run can start without explicit Phase A approval.

### Phase B acceptance
- All generated assignments comply with approved hard constraints.
- Every scheduled exam has traceable provenance to applied constraints.
- Conflict report generated for every draft run.

---

## 17) Implementation Notes (Non-code)

- Use configurable policy tables to separate institution rules from extraction logic.
- Preserve original Hebrew fragments verbatim in `source_text` for legal/audit defensibility.
- Keep semantic interpretation explainable (rule hit list + confidence factors).

