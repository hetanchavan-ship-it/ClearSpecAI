from __future__ import annotations

from typing import Any


def history_record(
    *,
    item_id: str,
    user_id: str,
    created_at: str,
    title: str = "Test requirement",
) -> dict[str, Any]:
    return {
        "id": item_id,
        "user_id": user_id,
        "title": title,
        "domain": "general",
        "created_at": created_at,
        "raw_text": "Example stakeholder requirement.",
        "stories_md": "# Stories",
        "gap_md": None,
        "trace_md": None,
    }


def test_root_health_endpoint(
    api_harness,
) -> None:
    response = api_harness.client.get("/api/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "ClearSpec AI",
        "status": "ok",
    }

def test_public_config_exposes_safe_model_metadata(
    api_harness,
) -> None:
    response = api_harness.client.get(
        "/api/config"
    )

    assert response.status_code == 200

    assert response.json() == {
        "inference_provider": "OpenRouter",
        "model": "openai/gpt-oss-20b:free",
        "model_label": (
            "OPENAI / GPT-OSS-20B : FREE"
        ),
        "validator": "online",
    }

def test_register_and_duplicate_email(
    api_harness,
) -> None:
    payload = {
        "email": "NewUser@example.com",
        "name": "New User",
        "password": "secure-password",
    }

    first = api_harness.client.post(
        "/api/auth/register",
        json=payload,
    )

    assert first.status_code == 200
    assert first.json()["user"]["email"] == (
        "newuser@example.com"
    )
    assert first.json()["token"].startswith(
        "test-token:registered-user:"
    )

    duplicate = api_harness.client.post(
        "/api/auth/register",
        json=payload,
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == (
        "Email already registered"
    )


def test_login_success_and_invalid_password(
    api_harness,
) -> None:
    api_harness.db.users.documents.append(
        {
            "id": "login-user",
            "email": "login@example.com",
            "name": "Login User",
            "password_hash": "hash:correct-password",
        }
    )

    success = api_harness.client.post(
        "/api/auth/login",
        json={
            "email": "LOGIN@example.com",
            "password": "correct-password",
        },
    )

    assert success.status_code == 200
    assert success.json()["user"]["id"] == "login-user"

    invalid = api_harness.client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "wrong-password",
        },
    )

    assert invalid.status_code == 401
    assert invalid.json()["detail"] == (
        "Invalid email or password"
    )


def test_me_returns_current_user_profile(
    api_harness,
) -> None:
    api_harness.db.users.documents.append(
        {
            "id": "user-1",
            "email": "user1@example.com",
            "name": "Current User",
            "password_hash": "unused",
        }
    )

    response = api_harness.client.get(
        "/api/auth/me"
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "user-1",
        "email": "user1@example.com",
        "name": "Current User",
    }


