from __future__ import annotations

from trace_semantic_validator import validate_trace_semantics


def issue_codes(text: str) -> set[str]:
    return {
        code
        for code, _message in validate_trace_semantics(
            text,
            "",
        )
    }


def make_ingestion_trace(schema: str) -> str:
    return f"""
# Technical Traceability Artifacts

## 4. PostgreSQL Schema Changes

```sql
{schema}
```

## 7. Core Logic Pseudocode

```text
function ingest_lab_result(idempotency_key):
    validate the authenticated ingestion request
    persist the result atomically
```
""".strip()


def test_lab_result_ingestions_persists_idempotency_key() -> None:
    trace = make_ingestion_trace(
        """
CREATE TABLE lab_result_ingestions (
    ingestion_id UUID PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    UNIQUE (idempotency_key)
);
""".strip()
    )

    assert (
        "TRACE_INGEST_IDEMPOTENCY_MISSING"
        not in issue_codes(trace)
    )


def test_lab_result_ingestions_without_key_is_rejected() -> None:
    trace = make_ingestion_trace(
        """
CREATE TABLE lab_result_ingestions (
    ingestion_id UUID PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL
);
""".strip()
    )

    assert (
        "TRACE_INGEST_IDEMPOTENCY_MISSING"
        in issue_codes(trace)
    )
