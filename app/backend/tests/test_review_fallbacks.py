from __future__ import annotations

import os

# llm_client requires an API key while importing, but these tests never make
# an external OpenRouter request.
os.environ.setdefault(
    "OPENROUTER_API_KEY",
    "test-openrouter-key",
)

from llm_client import (  # noqa: E402
    _append_gap_review_section,
    _append_trace_review_section,
    _gap_has_only_review_issues,
    _trace_has_only_review_issues,
)
from output_validator import ValidationResult  # noqa: E402


TRACE_DISCLAIMER = (
    "> AI-generated design proposal \u2014 "
    "validate before implementation."
)


def make_result(
    stage: str,
    *codes: str,
) -> ValidationResult:
    result = ValidationResult(stage=stage)

    for code in codes:
        result.add(
            code,
            f"Regression-test message for {code}.",
        )

    return result


def test_gap_contradiction_classification_is_reviewable() -> None:
    result = make_result(
        "gap",
        "GAP_CONTRADICTION_CLASSIFICATION",
    )

    assert _gap_has_only_review_issues(result) is True


def test_gap_missing_section_is_not_reviewable() -> None:
    result = make_result(
        "gap",
        "GAP_SECTION_MISSING",
    )

    assert _gap_has_only_review_issues(result) is False


def test_gap_mixed_reviewable_and_hard_issues_are_blocked() -> None:
    result = make_result(
        "gap",
        "GAP_CONTRADICTION_CLASSIFICATION",
        "GAP_SECTION_MISSING",
    )

    assert _gap_has_only_review_issues(result) is False


def test_gap_review_section_contains_visible_warning() -> None:
    result = make_result(
        "gap",
        "GAP_CONTRADICTION_CLASSIFICATION",
    )

    output = _append_gap_review_section(
        "# Gap & Conflict Analysis\n\nComplete artifact.",
        result,
    )

    assert "## Validation Review Required" in output
    assert "GAP_CONTRADICTION_CLASSIFICATION" in output
    assert "classification inconsistency" in output.lower()


def test_trace_semantic_issue_is_reviewable() -> None:
    result = make_result(
        "trace",
        "TRACE_CURSOR_NOT_APPLIED",
    )

    assert _trace_has_only_review_issues(result) is True


def test_trace_missing_section_is_a_hard_failure() -> None:
    result = make_result(
        "trace",
        "TRACE_SECTION_MISSING",
    )

    assert _trace_has_only_review_issues(result) is False


def test_trace_missing_sql_is_a_hard_failure() -> None:
    result = make_result(
        "trace",
        "TRACE_SQL_BLOCK_MISSING",
    )

    assert _trace_has_only_review_issues(result) is False


def test_trace_mixed_reviewable_and_hard_issues_are_blocked() -> None:
    result = make_result(
        "trace",
        "TRACE_CURSOR_NOT_APPLIED",
        "TRACE_DISCLAIMER_MISSING",
    )

    assert _trace_has_only_review_issues(result) is False


def test_trace_review_section_preserves_disclaimer_as_final_line() -> None:
    result = make_result(
        "trace",
        "TRACE_CURSOR_NOT_APPLIED",
    )

    source = (
        "# Technical Traceability Artifacts\n\n"
        "Complete reviewable artifact.\n\n"
        f"{TRACE_DISCLAIMER}"
    )

    output = _append_trace_review_section(
        source,
        result,
    )

    assert "TRACE_CURSOR_NOT_APPLIED" in output
    assert output.count(TRACE_DISCLAIMER) == 1
    assert output.rstrip().endswith(TRACE_DISCLAIMER)
