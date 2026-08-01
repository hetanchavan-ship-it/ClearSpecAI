"""
Semantic validation rules for ClearSpec AI Technical Trace output.

This module is intentionally independent from output_validator.py to avoid
circular imports. It returns (code, message) tuples that output_validator can
add to its ValidationResult.
"""

from __future__ import annotations

import re


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "must",
    "of",
    "on",
    "or",
    "per",
    "should",
    "system",
    "that",
    "the",
    "then",
    "this",
    "to",
    "via",
    "when",
    "with",
}


def _strip_markdown(value: str) -> str:
    cleaned = re.sub(r"`{1,3}", " ", value)
    cleaned = re.sub(r"[*_>#|]", " ", cleaned)
    cleaned = re.sub(r"^\s*(?:[-+]\s*|\d+[.)]\s*)", "", cleaned)
    cleaned = re.sub(
        r"\[(?:ASSUMED|OPEN QUESTION)(?::[^\]]*)?\]",
        " ",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _tokens(value: str) -> set[str]:
    raw_tokens = re.findall(
        r"[a-z0-9]+",
        _strip_markdown(value).lower(),
    )

    return {
        token
        for token in raw_tokens
        if len(token) > 2 and token not in _STOPWORDS
    }


def _overlap(left: str, right: str) -> tuple[int, float]:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)

    if not left_tokens or not right_tokens:
        return 0, 0.0

    shared = left_tokens & right_tokens
    denominator = min(len(left_tokens), len(right_tokens))
    return len(shared), len(shared) / denominator


def _extract_heading_section(text: str, title: str) -> str:
    pattern = (
        rf"(?ims)^#{{1,4}}\s*"
        rf"(?:\d+\.\s*)?"
        rf"{re.escape(title)}\s*$"
        rf"(.*?)"
        rf"(?=^#{{1,4}}\s|\Z)"
    )
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _extract_sql(text: str) -> str:
    return "\n".join(
        re.findall(r"(?is)```sql\s*(.*?)```", text)
    )


def _table_body(sql: str, *table_names: str) -> str:
    names = "|".join(re.escape(name) for name in table_names)
    pattern = (
        rf"(?is)"
        rf"CREATE\s+TABLE\s+"
        rf"(?:IF\s+NOT\s+EXISTS\s+)?"
        rf"(?:\"?[A-Za-z_][A-Za-z0-9_]*\"?\.)?"
        rf"\"?(?:{names})\"?"
        rf"\s*\((.*?)\)\s*;"
    )
    match = re.search(pattern, sql)
    return match.group(1) if match else ""


def _threshold_table_names(
    sql: str,
) -> list[str]:
    """Return table names representing critical-value rules or thresholds."""

    created_tables = re.findall(
        r"(?i)"
        r"CREATE\s+TABLE\s+"
        r"(?:IF\s+NOT\s+EXISTS\s+)?"
        r"(?:\"?[A-Za-z_][A-Za-z0-9_]*\"?\.)?"
        r"\"?([A-Za-z_][A-Za-z0-9_]*)\"?"
        r"\s*\(",
        sql,
    )

    matches: list[str] = []

    for table_name in created_tables:
        normalized = table_name.lower()
        tokens = {
            token
            for token in normalized.split("_")
            if token
        }

        has_critical_concept = bool(
            tokens & {"critical", "criticality"}
        )
        has_rule_concept = bool(
            tokens
            & {
                "threshold",
                "thresholds",
                "rule",
                "rules",
                "criteria",
                "criterion",
            }
        )

        if has_critical_concept and has_rule_concept:
            matches.append(normalized)

    return matches


def _source_assumptions(source_text: str) -> list[str]:
    """
    Extract statements only from explicit Assumptions sections.

    A Given/When/Then line is not treated as wholly assumed merely because
    one small clause contains an [ASSUMED: ...] annotation.
    """

    assumptions: list[str] = []

    section_pattern = (
        r"(?ims)"
        r"^#{2,4}\s+Assumptions\s*$"
        r"(.*?)"
        r"(?=^#{1,4}\s+|\Z)"
    )

    for section_match in re.finditer(
        section_pattern,
        source_text,
    ):
        section = section_match.group(1)

        for line in section.splitlines():
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.lower() in {
                "none",
                "none identified",
                "- none",
                "- none identified",
            }:
                continue

            cleaned = _strip_markdown(stripped)

            if len(_tokens(cleaned)) >= 4:
                assumptions.append(cleaned)

    return assumptions


def _check_assumption_promotion(
    text: str,
    source_text: str,
) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    confirmed = _extract_heading_section(
        text,
        "Confirmed Requirements",
    )

    if not confirmed:
        return issues

    if re.search(
        r"(?i)\b(?:assumed|assumption|open question)\b",
        confirmed,
    ):
        issues.append(
            (
                "TRACE_ASSUMPTION_PROMOTED",
                "Confirmed Requirements contains assumption/open-question "
                "wording. Move those statements to Assumptions or Open "
                "Questions.",
            )
        )

    assumptions = _source_assumptions(source_text)

    if not assumptions:
        return issues

    confirmed_lines = [
        _strip_markdown(line)
        for line in confirmed.splitlines()
        if len(_tokens(line)) >= 4
    ]

    for confirmed_line in confirmed_lines:
        for assumption in assumptions:
            shared_count, score = _overlap(
                confirmed_line,
                assumption,
            )

            if shared_count >= 4 and score >= 0.58:
                issues.append(
                    (
                        "TRACE_ASSUMPTION_PROMOTED",
                        "A Confirmed Requirements statement closely matches "
                        "an [ASSUMED] source statement: "
                        f"'{confirmed_line[:180]}'. Keep it under "
                        "Assumptions.",
                    )
                )
                break

    return issues