def test_clean_rejects_short_input(
    api_harness,
) -> None:
    response = api_harness.client.post(
        "/api/clean",
        json={
            "raw_text": "short",
            "domain": "general",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Please provide at least 10 characters of input."
    )
    assert api_harness.llm_calls == []


def test_clean_generates_stories_and_saves_history(
    api_harness,
) -> None:
    response = api_harness.client.post(
        "/api/clean",
        json={
            "raw_text": (
                "Doctors need faster access to consolidated "
                "laboratory results."
            ),
            "domain": "healthcare",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["stories_md"] == (
        "# Standardised User Stories\n\n"
        "Mock generated stories."
    )
    assert body["title"].startswith(
        "Doctors need faster access"
    )

    assert len(
        api_harness.db.history.documents
    ) == 1

    stored = api_harness.db.history.documents[0]

    assert stored["user_id"] == "user-1"
    assert stored["domain"] == "healthcare"
    assert stored["stories_md"] == body["stories_md"]
    assert api_harness.llm_calls[-1]["stage"] == (
        "stories"
    )


def test_analyze_updates_only_owned_history(
    api_harness,
) -> None:
    api_harness.db.history.documents.extend(
        [
            history_record(
                item_id="owned-item",
                user_id="user-1",
                created_at="2026-07-21T09:00:00+00:00",
            ),
            history_record(
                item_id="foreign-item",
                user_id="user-2",
                created_at="2026-07-21T09:01:00+00:00",
            ),
        ]
    )

    response = api_harness.client.post(
        "/api/analyze",
        json={
            "stories": "# Stories\n\nValid stories.",
            "context": "Existing system context.",
            "history_id": "owned-item",
        },
    )

    assert response.status_code == 200
    assert response.json()["gap_md"].startswith(
        "# Gap & Conflict Analysis"
    )

    owned = api_harness.db.history.documents[0]
    foreign = api_harness.db.history.documents[1]

    assert owned["gap_md"] == response.json()["gap_md"]
    assert foreign["gap_md"] is None
    assert api_harness.llm_calls[-1]["stage"] == "gap"


def test_trace_updates_owned_history(
    api_harness,
) -> None:
    api_harness.db.history.documents.append(
        history_record(
            item_id="owned-item",
            user_id="user-1",
            created_at="2026-07-21T09:00:00+00:00",
        )
    )

    response = api_harness.client.post(
        "/api/trace",
        json={
            "stories": "# Stories\n\nValid stories.",
            "history_id": "owned-item",
        },
    )

    assert response.status_code == 200
    assert response.json()["trace_md"].startswith(
        "# Technical Traceability Artifacts"
    )

    stored = api_harness.db.history.documents[0]

    assert stored["trace_md"] == (
        response.json()["trace_md"]
    )
    assert api_harness.llm_calls[-1]["stage"] == (
        "trace"
    )


def test_history_list_is_scoped_and_sorted(
    api_harness,
) -> None:
    api_harness.db.history.documents.extend(
        [
            history_record(
                item_id="older",
                user_id="user-1",
                created_at="2026-07-20T08:00:00+00:00",
                title="Older item",
            ),
            history_record(
                item_id="foreign",
                user_id="user-2",
                created_at="2026-07-22T08:00:00+00:00",
                title="Foreign item",
            ),
            history_record(
                item_id="newer",
                user_id="user-1",
                created_at="2026-07-21T08:00:00+00:00",
                title="Newer item",
            ),
        ]
    )

    response = api_harness.client.get(
        "/api/history"
    )

    assert response.status_code == 200

    items = response.json()

    assert [
        item["id"]
        for item in items
    ] == [
        "newer",
        "older",
    ]


def test_get_and_delete_history_enforce_ownership(
    api_harness,
) -> None:
    api_harness.db.history.documents.extend(
        [
            history_record(
                item_id="owned",
                user_id="user-1",
                created_at="2026-07-21T08:00:00+00:00",
            ),
            history_record(
                item_id="foreign",
                user_id="user-2",
                created_at="2026-07-21T09:00:00+00:00",
            ),
        ]
    )

    owned_get = api_harness.client.get(
        "/api/history/owned"
    )
    foreign_get = api_harness.client.get(
        "/api/history/foreign"
    )

    assert owned_get.status_code == 200
    assert foreign_get.status_code == 404

    foreign_delete = api_harness.client.delete(
        "/api/history/foreign"
    )
    owned_delete = api_harness.client.delete(
        "/api/history/owned"
    )

    assert foreign_delete.status_code == 404
    assert owned_delete.status_code == 200
    assert owned_delete.json() == {"ok": True}

    remaining_ids = {
        document["id"]
        for document in api_harness.db.history.documents
    }

    assert remaining_ids == {"foreign"}


def test_extract_returns_mocked_file_content(
    api_harness,
) -> None:
    response = api_harness.client.post(
        "/api/extract",
        files={
            "file": (
                "requirements.txt",
                b"Example uploaded requirement.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Mock extracted stakeholder text.",
        "filename": "requirements.txt",
    }
