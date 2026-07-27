from __future__ import annotations
from collections.abc import Iterator

import os
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient


# Safe import-time configuration. No external services are contacted.
os.environ.setdefault(
    "MONGO_URL",
    "mongodb://127.0.0.1:27017",
)
os.environ.setdefault(
    "DB_NAME",
    "clearspec_test",
)
os.environ.setdefault(
    "CORS_ORIGINS",
    "http://localhost:3000",
)
os.environ.setdefault(
    "JWT_SECRET",
    "test-jwt-secret-that-is-not-used-in-production",
)
os.environ.setdefault(
    "OPENROUTER_API_KEY",
    "test-openrouter-key",
)
os.environ.setdefault(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-20b:free",
)

import server  # noqa: E402


def _matches(
    document: dict[str, Any],
    query: dict[str, Any],
) -> bool:
    return all(
        document.get(key) == expected
        for key, expected in query.items()
    )


def _apply_projection(
    document: dict[str, Any],
    projection: dict[str, int] | None,
) -> dict[str, Any]:
    result = deepcopy(document)

    if projection and projection.get("_id") == 0:
        result.pop("_id", None)

    return result


class FakeCursor:
    def __init__(
        self,
        documents: list[dict[str, Any]],
    ) -> None:
        self.documents = [
            deepcopy(document)
            for document in documents
        ]
        self.index = 0

    def sort(
        self,
        field: str,
        direction: int,
    ) -> "FakeCursor":
        self.documents.sort(
            key=lambda document: document.get(field, ""),
            reverse=direction == -1,
        )
        return self

    def limit(
        self,
        count: int,
    ) -> "FakeCursor":
        self.documents = self.documents[:count]
        return self

    def __aiter__(self) -> "FakeCursor":
        self.index = 0
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self.index >= len(self.documents):
            raise StopAsyncIteration

        document = deepcopy(
            self.documents[self.index]
        )
        self.index += 1
        return document


class FakeCollection:
    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []

    async def find_one(
        self,
        query: dict[str, Any],
        projection: dict[str, int] | None = None,
    ) -> dict[str, Any] | None:
        for document in self.documents:
            if _matches(document, query):
                return _apply_projection(
                    document,
                    projection,
                )

        return None

    async def insert_one(
        self,
        document: dict[str, Any],
    ) -> SimpleNamespace:
        stored = deepcopy(document)
        stored.setdefault(
            "_id",
            f"fake-{len(self.documents) + 1}",
        )
        self.documents.append(stored)

        return SimpleNamespace(
            inserted_id=stored["_id"],
        )

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
    ) -> SimpleNamespace:
        for document in self.documents:
            if not _matches(document, query):
                continue

            set_values = update.get("$set", {})
            document.update(
                deepcopy(set_values)
            )

            return SimpleNamespace(
                matched_count=1,
                modified_count=1,
            )

        return SimpleNamespace(
            matched_count=0,
            modified_count=0,
        )

    def find(
        self,
        query: dict[str, Any],
        projection: dict[str, int] | None = None,
    ) -> FakeCursor:
        documents = [
            _apply_projection(
                document,
                projection,
            )
            for document in self.documents
            if _matches(document, query)
        ]

        return FakeCursor(documents)

    async def delete_one(
        self,
        query: dict[str, Any],
    ) -> SimpleNamespace:
        for index, document in enumerate(
            self.documents
        ):
            if not _matches(document, query):
                continue

            self.documents.pop(index)

            return SimpleNamespace(
                deleted_count=1,
            )

        return SimpleNamespace(
            deleted_count=0,
        )


class FakeDatabase:
    def __init__(self) -> None:
        self.users = FakeCollection()
        self.history = FakeCollection()


class FakeMongoClient:
    def close(self) -> None:
        return None


@dataclass
class ApiHarness:
    client: TestClient
    db: FakeDatabase
    llm_calls: list[dict[str, str]]
    current_user: dict[str, str]

    def set_user(
        self,
        user_id: str,
        email: str,
    ) -> None:
        self.current_user.clear()
        self.current_user.update(
            {
                "id": user_id,
                "email": email,
            }
        )


@pytest.fixture
def api_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[ApiHarness]:
    fake_db = FakeDatabase()
    llm_calls: list[dict[str, str]] = []

    current_user = {
        "id": "user-1",
        "email": "user1@example.com",
    }

    async def override_current_user() -> dict[str, str]:
        return dict(current_user)

    async def fake_call_llm(
        system_message: str,
        user_message: str,
        *,
        stage: str,
    ) -> str:
        llm_calls.append(
            {
                "system_message": system_message,
                "user_message": user_message,
                "stage": stage,
            }
        )

        outputs = {
            "stories": (
                "# Standardised User Stories\n\n"
                "Mock generated stories."
            ),
            "gap": (
                "# Gap & Conflict Analysis\n\n"
                "Mock generated gap analysis."
            ),
            "trace": (
                "# Technical Traceability Artifacts\n\n"
                "Mock generated technical trace."
            ),
        }

        return outputs[stage]

    async def fake_extract_text(file: Any) -> str:
        return "Mock extracted stakeholder text."

    def fake_user_doc(
        email: str,
        name: str,
        password: str,
    ) -> dict[str, str]:
        return {
            "id": "registered-user",
            "email": email.lower().strip(),
            "name": name.strip(),
            "password_hash": f"hash:{password}",
            "created_at": (
                "2026-07-21T09:00:00+00:00"
            ),
        }

    def fake_create_token(
        user_id: str,
        email: str,
    ) -> str:
        return f"test-token:{user_id}:{email}"

    def fake_verify_password(
        password: str,
        password_hash: str,
    ) -> bool:
        return password_hash == f"hash:{password}"

    monkeypatch.setattr(
        server,
        "db",
        fake_db,
    )
    monkeypatch.setattr(
        server,
        "client",
        FakeMongoClient(),
    )
    monkeypatch.setattr(
        server,
        "call_llm",
        fake_call_llm,
    )
    monkeypatch.setattr(
        server,
        "extract_text",
        fake_extract_text,
    )
    monkeypatch.setattr(
        server,
        "user_doc",
        fake_user_doc,
    )
    monkeypatch.setattr(
        server,
        "create_token",
        fake_create_token,
    )
    monkeypatch.setattr(
        server,
        "verify_password",
        fake_verify_password,
    )

    server.app.dependency_overrides.clear()
    server.app.dependency_overrides[
        server.get_current_user
    ] = override_current_user

    with TestClient(server.app) as client:
        yield ApiHarness(
            client=client,
            db=fake_db,
            llm_calls=llm_calls,
            current_user=current_user,
        )

    server.app.dependency_overrides.clear()
