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
    """
    Return CREATE TABLE names that clearly represent a critical-value
    threshold or clinical criticality rule artifact.

    Accepts valid naming variations such as:
    - critical_threshold
    - critical_threshold_rule
    - critical_value_threshold
    - critical_value_rule
    - lab_critical_threshold
    - clinical_critical_rule
    """

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
        tokens = set(
            token
            for token in normalized.split("_")
            if token
        )

        has_critical_concept = (
            "critical" in tokens
            or "criticality" in tokens
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

        if (
            has_critical_concept
            and has_rule_concept
        ):
            matches.append(
                normalized
            )

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

    schema_present = bool(
        _threshold_table_names(
            sql
        )
    )

    external_service_present = re.search(
        r"(?i)\b(?:"
        r"external|"
        r"central|"
        r"dedicated|"
        r"versioned"
        r")?\s*"
        r"(?:"
        r"clinical[- ]rules?|"
        r"critical[- ]value\s+rules?|"
        r"criticality\s+rules?|"
        r"rules?\s+engine"
        r")\s+"
        r"(?:service|engine|system)\b",
        text,
    )

    if (
        schema_present
        or external_service_present
    ):
        return []

    return [
        (
            "TRACE_THRESHOLD_ARTIFACT_MISSING",
            (
                "Server-side critical-value validation is referenced "
                "without a versioned threshold/rule schema or explicit "
                "external clinical rule service. Define units, versions, "
                "approvals, and auditability."
            ),
        )
    ]


def _check_threshold_selection(
    text: str,
    sql: str,
) -> list[tuple[str, str]]:
    threshold_tables = _threshold_table_names(
        sql
    )

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

    selection_text = "\n".join(
        selection_contexts
    )

    if not selection_text:
        selection_text = text

    checks = {
        "test code": bool(
            re.search(
                r"(?i)\btest_code\b",
                selection_text,
            )
        ),
        "unit": bool(
            re.search(
                r"(?i)\bunit_code\b|\bnormalized_unit\b",
                selection_text,
            )
        ),
        "effective interval": bool(
            re.search(
                r"(?i)\b(?:"
                r"effective_from|"
                r"valid_from|"
                r"active_from"
                r")\b",
                selection_text,
            )
            and re.search(
                r"(?i)\b(?:"
                r"retired_at|"
                r"effective_to|"
                r"valid_to|"
                r"active_until"
                r")\b",
                selection_text,
            )
        ),
        "approval state": bool(
            re.search(
                r"(?i)\b(?:"
                r"approved|"
                r"approval_status|"
                r"approved_at|"
                r"is_approved"
                r")\b",
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
                (
                    "Critical-threshold selection is underspecified. "
                    "Define deterministic matching by test code, normalized "
                    "unit, effective interval, approval state, and highest "
                    "applicable version. Missing or unclear: "
                    + ", ".join(missing)
                    + "."
                ),
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


def _check_cursor_pagination(text: str) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    queries = re.findall(
        r"(?is)(SELECT\b.{0,1800}?ORDER\s+BY\b.{0,300}?LIMIT\b.{0,80})",
        text,
    )

    for query in queries:
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
                    "Cursor pagination compares a field that does not match "
                    f"the leading ORDER BY field '{order_field}'. Use a "
                    "compound cursor aligned with the full sort order.",
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
                        f"Cursor comparison '{field} {operator} ...' conflicts "
                        f"with ORDER BY {order_field} {direction}. Use a "
                        "direction-compatible comparator and deterministic "
                        "tie-breaker.",
                    )
                )

    return issues


def _check_cursor_not_applied(text: str) -> list[tuple[str, str]]:
    cursor_declared = re.search(
        r"(?i)"
        r"\bcursor\b.{0,50}\blimit\b|"
        r"\blimit\b.{0,50}\bcursor\b|"
        r"function\s+\w+\s*\([^)]*\bcursor\b",
        text,
    )

    if not cursor_declared:
        return []

    functions = re.findall(
        r"(?is)"
        r"(function\s+\w+\s*\([^)]*\bcursor\b[^)]*\).*?)"
        r"(?=\nfunction\s+\w+\s*\(|\n##|\Z)",
        text,
    )

    relevant_text = "\n".join(functions) if functions else text

    cursor_used_beyond_signature = re.search(
        r"(?is)"
        r"(?:WHERE|AND)\b.{0,500}?"
        r"(?:"
        r"\bcursor\b|"
        r"\bcursor_[a-z0-9_]+\b|"
        r"\bcollection_ts\s*(?:<|>|<=|>=)\s*(?:\$\d+|:[a-z_]+|\?)|"
        r"\bid\s*(?:<|>|<=|>=)\s*(?:\$\d+|:[a-z_]+|\?)"
        r")",
        relevant_text,
    )

    only_signature_mentions = len(
        re.findall(r"(?i)\bcursor\b", relevant_text)
    ) <= len(functions) if functions else False

    if not cursor_used_beyond_signature or only_signature_mentions:
        return [
            (
                "TRACE_CURSOR_NOT_APPLIED",
                "Cursor pagination is declared, but the cursor is not applied "
                "to the data query. Use a compound cursor aligned with "
                "ORDER BY, such as collection timestamp plus a stable ID "
                "tie-breaker.",
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
        _check_caller_triggered_alert_endpoint(text),
    )

    for check_issues in checks:
        for issue in check_issues:
            if issue not in issues:
                issues.append(issue)

    return issues


__all__ = ["validate_trace_semantics"]