def _check_time_dependent_check(sql: str) -> list[tuple[str, str]]:
    if re.search(
        r"(?is)"
        r"CHECK\s*\("
        r".{0,400}?"
        r"\b(?:"
        r"now\s*\(|"
        r"current_timestamp\b|"
        r"current_date\b|"
        r"current_time\b|"
        r"clock_timestamp\s*\(|"
        r"statement_timestamp\s*\(|"
        r"transaction_timestamp\s*\("
        r")",
        sql,
    ):
        return [
            (
                "TRACE_TIME_DEPENDENT_CHECK",
                "A PostgreSQL CHECK constraint depends on the current time. "
                "Validate time-relative rules in application logic or a "
                "justified trigger instead.",
            )
        ]

    return []


def _check_lab_value_model(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    body = _table_body(
        sql,
        "lab_result",
        "lab_results",
        "laboratory_result",
        "laboratory_results",
    )

    if not body:
        return issues

    stores_only_text = re.search(
        r"(?im)^\s*(?:value|result_value|test_value)\s+TEXT\b",
        body,
    )
    has_numeric_column = re.search(
        r"(?im)^\s*"
        r"(?:numeric_value|result_numeric|numeric_result|value_numeric)"
        r"\s+(?:NUMERIC|DECIMAL|DOUBLE\s+PRECISION|REAL)\b",
        body,
    )
    critical_context = re.search(
        r"(?i)\b(?:critical|threshold|reference range|"
        r"server_validate_critical|is_critical_server_validated)\b",
        text,
    )

    if stores_only_text and not has_numeric_column and critical_context:
        issues.append(
            (
                "TRACE_NUMERIC_VALUE_AS_TEXT",
                "A laboratory value used for critical-threshold logic is "
                "stored only as TEXT. Model numeric and textual values "
                "separately and include units before comparison.",
            )
        )

    if re.search(r"(?im)^\s*finalized\s+BOOLEAN\b", body):
        issues.append(
            (
                "TRACE_BOOLEAN_FINALIZED_STATE",
                "Laboratory-result lifecycle is represented by a single "
                "finalized BOOLEAN. Use a constrained lifecycle status such "
                "as preliminary, final, amended, corrected, cancelled, or "
                "retracted, with timestamps.",
            )
        )

    return issues


def _check_threshold_artifact(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    validation_referenced = re.search(
        r"(?i)\b(?:"
        r"server_validate_critical|"
        r"is_critical_server_validated|"
        r"server_side_critical|"
        r"server[- ]side\s+(?:criticality|critical[- ]value)\s+validation|"
        r"critical(?:ity)?\s+(?:threshold|rule|validation)|"
        r"predefined\s+critical\s+values|"
        r"validate_critical|"
        r"derive_criticality"
        r")\b",
        text,
    )

    if not validation_referenced:
        return []

    schema_present = bool(_threshold_table_names(sql))

    external_service_present = re.search(
        r"(?i)\b(?:"
        r"external|central|dedicated|versioned"
        r")?\s*"
        r"(?:clinical[- ]rules?|critical[- ]value\s+rules?|"
        r"criticality\s+rules?|rules?\s+engine)\s+"
        r"(?:service|engine|system)\b",
        text,
    )

    if schema_present or external_service_present:
        return []

    return [
        (
            "TRACE_THRESHOLD_ARTIFACT_MISSING",
            "Server-side critical-value validation is referenced without a "
            "versioned threshold/rule schema or explicit external clinical "
            "rule service. Define units, versions, approvals, and auditability.",
        )
    ]


def _check_threshold_selection(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    threshold_tables = _threshold_table_names(sql)

    if not threshold_tables:
        return []

    table_pattern = "|".join(
        re.escape(table_name)
        for table_name in threshold_tables
    )

    selection_contexts = re.findall(
        rf"(?is)"
        rf"(?:SELECT\b.{{0,1200}}?"
        rf"(?:{table_pattern}).{{0,1200}}?"
        rf"(?:;|\n\n|END FUNCTION|function\s+\w+\s*\())",
        text,
    )

    selection_text = "\n".join(selection_contexts) or text

    checks = {
        "test code": bool(
            re.search(r"(?i)\btest_code\b", selection_text)
        ),
        "unit": bool(
            re.search(
                r"(?i)\bunit_code\b|\bnormalized_unit\b",
                selection_text,
            )
        ),
        "effective interval": bool(
            re.search(
                r"(?i)\b(?:effective_from|valid_from|active_from)\b",
                selection_text,
            )
            and re.search(
                r"(?i)\b(?:retired_at|effective_to|valid_to|active_until)\b",
                selection_text,
            )
        ),
        "approval state": bool(
            re.search(
                r"(?i)\b(?:approved|approval_status|approved_at|is_approved)\b",
                selection_text,
            )
        ),
        "deterministic version": bool(
            re.search(
                r"(?i)"
                r"ORDER\s+BY\s+.*\bversion\b.*DESC|"
                r"\bMAX\s*\(\s*version\s*\)|"
                r"\bhighest\s+(?:applicable\s+)?version\b|"
                r"\blatest\s+approved\s+version\b",
                selection_text,
            )
        ),
    }

    missing = [
        label
        for label, present in checks.items()
        if not present
    ]

    if len(missing) >= 2:
        return [
            (
                "TRACE_THRESHOLD_SELECTION_INCOMPLETE",
                "Critical-threshold selection is underspecified. Define "
                "deterministic matching by test code, normalized unit, "
                "effective interval, approval state, and highest applicable "
                "version. Missing or unclear: "
                + ", ".join(missing)
                + ".",
            )
        ]

    return []


def _check_no_on_call_conflict(
    text: str,
    source_text: str,
    sql: str,
) -> list[tuple[str, str]]:
    combined = text + "\n" + source_text
    escalation_expected = re.search(
        r"(?is)(?:no\s+on[- ]call|on[- ]call.{0,80}unavailable|"
        r"no\s+assignment|not\s+assign).{0,180}\b(?:escalat|missed)\b",
        combined,
    )

    if not escalation_expected:
        return []

    notification_body = _table_body(
        sql,
        "notification",
        "notifications",
        "critical_notification",
        "critical_notifications",
    )
    assignment_required = re.search(
        r"(?im)^\s*(?:assignment_id|on_call_id|on_call_assignment_id)"
        r"\s+UUID\s+NOT\s+NULL\b",
        notification_body,
    )
    returns_error = re.search(
        r"(?is)if\s+(?:not\s+assign|assign\s+is\s+null|"
        r"not\s+on_call|on_call\s+is\s+null).{0,180}?"
        r"return\s+(?:404|409|422|error)",
        text,
    )

    if assignment_required or returns_error:
        return [
            (
                "TRACE_NO_ON_CALL_ESCALATION_CONFLICT",
                "The design requires escalation or missed-event handling when "
                "no on-call assignment exists, but the schema or pseudocode "
                "requires an assignment or returns an error. Persist an "
                "UNASSIGNED alert/escalation state and process it safely.",
            )
        ]

    return []


def _check_on_call_overlap(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    body = _table_body(
        sql,
        "on_call_assignment",
        "on_call_assignments",
    )

    if not body:
        return []

    has_time_range = bool(
        re.search(r"(?im)^\s*start_(?:ts|time)\s+TIMESTAMPTZ\b", body)
        and re.search(r"(?im)^\s*end_(?:ts|time)\s+TIMESTAMPTZ\b", body)
    )

    if not has_time_range:
        return []

    has_exclusion_constraint = bool(
        re.search(
            r"(?is)"
            r"EXCLUDE\s+USING\s+gist|"
            r"tstzrange\s*\(",
            sql,
        )
    )
    has_overlap_validation = bool(
        re.search(
            r"(?i)"
            r"prevent\s+overlap|"
            r"overlap\s+validation|"
            r"reject\s+overlapping|"
            r"no\s+overlapping\s+assignments",
            text,
        )
    )

    if not has_exclusion_constraint and not has_overlap_validation:
        return [
            (
                "TRACE_ON_CALL_OVERLAP_UNCONTROLLED",
                "On-call assignments contain start/end timestamps but do not "
                "prevent overlapping active assignments. Define assignment "
                "scope and enforce non-overlap with a PostgreSQL exclusion "
                "constraint or transactionally enforced validation.",
            )
        ]

    return []


def _check_notification_lifecycle(
    sql: str,
) -> list[tuple[str, str]]:
    body = _table_body(
        sql,
        "notification",
        "notifications",
        "critical_notification",
        "critical_notifications",
    )

    if not body:
        return []

    boolean_only = (
        re.search(r"(?im)^\s*delivered\s+BOOLEAN\b", body)
        and re.search(r"(?im)^\s*acknowledged\s+BOOLEAN\b", body)
        and not re.search(r"(?im)^\s*status\s+", body)
    )
    attempt_table = re.search(
        r"(?i)CREATE\s+TABLE\s+"
        r"(?:IF\s+NOT\s+EXISTS\s+)?"
        r"(?:\"?[A-Za-z_][A-Za-z0-9_]*\"?\.)?"
        r"\"?notification_delivery(?:_attempts?)?\"?",
        sql,
    )

    if boolean_only and not attempt_table:
        return [
            (
                "TRACE_NOTIFICATION_LIFECYCLE_INCOMPLETE",
                "Notification lifecycle is represented only by delivered and "
                "acknowledged booleans. Add a constrained status and delivery "
                "attempt records with timestamps, provider IDs, retries, and "
                "failure reasons.",
            )
        ]

    return []


def _cursor_function_blocks(text: str) -> list[str]:
    """Return only pseudocode functions that explicitly accept or use a cursor."""
    blocks = re.findall(
        r"(?is)(function\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\).*?)"
        r"(?=\nfunction\s+[A-Za-z_][A-Za-z0-9_]*\s*\(|\n##|\Z)",
        text,
    )
    return [
        block
        for block in blocks
        if re.search(r"(?i)\bcursor\b|\bnext_cursor\b", block)
    ]


def _query_literals(block: str) -> list[str]:
    """Extract quoted SQL-like query strings from a pseudocode function."""
    literals: list[str] = []
    for match in re.finditer(
        r"(?is)(?:query|sql)\s*(?:\+?=)\s*([\"'])(.*?)\1",
        block,
    ):
        literals.append(match.group(2))
    return literals


def _check_cursor_pagination(text: str) -> list[tuple[str, str]]:
    """Validate cursor comparisons only inside cursor-aware result-list functions."""
    issues: list[tuple[str, str]] = []

    for block in _cursor_function_blocks(text):
        queries = _query_literals(block)
        if not queries:
            queries = re.findall(
                r"(?is)(SELECT\b.{0,1600}?ORDER\s+BY\b.{0,300}?LIMIT\b.{0,100})",
                block,
            )

        for query in queries:
            if not re.search(r"(?i)\bSELECT\b", query):
                continue

            order_match = re.search(
                r"(?i)ORDER\s+BY\s+"
                r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?"
                r"([A-Za-z_][A-Za-z0-9_]*)"
                r"(?:\s+(ASC|DESC))?",
                query,
            )
            if not order_match:
                continue

            order_field = order_match.group(1).lower()
            direction = (order_match.group(2) or "ASC").upper()
            comparisons = re.findall(
                r"(?i)(?:[A-Za-z_][A-Za-z0-9_]*\.)?"
                r"([A-Za-z_][A-Za-z0-9_]*)\s*(<=|>=|<|>)\s*"
                r"(?:\$\d+|:[A-Za-z_][A-Za-z0-9_]*|\?)",
                query,
            )
            if not comparisons:
                continue

            fields = {field.lower() for field, _ in comparisons}
            if order_field not in fields:
                issues.append(
                    (
                        "TRACE_CURSOR_ORDER_MISMATCH",
                        "Cursor pagination compares fields that do not match "
                        f"the leading ORDER BY field '{order_field}'. Align "
                        "the compound cursor with the complete result sort.",
                    )
                )
                continue

            for field, operator in comparisons:
                if field.lower() != order_field:
                    continue
                wrong_direction = (
                    direction == "DESC" and operator in {">", ">="}
                ) or (
                    direction == "ASC" and operator in {"<", "<="}
                )
                if wrong_direction:
                    issues.append(
                        (
                            "TRACE_CURSOR_DIRECTION_INVALID",
                            f"Cursor comparison '{field} {operator} ...' "
                            f"conflicts with ORDER BY {order_field} {direction}. "
                            "Use a direction-compatible comparator and stable tie-breaker.",
                        )
                    )

    return issues


def _check_cursor_not_applied(text: str) -> list[tuple[str, str]]:
    """Require cursor use only when a concrete cursor-aware function is present."""
    blocks = _cursor_function_blocks(text)
    if not blocks:
        return []

    for block in blocks:
        query_text = "\n".join(_query_literals(block)) or block
        cursor_condition = re.search(
            r"(?is)(?:WHERE|AND)\b.{0,700}?"
            r"(?:\bcursor\b|\bcursor_[A-Za-z0-9_]+\b|"
            r"\b(?:collection_ts|result_date|created_at|finalized_at|id)"
            r"\s*(?:<|>|<=|>=)\s*(?:\$\d+|:[A-Za-z_][A-Za-z0-9_]*|\?))",
            query_text,
        )
        conditional_query_building = re.search(
            r"(?is)if\s+cursor\s*(?:!=|is\s+not)\s*(?:null|none)"
            r".{0,400}?(?:query|sql)\s*\+=\s*[\"']\s*(?:AND|WHERE)\b",
            block,
        )
        if not cursor_condition and not conditional_query_building:
            return [
                (
                    "TRACE_CURSOR_NOT_APPLIED",
                    "A result-list function accepts a cursor, but no cursor condition "
                    "is applied to its data query. Use a compound cursor aligned "
                    "with ORDER BY, such as timestamp plus a stable ID tie-breaker.",
                )
            ]
    return []

def _check_queue_outbox(text: str) -> list[tuple[str, str]]:
    queue_operation = re.search(
        r"(?i)\b(?:enqueue|publish|queue)[A-Za-z0-9_]*\s*\(|"
        r"\b(?:enqueue|publish|queue)\b.{0,80}\b(?:job|event|message)\b",
        text,
    )
    database_write = re.search(
        r"(?i)\b(?:insert|update|create)\b.{0,80}"
        r"\b(?:lab_result|notification|event|record)\b",
        text,
    )

    if queue_operation and database_write and "outbox" not in text.lower():
        return [
            (
                "TRACE_QUEUE_WITHOUT_OUTBOX",
                "The design combines database writes with queue publication "
                "but does not define a transactional outbox. Persist an "
                "outbox event in the same transaction and publish after commit.",
            )
        ]

    return []


def _check_idempotency_precheck(
    text: str,
) -> list[tuple[str, str]]:
    pattern = (
        r"(?is)"
        r"if\s+"
        r"(?:exists|find|select|lookup|check)[^\n]{0,120}"
        r"(?:idempotency|idem_key|idempotency_key)"
        r".{0,180}?"
        r"return\s+(?:409|conflict)"
    )

    if re.search(pattern, text):
        return [
            (
                "TRACE_IDEMPOTENCY_PRECHECK",
                "Idempotency is enforced with a pre-insert existence check, "
                "which is race-prone under concurrency. Attempt the insert "
                "under a UNIQUE constraint and translate the unique-violation "
                "exception into HTTP 409.",
            )
        ]

    return []


def _check_outbox_publish_safety(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    outbox_present = bool(
        re.search(r"(?i)\boutbox\b", text)
        or re.search(
            r"(?i)CREATE\s+TABLE\s+"
            r"(?:IF\s+NOT\s+EXISTS\s+)?"
            r"(?:\"?[A-Za-z_][A-Za-z0-9_]*\"?\.)?"
            r"\"?outbox",
            sql,
        )
    )

    if not outbox_present:
        return []

    publisher_pattern = re.search(
        r"(?is)"
        r"(?:function\s+outbox\w*|outbox\w*\s+worker)"
        r".{0,1800}?"
        r"\bpublish\b"
        r".{0,600}?"
        r"(?:published\s*=\s*true|update\b.{0,120}\bpublished)",
        text,
    )

    if not publisher_pattern:
        return []

    safety_markers = (
        r"(?i)\bat[- ]least[- ]once\b",
        r"(?i)\bidempotent\s+consumer\b",
        r"(?i)\bconsumer\s+dedup",
        r"(?i)\bFOR\s+UPDATE\s+SKIP\s+LOCKED\b",
        r"(?i)\bpublished_at\b",
        r"(?i)\battempt_count\b",
        r"(?i)\blast_error\b",
    )

    present_count = sum(
        1
        for marker in safety_markers
        if re.search(marker, text)
    )

    if present_count < 2:
        return [
            (
                "TRACE_OUTBOX_DUPLICATE_PUBLISH_RISK",
                "The outbox publisher publishes and then marks the event as "
                "published, but duplicate publication and concurrent-worker "
                "safety are not defined. Specify at-least-once delivery, "
                "idempotent consumers keyed by event ID, row claiming with "
                "FOR UPDATE SKIP LOCKED, and retry metadata such as "
                "published_at, attempt_count, and last_error.",
            )
        ]

    return []


def _check_patient_identifier_sensitivity(
    text: str,
) -> list[tuple[str, str]]:
    unsafe_patterns = (
        r"(?i)\bpatient\s+(?:id|identifier)\b.{0,80}\bnon[- ]sensitive\b",
        r"(?i)\bnon[- ]sensitive\b.{0,80}\bpatient\s+(?:id|identifier)\b",
        r"(?i)\bnotifications?\b.{0,100}\bpatient\s+(?:id|identifier)\s+only\b"
        r".{0,80}\bno\s+(?:full\s+)?PHI\b",
        r"(?i)\bpatient\s+(?:id|identifier)\s+only\b.{0,80}"
        r"\bno\s+(?:full\s+)?PHI\b",
    )

    if any(re.search(pattern, text) for pattern in unsafe_patterns):
        return [
            (
                "TRACE_PATIENT_ID_NOT_SENSITIVE",
                "A patient identifier is treated as non-sensitive or as "
                "outside PHI merely because it is the only identifier sent. "
                "Patient identifiers linked to clinical alerts remain "
                "sensitive; minimise them and require authenticated access "
                "for full clinical details.",
            )
        ]

    return []


def _check_confirmed_architecture_decision(
    text: str,
    source_text: str,
) -> list[tuple[str, str]]:
    section = _extract_heading_section(
        text,
        "Technical Risks and Decisions",
    )

    if not section:
        return []

    architecture_keywords = {
        "outbox",
        "secret",
        "secrets",
        "vault",
        "postgresql",
        "database",
        "queue",
        "kafka",
        "redis",
        "encryption",
        "threshold",
        "server-side",
        "microservice",
        "architecture",
        "circuit",
        "retry",
    }

    source_lower = source_text.lower()

    for line in section.splitlines():
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        cells = [
            cell.strip()
            for cell in stripped.strip("|").split("|")
        ]

        if len(cells) < 3:
            continue

        if cells[-1].upper() != "CONFIRMED":
            continue

        row_text = " ".join(cells[:-1]).lower()
        matched_keywords = {
            keyword
            for keyword in architecture_keywords
            if keyword in row_text
        }

        if not matched_keywords:
            continue

        source_confirms = any(
            keyword in source_lower
            for keyword in matched_keywords
        )

        if not source_confirms:
            return [
                (
                    "TRACE_CONFIRMED_ARCHITECTURE_DECISION",
                    "An architectural recommendation is marked CONFIRMED "
                    "without explicit confirmation in the supplied stories or "
                    "Gap Analysis. Use PROPOSED or ASSUMED unless the source "
                    "explicitly confirms that decision.",
                )
            ]

    return []


def _check_btree_gist_extension(
    sql: str,
) -> list[tuple[str, str]]:
    uses_text_gist_equality = bool(
        re.search(
            r"(?is)EXCLUDE\s+USING\s+gist\s*\(.*?"
            r"\b(?:facility_code|dept_code|department_code|service_code|"
            r"scope_code|tenant_id)\b\s+WITH\s+=",
            sql,
        )
    )
    has_extension = bool(
        re.search(
            r"(?i)CREATE\s+EXTENSION\s+IF\s+NOT\s+EXISTS\s+"
            r"\"?btree_gist\"?",
            sql,
        )
    )

    if uses_text_gist_equality and not has_extension:
        return [
            (
                "TRACE_BTREE_GIST_MISSING",
                "A GiST exclusion constraint uses equality on scalar fields "
                "such as TEXT, but btree_gist is not enabled. Add "
                "CREATE EXTENSION IF NOT EXISTS btree_gist; or use a "
                "different overlap-enforcement design.",
            )
        ]

    return []



def _check_sql_clause_order(text: str) -> list[tuple[str, str]]:
    """Detect invalid clause ordering only inside concrete query construction."""
    blocks = re.findall(
        r"(?is)(function\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\).*?)"
        r"(?=\nfunction\s+[A-Za-z_][A-Za-z0-9_]*\s*\(|\n##|\Z)",
        text,
    )

    for block in blocks:
        for query in _query_literals(block):
            normalized = re.sub(r"\s+", " ", query).strip()
            invalid = (
                re.search(r"(?i)\bORDER\s+BY\b.*?\bLIMIT\b.*?\b(?:AND|WHERE)\b", normalized)
                or re.search(r"(?i)\bLIMIT\b.*?\bWHERE\b", normalized)
                or re.search(r"(?i)\bORDER\s+BY\b.*?\bWHERE\b", normalized)
            )
            if invalid:
                return [
                    (
                        "TRACE_SQL_CLAUSE_ORDER_INVALID",
                        "A constructed SQL query places WHERE/AND after ORDER BY or LIMIT. "
                        "Build all filters first, followed by ORDER BY and LIMIT.",
                    )
                ]

        for assignment in re.finditer(
            r"(?is)(?:query|sql)\s*=\s*([\"'])(.*?)\1",
            block,
        ):
            base_query = assignment.group(2)
            if not re.search(r"(?i)\b(?:ORDER\s+BY|LIMIT)\b", base_query):
                continue
            tail = block[assignment.end():]
            append_filter = re.search(
                r"(?is)(?:query|sql)\s*\+=\s*([\"'])\s*(?:AND|WHERE)\b.*?\1",
                tail,
            )
            if append_filter:
                return [
                    (
                        "TRACE_SQL_CLAUSE_ORDER_INVALID",
                        "Query construction appends a WHERE/AND filter after ORDER BY or LIMIT. "
                        "Build filters before final sort and pagination clauses.",
                    )
                ]
    return []

def _check_cursor_tiebreaker(
    text: str,
) -> list[tuple[str, str]]:
    cursor_context = re.search(
        r"(?i)\bcursor\b|\bnext_cursor\b|cursor[- ]based",
        text,
    )

    if not cursor_context:
        return []

    order_clauses = re.findall(
        r"(?i)ORDER\s+BY\s+([^\n;\"']+)",
        text,
    )

    timestamp_order = any(
        re.search(
            r"(?i)\b(?:collection_ts|result_date|created_at|finalized_at)\b",
            clause,
        )
        for clause in order_clauses
    )
    stable_id_tiebreaker = any(
        re.search(
            r"(?i)\b(?:collection_ts|result_date|created_at|finalized_at)\b"
            r"[^\n,]*\b(?:ASC|DESC)?\s*,\s*"
            r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?id\b",
            clause,
        )
        for clause in order_clauses
    )

    if timestamp_order and not stable_id_tiebreaker:
        return [
            (
                "TRACE_CURSOR_TIEBREAKER_MISSING",
                "Cursor pagination orders by a non-unique timestamp without "
                "a stable ID tie-breaker. Use a compound cursor and ORDER BY "
                "timestamp plus id in the same direction.",
            )
        ]

    return []



def _check_notification_before_critical_check(text: str) -> list[tuple[str, str]]:
    """Check only ingestion/result-processing workflows, not delivery workers."""
    functions = re.findall(
        r"(?is)(function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\).*?)"
        r"(?=\nfunction\s+[A-Za-z_][A-Za-z0-9_]*\s*\(|\n##|\Z)",
        text,
    )

    for function, function_name in functions:
        name = function_name.lower()
        is_ingestion_flow = bool(
            re.search(r"(?:ingest|process|handle|create|receive).*(?:lab|result)", name)
            or re.search(r"(?i)\binsert\s+lab_result\b", function)
        )
        if not is_ingestion_flow:
            continue

        notification_pos = re.search(r"(?i)(?:insert|create)\s+notification\b", function)
        if not notification_pos:
            continue

        validation_pos = re.search(
            r"(?i)(?:server_side_critical|server_validate_critical|validate_critical|"
            r"derive_criticality|is_critical_server_validated|validated_critical)",
            function,
        )
        guarded_creation = re.search(
            r"(?is)if\s+(?:is_critical|is_crit|validated_critical|criticality_result)"
            r".{0,500}?(?:insert|create)\s+notification\b",
            function,
        )
        if not validation_pos or (
            notification_pos.start() < validation_pos.start() and not guarded_creation
        ):
            return [
                (
                    "TRACE_NOTIFICATION_BEFORE_CRITICAL_CHECK",
                    "An ingestion/result-processing workflow creates a notification before "
                    "server-side criticality validation. Persist the result and outbox event "
                    "first, then create the notification only after validated criticality.",
                )
            ]
    return []

def _check_critical_function_rule_artifact(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    function_referenced = re.search(
        r"(?i)\b(?:server_side_critical|server_validate_critical|"
        r"validate_critical|derive_criticality|"
        r"is_critical_server_validated)\b",
        text,
    )

    if not function_referenced:
        return []

    if _threshold_table_names(sql):
        return []

    external_service = re.search(
        r"(?i)\b(?:clinical|critical[- ]value|criticality)\s+"
        r"(?:rule|rules|rules engine)\s+(?:service|engine)\b",
        text,
    )

    if external_service:
        return []

    return [
        (
            "TRACE_CRITICAL_FUNCTION_WITHOUT_RULE_ARTIFACT",
            "A server-side criticality function is called without a "
            "versioned threshold/rule table or explicit clinical-rules "
            "service. Define the rule source, unit normalization, effective "
            "dates, approval state, and deterministic version selection.",
        )
    ]


def _check_undefined_routing_fields(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    referenced = set(
        re.findall(
            r"(?i)\blab\.(facility|facility_id|facility_code|"
            r"dept|department|department_id|department_code|"
            r"care_team_id|service_code)\b",
            text,
        )
    )

    if not referenced:
        return []

    body = _table_body(
        sql,
        "lab_result",
        "lab_results",
        "laboratory_result",
        "laboratory_results",
    )
    normalized_body = body.lower()

    aliases = {
        "facility": ("facility", "facility_id", "facility_code"),
        "facility_id": ("facility", "facility_id", "facility_code"),
        "facility_code": ("facility", "facility_id", "facility_code"),
        "dept": ("dept", "dept_code", "department", "department_id", "department_code"),
        "department": ("dept", "dept_code", "department", "department_id", "department_code"),
        "department_id": ("dept", "dept_code", "department", "department_id", "department_code"),
        "department_code": ("dept", "dept_code", "department", "department_id", "department_code"),
        "care_team_id": ("care_team_id",),
        "service_code": ("service_code",),
    }

    missing = []
    for field in sorted(referenced):
        if not any(
            re.search(rf"(?im)^\s*{re.escape(candidate)}\s+", normalized_body)
            for candidate in aliases.get(field, (field,))
        ):
            missing.append(field)

    if missing:
        return [
            (
                "TRACE_UNDEFINED_ROUTING_FIELDS",
                "Notification routing references fields that are not defined "
                "on the laboratory result or another explicit routing "
                "context: " + ", ".join(missing) + ". Define facility, "
                "department, service, encounter, or care-team routing data "
                "and select it before use.",
            )
        ]

    return []



def _check_no_on_call_handler_missing(text: str) -> list[tuple[str, str]]:
    """Inspect each on-call routing function and accept common null handlers."""
    functions = re.findall(
        r"(?is)(function\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\).*?)"
        r"(?=\nfunction\s+[A-Za-z_][A-Za-z0-9_]*\s*\(|\n##|\Z)",
        text,
    )

    for function in functions:
        resolves_on_call = re.search(
            r"(?i)\b(?:get_current_on_call|get_active_on_call|resolve_on_call|"
            r"oncall\s*=|on_call\s*=|assignment\s*=.*on[_ -]?call|"
            r"SELECT\s+.*FROM\s+on_call_assignment)",
            function,
        )
        if not resolves_on_call:
            continue

        explicit_handler = re.search(
            r"(?is)if\s+(?:not\s+(?:oncall|on_call|assignment)|"
            r"(?:oncall|on_call|assignment)\s+is\s+(?:null|none)|"
            r"(?:oncall|on_call|assignment)\s*==\s*(?:null|none)|"
            r"(?:oncall|on_call|assignment)\s*==\s*false)"
            r".{0,600}?(?:escalat|missed|unassigned|audit|fallback|"
            r"dead[- ]letter|create\s+(?:alert|event)|insert\s+(?:alert|event))",
            function,
        )
        if not explicit_handler:
            return [
                (
                    "TRACE_NO_ON_CALL_HANDLER_MISSING",
                    "An on-call routing workflow does not explicitly handle an absent "
                    "assignment. Persist an UNASSIGNED or MISSED state, audit it, and invoke "
                    "the approved fallback.",
                )
            ]
    return []

def _check_ingest_idempotency_missing(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    ingest_function = re.search(
        r"(?is)function\s+ingest\w*lab\w*\([^)]*"
        r"(?:idempotency|idem_key|idempotency_key)[^)]*\)",
        text,
    )

    if not ingest_function:
        return []

    lab_body = _table_body(
        sql,
        "lab_result",
        "lab_results",
        "laboratory_result",
        "laboratory_results",
    )
    ingest_body = _table_body(
        sql,
        "ingestion_request",
        "ingestion_requests",
        "lab_ingestion_request",
        "lab_ingestion_requests",
        "lab_result_ingestion",
        "lab_result_ingestions",
    )

    persisted_key = bool(
        re.search(r"(?im)^\s*idempotency_key\s+", lab_body)
        or re.search(r"(?im)^\s*idempotency_key\s+", ingest_body)
    )
    source_identity = bool(
        re.search(r"(?im)^\s*source_result_id\s+", lab_body)
        and re.search(r"(?im)^\s*source_system\s+", lab_body)
        and re.search(r"(?im)^\s*source_version\s+", lab_body)
    )

    if not persisted_key and not source_identity:
        return [
            (
                "TRACE_INGEST_IDEMPOTENCY_MISSING",
                "Laboratory-result ingestion accepts an idempotency key but "
                "does not persist it on the result or an ingestion-request "
                "table, and no unique source identity is defined. Add a "
                "database-enforced UNIQUE idempotency or source/version key.",
            )
        ]

    return []


def _check_api_core_logic_mismatch(
    text: str,
) -> list[tuple[str, str]]:
    has_ingest_logic = bool(
        re.search(r"(?i)function\s+ingest\w*lab", text)
    )

    if not has_ingest_logic:
        return []

    endpoints_section = _extract_heading_section(
        text,
        "REST API Endpoints",
    )
    has_ingest_endpoint = bool(
        re.search(
            r"(?i)\bPOST\b.{0,120}/(?:internal/)?(?:lab-results|"
            r"laboratory-results|lab_results)\b",
            endpoints_section,
        )
    )

    if not has_ingest_endpoint:
        return [
            (
                "TRACE_API_CORE_LOGIC_MISMATCH",
                "Core logic defines laboratory-result ingestion, but the REST "
                "API contract does not expose or document the corresponding "
                "internal ingestion endpoint. Add the authenticated, "
                "idempotent endpoint or identify the non-HTTP event contract.",
            )
        ]

    return []


def _check_get_request_body(
    text: str,
) -> list[tuple[str, str]]:
    endpoints = _extract_heading_section(text, "REST API Endpoints")
    payloads = _extract_heading_section(text, "Representative Payloads")

    has_get_collection = bool(
        re.search(
            r"(?i)\bGET\b.{0,120}/patients?/\{[^}]+\}/lab-results",
            endpoints,
        )
    )
    has_post_example = bool(
        re.search(r"(?i)Successful Request.*?POST\s+", payloads, re.S)
    )
    body_contains_query_controls = bool(
        re.search(
            r"(?is)Successful Request.*?```json.*?"
            r"\"(?:cursor|limit|sort|dateFrom|dateTo)\"\s*:",
            payloads,
        )
    )

    if has_get_collection and body_contains_query_controls and not has_post_example:
        return [
            (
                "TRACE_GET_REQUEST_BODY",
                "The representative request uses a JSON body for a GET "
                "collection endpoint. Put the patient identifier in the path "
                "and cursor/limit/filter values in query parameters, or label "
                "the example as a POST request if that is intended.",
            )
        ]

    return []


def _check_caller_triggered_alert_endpoint(
    text: str,
) -> list[tuple[str, str]]:
    markdown_table_endpoint = re.search(
        r"(?im)^\s*\|?\s*POST\s*\|?\s*"
        r"/[^\s|]*notifications?[^\s|]*(?:critical|trigger|send)",
        text,
    )
    plain_endpoint = re.search(
        r"(?im)^\s*POST\s+/[^\s]*notifications?[^\s]*"
        r"(?:critical|trigger|send)",
        text,
    )

    if markdown_table_endpoint or plain_endpoint:
        return [
            (
                "TRACE_CALLER_TRIGGERED_CRITICAL_NOTIFICATION",
                "A caller-triggered critical-notification endpoint is "
                "proposed. Prefer result ingestion, server-side criticality "
                "validation, and an outbox-driven notification workflow.",
            )
        ]

    return []


def validate_trace_semantics(
    text: str,
    source_text: str = "",
) -> list[tuple[str, str]]:
    """Return deterministic semantic issues for a Technical Trace."""

    sql = _extract_sql(text)
    issues: list[tuple[str, str]] = []

    checks = (
        _check_assumption_promotion(text, source_text),
        _check_time_dependent_check(sql),
        _check_lab_value_model(text, sql),
        _check_threshold_artifact(text, sql),
        _check_threshold_selection(text, sql),
        _check_no_on_call_conflict(text, source_text, sql),
        _check_on_call_overlap(text, sql),
        _check_notification_lifecycle(sql),
        _check_cursor_pagination(text),
        _check_cursor_not_applied(text),
        _check_queue_outbox(text),
        _check_idempotency_precheck(text),
        _check_outbox_publish_safety(text, sql),
        _check_patient_identifier_sensitivity(text),
        _check_confirmed_architecture_decision(text, source_text),
        _check_btree_gist_extension(sql),
        _check_sql_clause_order(text),
        _check_cursor_tiebreaker(text),
        _check_notification_before_critical_check(text),
        _check_critical_function_rule_artifact(text, sql),
        _check_undefined_routing_fields(text, sql),
        _check_no_on_call_handler_missing(text),
        _check_ingest_idempotency_missing(text, sql),
        _check_api_core_logic_mismatch(text),
        _check_get_request_body(text),
        _check_caller_triggered_alert_endpoint(text),
    )

    for check_issues in checks:
        for issue in check_issues:
            if issue not in issues:
                issues.append(issue)

    return issues


__all__ = ["validate_trace_semantics"]