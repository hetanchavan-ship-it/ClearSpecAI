from __future__ import annotations

from output_validator import (
    ValidationResult,
    build_repair_user_message,
    validate_output,
)


def _gap_section(heading: str, body: str) -> str:
    supporting_text = (
        "This section records the evidence, uncertainty, delivery impact, "
        "stakeholder decision required, and the recommended review action. "
        "The finding must remain visible until an authorised stakeholder "
        "confirms the expected behaviour and measurable outcome."
    )

    return f"{heading}\n\n{body}\n\n{supporting_text}\n"


def make_gap_output(
    *,
    include_nfr_heading: bool = True,
) -> str:
    sections = [
        _gap_section(
            "# Gap & Conflict Analysis",
            (
                "The supplied requirement is reviewed for ambiguity, missing "
                "behaviour, feasibility risk, security concerns, and delivery "
                "dependencies."
            ),
        ),
        _gap_section(
            "## 1. Contradictions",
            "- None identified.",
        ),
        _gap_section(
            "## 2. Ambiguities and Feasibility Risks",
            (
                "- The source does not define which laboratory systems supply "
                "results or how quickly those systems publish final values."
            ),
        ),
        _gap_section(
            "## 3. Vague or Unmeasurable Terms",
            (
                "- The phrase \"faster access\" requires a measurable retrieval "
                "target and a defined starting event."
            ),
        ),
        _gap_section(
            "## 4. Missing Functional Requirements",
            (
                "- Define result search, filtering, patient matching, "
                "authorisation, acknowledgement, and escalation behaviour."
            ),
        ),
        _gap_section(
            "## 5. Missing Edge Cases",
            (
                "- Define duplicate results, corrected results, unavailable "
                "physicians, delayed notifications, and service outages."
            ),
        ),
        _gap_section(
            "## 6. Security, Privacy, and Compliance Concerns",
            (
                "- Confirm access control, audit logging, minimum necessary "
                "data display, retention, and notification privacy."
            ),
        ),
    ]

    if include_nfr_heading:
        sections.append(
            _gap_section(
                "## 7. Non-Functional Requirements Missing",
                (
                    "- Define availability, latency, auditability, recovery, "
                    "capacity, observability, and notification-delivery targets."
                ),
            )
        )

    sections.extend(
        [
            _gap_section(
                "## 8. Open Questions for Stakeholders",
                (
                    "1. Which event starts the sixty-second notification timer?\n"
                    "2. Which physician role receives the first notification?\n"
                    "3. What happens when the primary recipient is unavailable?"
                ),
            ),
            _gap_section(
                "## 9. Recommended Story Improvements",
                (
                    "- Separate result retrieval, critical-result detection, "
                    "notification delivery, acknowledgement, and escalation "
                    "into independently reviewable stories."
                ),
            ),
            _gap_section(
                "## 10. Risk Score",
                (
                    "**Overall Risk: HIGH**\n\n"
                    "The requirement affects time-sensitive clinical workflows "
                    "but leaves integration, ownership, escalation, security, "
                    "and operational targets unresolved."
                ),
            ),
        ]
    )

    return "\n".join(sections)


def issue_codes(result: ValidationResult) -> set[str]:
    return {
        issue.code
        for issue in result.issues
    }


def test_complete_gap_contract_has_every_required_heading() -> None:
    result = validate_output(
        "gap",
        make_gap_output(),
    )

    assert "GAP_SECTION_MISSING" not in issue_codes(result)


def test_missing_nfr_heading_is_rejected() -> None:
    result = validate_output(
        "gap",
        make_gap_output(
            include_nfr_heading=False,
        ),
    )

    assert "GAP_SECTION_MISSING" in issue_codes(result)

    assert any(
        "Non-Functional Requirements Missing" in issue.message
        for issue in result.issues
    )


def test_repair_message_contains_missing_heading() -> None:
    invalid_output = make_gap_output(
        include_nfr_heading=False,
    )

    result = validate_output(
        "gap",
        invalid_output,
    )

    repair_message = build_repair_user_message(
        stage="gap",
        original_user_message=(
            "Audit the supplied user stories and return the complete "
            "Gap Analysis."
        ),
        invalid_output=invalid_output,
        validation_result=result,
    )

    assert "GAP_SECTION_MISSING" in repair_message
    assert "Non-Functional Requirements Missing" in repair_message


def test_trace_repair_message_restores_exact_matrix_heading() -> None:
    result = ValidationResult(stage="trace")

    result.add(
        "TRACE_SECTION_MISSING",
        (
            "Missing required Technical Trace heading: "
            "'Story-to-Artifact Traceability Matrix'."
        ),
    )

    repair_message = build_repair_user_message(
        stage="trace",
        original_user_message=(
            "Produce the Technical Traceability artifacts in the required "
            "structure."
        ),
        invalid_output=(
            "# Technical Traceability Artifacts\n\n"
            "Incomplete trace output."
        ),
        validation_result=result,
    )

    assert "## 2. Story-to-Artifact Traceability Matrix" in repair_message
    assert "Do not rename, merge, or omit mandatory sections." in repair_message


def test_trace_repair_message_requires_persisted_idempotency() -> None:
    result = ValidationResult(stage="trace")

    result.add(
        "TRACE_IDEMPOTENCY_NOT_PERSISTED",
        (
            "Idempotency is described but no idempotency_key is persisted "
            "in the schema."
        ),
    )

    repair_message = build_repair_user_message(
        stage="trace",
        original_user_message=(
            "Produce the Technical Traceability artifacts in the required "
            "structure."
        ),
        invalid_output=(
            "# Technical Traceability Artifacts\n\n"
            "The API accepts an Idempotency-Key header."
        ),
        validation_result=result,
    )

    assert "idempotency_key" in repair_message
    assert "PostgreSQL schema" in repair_message
    assert "UNIQUE constraint" in repair_message
    assert "HTTP 409" in repair_message


def test_unknown_stage_is_rejected() -> None:
    result = validate_output(
        "unsupported-stage",
        "Example output",
    )

    assert result.ok is False
    assert "UNKNOWN_STAGE" in issue_codes(result)


def test_validation_result_formats_numbered_issues() -> None:
    result = ValidationResult(
        stage="gap",
    )

    result.add(
        "EXAMPLE_ONE",
        "First regression issue.",
    )
    result.add(
        "EXAMPLE_TWO",
        "Second regression issue.",
    )

    formatted = result.formatted_issues()

    assert "1. [EXAMPLE_ONE] First regression issue." in formatted
    assert "2. [EXAMPLE_TWO] Second regression issue." in formatted
