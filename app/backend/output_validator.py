"""
Deterministic output validation for the ClearSpec AI pipeline.

This module validates the visible Markdown returned by the three AI stages:

- stories
- gap
- trace

It uses only Python's standard library.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Literal
from trace_semantic_validator import validate_trace_semantics


StageName = Literal["stories", "gap", "trace"]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


@dataclass
class ValidationResult:
    stage: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(
        self,
        code: str,
        message: str,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
            )
        )

    def formatted_issues(self) -> str:
        if self.ok:
            return "No validation issues."

        return "\n".join(
            f"{index}. [{issue.code}] {issue.message}"
            for index, issue in enumerate(
                self.issues,
                start=1,
            )
        )


_ALLOWED_RISK_STATUSES = {
    "OPEN",
    "ASSUMED",
    "BLOCKED",
    "PROPOSED",
    "CONFIRMED",
}


# ============================================================
# COMMON HELPERS
# ============================================================


def _has_heading(
    text: str,
    title: str,
) -> bool:
    pattern = (
        rf"(?im)^#{{1,4}}\s*"
        rf"(?:\d+\.\s*)?"
        rf"{re.escape(title)}\s*$"
    )

    return re.search(pattern, text) is not None


def _extract_section(
    text: str,
    heading_title: str,
) -> str:
    pattern = (
        rf"(?ims)^#{{1,4}}\s*"
        rf"(?:\d+\.\s*)?"
        rf"{re.escape(heading_title)}\s*$"
        rf"(.*?)"
        rf"(?=^#{{1,4}}\s|\Z)"
    )

    match = re.search(pattern, text)

    if not match:
        return ""

    return match.group(1).strip()


def _split_story_blocks(
    text: str,
) -> list[str]:
    matches = list(
        re.finditer(
            r"(?im)^##\s+Story\s+\d+\s*:",
            text,
        )
    )

    if not matches:
        return []

    blocks: list[str] = []

    for index, match in enumerate(matches):
        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        blocks.append(
            text[start:end].strip()
        )

    return blocks


def _contains_given_when_then(
    block: str,
) -> bool:
    return all(
        re.search(
            rf"(?i)\b{word}\b",
            block,
        )
        for word in (
            "Given",
            "When",
            "Then",
        )
    )


# ============================================================
# STORIES VALIDATION
# ============================================================


def _validate_stories(
    text: str,
) -> ValidationResult:
    result = ValidationResult(
        stage="stories"
    )

    if len(text.strip()) < 350:
        result.add(
            "STORIES_TOO_SHORT",
            (
                "The Stories response is too short to contain "
                "complete user stories."
            ),
        )

    if not _has_heading(
        text,
        "User Stories",
    ):
        result.add(
            "STORIES_TITLE_MISSING",
            (
                "The response must start with a "
                "'# User Stories' heading."
            ),
        )

    story_blocks = _split_story_blocks(text)

    if not story_blocks:
        result.add(
            "STORY_BLOCK_MISSING",
            (
                "At least one '## Story N:' block "
                "is required."
            ),
        )

        return result

    for index, block in enumerate(
        story_blocks,
        start=1,
    ):
        label = f"Story {index}"

        if not re.search(
            r"(?im)^"
            r"\*{0,2}"
            r"As\s+an?"
            r"\*{0,2}"
            r"\s+.+$",
            block,
        ):
            result.add(
                "STORY_ACTOR_MISSING",
                (
                    f"{label} must contain an "
                    "'As a' or 'As an' actor statement."
                ),
            )

        if not re.search(
            r"(?im)^"
            r"\*{0,2}"
            r"I\s+want"
            r"\*{0,2}"
            r"\s+.+$",
            block,
        ):
            result.add(
                "STORY_GOAL_MISSING",
                (
                    f"{label} must contain an "
                    "'I want' capability statement."
                ),
            )

        if not re.search(
            r"(?im)^"
            r"\*{0,2}"
            r"So\s+that"
            r"\*{0,2}"
            r"\s+.+$",
            block,
        ):
            result.add(
                "STORY_VALUE_MISSING",
                (
                    f"{label} must contain a "
                    "'So that' value statement."
                ),
            )

        if not re.search(
            r"(?im)^#{2,4}\s+"
            r"Acceptance Criteria\s*$",
            block,
        ):
            result.add(
                "STORY_AC_HEADING_MISSING",
                (
                    f"{label} must contain an "
                    "Acceptance Criteria heading."
                ),
            )

        if not _contains_given_when_then(
            block
        ):
            result.add(
                "STORY_GWT_MISSING",
                (
                    f"{label} must contain measurable "
                    "Given/When/Then criteria."
                ),
            )

        if not re.search(
            r"(?im)^"
            r"\*{0,2}"
            r"Priority:"
            r"\*{0,2}"
            r"\s*P[0-3]\s*$",
            block,
        ):
            result.add(
                "STORY_PRIORITY_INVALID",
                (
                    f"{label} must contain Priority: "
                    "P0, P1, P2, or P3."
                ),
            )

        if not re.search(
            r"(?im)^"
            r"\*{0,2}"
            r"Estimate:"
            r"\*{0,2}"
            r"\s*(?:XS|S|M|L|XL)\s*$",
            block,
        ):
            result.add(
                "STORY_ESTIMATE_INVALID",
                (
                    f"{label} must contain Estimate: "
                    "XS, S, M, L, or XL."
                ),
            )

        if not re.search(
            r"(?im)^#{2,4}\s+"
            r"Assumptions\s*$",
            block,
        ):
            result.add(
                "STORY_ASSUMPTIONS_MISSING",
                (
                    f"{label} must contain an "
                    "Assumptions section."
                ),
            )

        else:
            assumptions = _extract_section(
                block,
                "Assumptions",
            )

            if (
                assumptions
                and "None identified" not in assumptions
                and "[ASSUMED]" not in assumptions
            ):
                result.add(
                    "STORY_ASSUMPTION_TAG_MISSING",
                    (
                        f"{label} contains assumptions "
                        "that are not marked [ASSUMED]."
                    ),
                )

        if not re.search(
            r"(?im)^#{2,4}\s+"
            r"Open Questions\s*$",
            block,
        ):
            result.add(
                "STORY_OPEN_QUESTIONS_MISSING",
                (
                    f"{label} must contain an "
                    "Open Questions section."
                ),
            )

    return result


# ============================================================
# GAP ANALYSIS VALIDATION
# ============================================================


def _validate_gap(
    text: str,
) -> ValidationResult:
    result = ValidationResult(
        stage="gap"
    )

    if len(text.strip()) < 900:
        result.add(
            "GAP_TOO_SHORT",
            (
                "The Gap Analysis is too short for "
                "the mandatory analysis sections."
            ),
        )

    required_headings = (
        "Gap & Conflict Analysis",
        "Contradictions",
        "Ambiguities and Feasibility Risks",
        "Vague or Unmeasurable Terms",
        "Missing Functional Requirements",
        "Missing Edge Cases",
        "Security, Privacy, and Compliance Concerns",
        "Non-Functional Requirements Missing",
        "Open Questions for Stakeholders",
        "Recommended Story Improvements",
        "Risk Score",
    )

    for heading in required_headings:
        if not _has_heading(
            text,
            heading,
        ):
            result.add(
                "GAP_SECTION_MISSING",
                (
                    "Missing required Gap Analysis "
                    f"heading: '{heading}'."
                ),
            )

    risk_section = _extract_section(
        text,
        "Risk Score",
    )

    # Use the whole response as a fallback when the model formats
    # the Risk Score section differently from the expected heading.
    risk_source = risk_section or text

    risk_score_match = re.search(
        r"(?im)"
        r"^\s*"
        r"(?:[-*]\s*)?"
        r"\*{0,2}"
        r"(?:Overall(?:\s+Risk)?|Risk\s+Level)"
        r"\s*:"
        r"\*{0,2}"
        r"\s*"
        r"\*{0,2}"
        r"(LOW|MEDIUM|HIGH|CRITICAL)"
        r"\*{0,2}"
        r"\b",
        risk_source,
    )

    if not risk_score_match:
        result.add(
            "GAP_RISK_SCORE_INVALID",
            (
                "Risk Score must include Overall: "
                "LOW, MEDIUM, HIGH, or CRITICAL."
            ),
        )

    recommendation_match = re.search(
        r"(?im)"
        r"^\s*"
        r"(?:[-*]\s*)?"
        r"\*{0,2}"
        r"Implementation\s+recommendation"
        r"\s*:"
        r"\*{0,2}"
        r"\s*"
        r"\*{0,2}"
        r"(PROCEED WITH CONDITIONS|"
        r"BLOCK UNTIL CLARIFIED|"
        r"PROCEED)"
        r"\*{0,2}"
        r"\b",
        risk_source,
    )

    if not recommendation_match:
        result.add(
            "GAP_RECOMMENDATION_INVALID",
            (
                "Risk Score must include a valid "
                "implementation recommendation."
            ),
        )

    ambiguity_section = _extract_section(
        text,
        "Ambiguities and Feasibility Risks",
    )

    contradictions_section = _extract_section(
        text,
        "Contradictions",
    )

    if (
        re.search(
            r"(?i)"
            r"No direct contradictions identified",
            contradictions_section,
        )
        and re.search(
            r"(?i)\bcontradicts?\b",
            ambiguity_section,
        )
    ):
        result.add(
            "GAP_CONTRADICTION_CLASSIFICATION",
            (
                "The response says no direct contradictions "
                "exist but labels an ambiguity item as a "
                "contradiction."
            ),
        )

    unsupported_regulation_patterns = (
        r"(?i)\bHIPAA compliance\b",
        r"(?i)\bGDPR compliance\b",
        r"(?i)\bPCI[- ]DSS compliance\b",
        r"(?i)\bSOX compliance\b",
    )

    for pattern in unsupported_regulation_patterns:
        match = re.search(
            pattern,
            text,
        )

        if not match:
            continue

        nearby = text[
            max(
                0,
                match.start() - 120,
            ):
            match.end() + 120
        ]

        if not re.search(
            r"(?i)"
            r"\[OPEN QUESTION\]|"
            r"if applicable|"
            r"applicable law|"
            r"confirm whether",
            nearby,
        ):
            result.add(
                "GAP_UNCONFIRMED_REGULATION",
                (
                    "A named regulation is presented as "
                    "applicable without being framed as "
                    "an open compliance question."
                ),
            )

            break

    return result


# ============================================================
# TECHNICAL TRACE VALIDATION
# ============================================================


def _extract_sql_blocks(
    text: str,
) -> list[str]:
    return re.findall(
        r"(?is)```sql\s*(.*?)```",
        text,
    )


def _validate_uuid_examples(
    text: str,
    result: ValidationResult,
) -> None:
    candidates = re.findall(
        r"(?i)"
        r"(?<![A-Za-z0-9])"
        r"[A-Za-z0-9]{8}-"
        r"[A-Za-z0-9]{4}-"
        r"[A-Za-z0-9]{4}-"
        r"[A-Za-z0-9]{4}-"
        r"[A-Za-z0-9]{12}"
        r"(?![A-Za-z0-9])",
        text,
    )

    for candidate in candidates:
        try:
            uuid.UUID(candidate)

        except ValueError:
            result.add(
                "TRACE_INVALID_UUID_EXAMPLE",
                (
                    "Invalid UUID example detected: "
                    f"'{candidate}'."
                ),
            )


def _validate_risk_statuses(
    text: str,
    result: ValidationResult,
) -> None:
    section = _extract_section(
        text,
        "Technical Risks and Decisions",
    )

    if not section:
        return

    for line in section.splitlines():
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        cells = [
            cell.strip()
            for cell in stripped.strip("|").split("|")
        ]

        if len(cells) < 2:
            continue

        final_cell = cells[-1].upper()

        if final_cell in {
            "STATUS",
            "---",
            "",
        }:
            continue

        if final_cell and set(final_cell) == {"-"}:
            continue

        if final_cell not in _ALLOWED_RISK_STATUSES:
            result.add(
                "TRACE_RISK_STATUS_INVALID",
                (
                    "Invalid risk status "
                    f"'{cells[-1]}'."
                ),
            )


def _validate_trace(
    text: str,
    source_text: str = "",
) -> ValidationResult:
    result = ValidationResult(
        stage="trace"
    )

    if len(text.strip()) < 1500:
        result.add(
            "TRACE_TOO_SHORT",
            (
                "The Technical Trace is too short for "
                "the mandatory technical artifacts."
            ),
        )

    required_headings = (
        "Technical Traceability Artifacts",
        "Scope, Assumptions, and Open Questions",
        "Story-to-Artifact Traceability Matrix",
        "Domain Model",
        "PostgreSQL Schema Changes",
        "REST API Endpoints",
        "Representative Payloads",
        "Core Logic Pseudocode",
        "Background Jobs and Event Processing",
        "Security, Privacy, and Reliability Controls",
        "Test and Implementation Plan",
        "Technical Risks and Decisions",
    )

    for heading in required_headings:
        if not _has_heading(
            text,
            heading,
        ):
            result.add(
                "TRACE_SECTION_MISSING",
                (
                    "Missing required Technical Trace "
                    f"heading: '{heading}'."
                ),
            )

    exact_disclaimer = (
        "> AI-generated design proposal — "
        "validate before implementation."
    )

    if not text.rstrip().endswith(
        exact_disclaimer
    ):
        result.add(
            "TRACE_DISCLAIMER_MISSING",
            (
                "The Technical Trace must end with "
                "the exact validation disclaimer."
            ),
        )

    confirmed_section = _extract_section(
        text,
        "Confirmed Requirements",
    )

    if (
        "[ASSUMED]" in confirmed_section
        or "[OPEN QUESTION]" in confirmed_section
    ):
        result.add(
            "TRACE_CONFIRMED_SECTION_CONTAMINATED",
            (
                "Confirmed Requirements contains an "
                "assumption or open question."
            ),
        )

    sql_blocks = _extract_sql_blocks(text)

    if not sql_blocks:
        result.add(
            "TRACE_SQL_BLOCK_MISSING",
            (
                "A fenced PostgreSQL SQL block "
                "is required."
            ),
        )

    else:
        combined_sql = "\n".join(
            sql_blocks
        )

        if not re.search(
            r"(?i)"
            r"CREATE\s+EXTENSION\s+"
            r"IF\s+NOT\s+EXISTS\s+"
            r"\"?pgcrypto\"?",
            combined_sql,
        ):
            result.add(
                "TRACE_PGCRYPTO_MISSING",
                (
                    "PostgreSQL DDL using "
                    "gen_random_uuid() must include "
                    "the pgcrypto extension."
                ),
            )

        if not re.search(
            r"(?i)CREATE\s+TABLE\b",
            combined_sql,
        ):
            result.add(
                "TRACE_TABLE_DDL_MISSING",
                (
                    "The PostgreSQL section must "
                    "contain at least one CREATE TABLE."
                ),
            )

        if re.search(
            r"(?im)^\s*INDEX\s+\w+\s*\(",
            combined_sql,
        ):
            result.add(
                "TRACE_MYSQL_INLINE_INDEX",
                (
                    "MySQL-style inline INDEX syntax "
                    "was found inside PostgreSQL DDL."
                ),
            )

        if not re.search(
            r"(?i)"
            r"CREATE\s+"
            r"(?:UNIQUE\s+)?"
            r"INDEX\b",
            combined_sql,
        ):
            result.add(
                "TRACE_INDEX_DDL_MISSING",
                (
                    "Indexes must be emitted as "
                    "separate CREATE INDEX statements."
                ),
            )

        if (
            re.search(
                r"(?i)\bidempotency_key\b",
                text,
            )
            and not re.search(
                r"(?i)\bidempotency_key\b",
                combined_sql,
            )
        ):
            result.add(
                "TRACE_IDEMPOTENCY_NOT_PERSISTED",
                (
                    "Idempotency is described but no "
                    "idempotency_key is persisted in "
                    "the schema."
                ),
            )

        if (
            re.search(
                r"(?i)\bcritical_threshold",
                text,
            )
            and not re.search(
                r"(?i)"
                r"CREATE\s+TABLE\s+"
                r"critical_threshold",
                combined_sql,
            )
            and (
                "external clinical-rule service"
                not in text.lower()
            )
        ):
            result.add(
                "TRACE_THRESHOLD_ARTIFACT_MISSING",
                (
                    "Critical-threshold validation is "
                    "referenced without a schema artifact "
                    "or explicit external rule service."
                ),
            )

    forbidden_patterns = (
        (
            "TRACE_DYNAMIC_ORDER_BY",
            r"(?is)"
            r"ORDER\s+BY\s*"
            r"[\"']?\s*\+",
            (
                "Dynamic ORDER BY concatenation "
                "was found."
            ),
        ),
        (
            "TRACE_NULL_NOTIFICATION",
            r"(?i)"
            r"create\s+notification"
            r"\s*\(\s*null\s*\)",
            (
                "The workflow creates a notification "
                "with null required data."
            ),
        ),
        (
            "TRACE_WRONG_IDEMPOTENCY_SCOPE",
            r"(?i)"
            r"exists\s+notification\s+where\s+"
            r"idempotency_key",
            (
                "Ingestion idempotency is checked "
                "against notifications instead of the "
                "ingested result or ingestion request."
            ),
        ),
        (
            "TRACE_SENSITIVE_IDENTIFIER_CLAIM",
            r"(?i)"
            r"\bnon-sensitive internal reference\b",
            (
                "A pseudonymous patient identifier "
                "is incorrectly described as "
                "non-sensitive."
            ),
        ),
        (
            "TRACE_PG_ENCRYPTION_CLAIM",
            r"(?i)\bPG encryption at rest\b",
            (
                "PostgreSQL is incorrectly presented "
                "as automatically providing storage "
                "encryption."
            ),
        ),
    )

    for (
        code,
        pattern,
        message,
    ) in forbidden_patterns:
        if re.search(
            pattern,
            text,
        ):
            result.add(
                code,
                message,
            )

    if (
        re.search(
            r"(?i)\bserver_validate_critical\b",
            text,
        )
        and re.search(
            r"(?i)\bcreate\s+notification\b",
            text,
        )
        and not re.search(
            r"(?is)"
            r"\bif\s+"
            r"(?:"
            r"is_crit|"
            r"is_critical|"
            r"validated_critical_flag"
            r")"
            r"\b.*?"
            r"(?:"
            r"create\s+notification|"
            r"insert\s+into\s+notification"
            r")",
            text,
        )
    ):
        result.add(
            "TRACE_CRITICAL_GUARD_MISSING",
            (
                "Notification creation is not clearly "
                "guarded by a validated critical-result "
                "condition."
            ),
        )

    enqueue_match = re.search(
        r"(?i)"
        r"\b(?:enqueue|publish|queue)"
        r"\w*.*"
        r"(?:job|event)",
        text,
    )

    commit_match = re.search(
        r"(?i)"
        r"\b(?:COMMIT|tx\s+commit)\b",
        text,
    )

    if (
        enqueue_match
        and commit_match
        and enqueue_match.start()
        < commit_match.start()
        and "outbox" not in text.lower()
    ):
        result.add(
            "TRACE_QUEUE_BEFORE_COMMIT",
            (
                "A background job appears to be queued "
                "before transaction commit without a "
                "transactional outbox."
            ),
        )

    if (
        re.search(
            r"(?i)"
            r"\bvalue\s+TEXT\s+NOT\s+NULL\b",
            text,
        )
        and re.search(
            r"(?i)"
            r"\bcritical\s+threshold",
            text,
        )
    ):
        result.add(
            "TRACE_NUMERIC_VALUE_AS_TEXT",
            (
                "A laboratory value used for threshold "
                "comparison is stored only as TEXT."
            ),
        )

    _validate_uuid_examples(
        text,
        result,
    )

    _validate_risk_statuses(
        text,
        result,
    )

    for code, message in validate_trace_semantics(
        text,
        source_text,
    ):
        result.add(
            code,
            message,
        )

    return result


# ============================================================
# PUBLIC FUNCTIONS
# ============================================================


def validate_output(
    stage: StageName | str,
    text: str,
    *,
    source_text: str = "",
) -> ValidationResult:
    """
    Validate one ClearSpec AI stage response.
    """

    normalized_stage = (
        stage or ""
    ).strip().lower()

    content = text or ""

    if normalized_stage == "stories":
        return _validate_stories(
            content
        )

    if normalized_stage == "gap":
        return _validate_gap(
            content
        )

    if normalized_stage == "trace":
        return _validate_trace(
            content,
            source_text=source_text or "",
        )

    result = ValidationResult(
        stage=normalized_stage or "unknown"
    )

    result.add(
        "UNKNOWN_STAGE",
        (
            "Unsupported validation stage: "
            f"'{stage}'."
        ),
    )

    return result


def build_repair_user_message(
    *,
    stage: StageName | str,
    original_user_message: str,
    invalid_output: str,
    validation_result: ValidationResult,
) -> str:
    """
    Build a correction request for an invalid AI response.

    Adds deterministic, issue-specific repair rules so the model does not
    merely rephrase the same invalid design.
    """

    issue_codes = {
        issue.code
        for issue in validation_result.issues
    }

    mandatory_fixes: list[str] = []

    if {
        "TRACE_ASSUMPTION_PROMOTED",
        "TRACE_CONFIRMED_SECTION_CONTAMINATED",
    } & issue_codes:
        mandatory_fixes.append(
            "- Remove assumed and unresolved statements from Confirmed "
            "Requirements. Put them under Assumptions or Open Questions. "
            "Do not merely remove the [ASSUMED] label while leaving the "
            "statement under Confirmed Requirements."
        )

    if "TRACE_TIME_DEPENDENT_CHECK" in issue_codes:
        mandatory_fixes.append(
            "- Remove every PostgreSQL CHECK constraint containing NOW(), "
            "CURRENT_TIMESTAMP, CURRENT_DATE, CURRENT_TIME, "
            "clock_timestamp(), statement_timestamp(), or "
            "transaction_timestamp(). Validate time-relative rules in "
            "application logic or a justified trigger instead."
        )

    if {
        "TRACE_QUEUE_WITHOUT_OUTBOX",
        "TRACE_QUEUE_BEFORE_COMMIT",
    } & issue_codes:
        mandatory_fixes.append(
            "- Add a transactional outbox table. Insert the domain record "
            "and outbox event in the same transaction. Publish the message "
            "only after commit through an outbox worker."
        )

    if (
        "TRACE_CALLER_TRIGGERED_CRITICAL_NOTIFICATION"
        in issue_codes
    ):
        mandatory_fixes.append(
            "- Remove caller-triggered send-critical-notification endpoints. "
            "Use laboratory-result ingestion, server-side criticality "
            "validation, an outbox event, and a background delivery worker."
        )

    if "TRACE_DYNAMIC_ORDER_BY" in issue_codes:
        mandatory_fixes.append(
            "- Remove dynamic ORDER BY concatenation. Map a fixed sort enum "
            "to complete predefined SQL fragments."
        )

    if "TRACE_NUMERIC_VALUE_AS_TEXT" in issue_codes:
        mandatory_fixes.append(
            "- Do not store threshold-comparable laboratory values only as "
            "TEXT. Model numeric_value, text_value, unit_code, and test_code "
            "separately."
        )

    if "TRACE_THRESHOLD_ARTIFACT_MISSING" in issue_codes:
        mandatory_fixes.append(
            "- Define either a versioned critical-threshold/rule schema or "
            "an explicit external clinical rules service, including units, "
            "versions, approvals, and auditability."
        )

    if (
        "TRACE_NO_ON_CALL_ESCALATION_CONFLICT"
        in issue_codes
    ):
        mandatory_fixes.append(
            "- Support an UNASSIGNED alert state. Do not require an on-call "
            "assignment when the workflow must escalate because no assignment "
            "exists."
        )

    if "TRACE_IDEMPOTENCY_PRECHECK" in issue_codes:
        mandatory_fixes.append(
            "- Remove race-prone idempotency existence checks such as "
            "'if key exists, return 409'. Enforce idempotency using a "
            "database UNIQUE constraint, attempt the insert atomically, "
            "and translate the unique-violation exception into HTTP 409."
        )

    if (
        "TRACE_OUTBOX_DUPLICATE_PUBLISH_RISK"
        in issue_codes
    ):
        mandatory_fixes.append(
            "- Define the outbox publisher as at-least-once delivery. "
            "Claim rows using FOR UPDATE SKIP LOCKED, use the outbox event "
            "ID as the consumer deduplication key, and include published_at, "
            "attempt_count, and last_error fields. Consumers must be "
            "idempotent because publishing may occur more than once."
        )

    if "TRACE_CURSOR_NOT_APPLIED" in issue_codes:
        mandatory_fixes.append(
            "- Apply the cursor inside the SQL WHERE clause. Use a compound "
            "cursor aligned with the complete ORDER BY clause, such as "
            "collection_ts plus id as a deterministic tie-breaker."
        )

    if "TRACE_PATIENT_ID_NOT_SENSITIVE" in issue_codes:
        mandatory_fixes.append(
            "- Treat patient identifiers linked to clinical data as "
            "sensitive. Do not describe them as non-sensitive or outside "
            "PHI. Use the minimum necessary reference in notifications and "
            "require authenticated access for full clinical details."
        )

    if (
        "TRACE_CONFIRMED_ARCHITECTURE_DECISION"
        in issue_codes
    ):
        mandatory_fixes.append(
            "- Do not mark architectural recommendations as CONFIRMED "
            "unless the supplied stories or Gap Analysis explicitly confirm "
            "them. Mark proposed architecture as PROPOSED or ASSUMED."
        )

    if (
        "TRACE_THRESHOLD_SELECTION_INCOMPLETE"
        in issue_codes
    ):
        mandatory_fixes.append(
            "- Define deterministic critical-threshold selection using "
            "test_code, normalized unit_code, effective_from, retired_at "
            "or effective_to, approved status, and the highest applicable "
            "version."
        )

    if (
        "TRACE_ON_CALL_OVERLAP_UNCONTROLLED"
        in issue_codes
    ):
        mandatory_fixes.append(
            "- Define the scope of each on-call assignment, such as facility, "
            "department, or service. Prevent overlapping active assignments "
            "using a PostgreSQL exclusion constraint or transactionally "
            "enforced overlap validation."
        )
        
    mandatory_fix_text = (
        "\n".join(mandatory_fixes)
        if mandatory_fixes
        else (
            "- Correct every listed validation failure without weakening "
            "or bypassing the required structure."
        )
    )

    return f"""
The previous {stage} response failed deterministic validation.

VALIDATION FAILURES
-------------------

{validation_result.formatted_issues()}

MANDATORY DETERMINISTIC FIXES
-----------------------------

{mandatory_fix_text}

ORIGINAL TASK
-------------

{original_user_message}

INVALID RESPONSE
----------------

{invalid_output}

CORRECTION INSTRUCTION
----------------------

Regenerate the complete response from the beginning.

Correct every listed validation failure. Preserve valid content where
appropriate, but do not discuss the validation process.

Do not repeat the same invalid SQL, endpoint, state model, or pseudocode using
different wording.

Return only the complete corrected Markdown artifact.
""".strip()


__all__ = [
    "StageName",
    "ValidationIssue",
    "ValidationResult",
    "validate_output",
    "build_repair_user_message",
]