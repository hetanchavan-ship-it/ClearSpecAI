from __future__ import annotations

import pytest

from config import (
    ConfigurationError,
    load_settings,
)


VALID_ENVIRONMENT = {
    "MONGO_URL": (
        "mongodb+srv://test-user:test-password@"
        "example.mongodb.net/"
    ),
    "DB_NAME": "clearspec_test",
    "CORS_ORIGINS": (
        "http://localhost:3000,"
        "https://clearspec.example.com"
    ),
    "JWT_SECRET": "a" * 32,
    "JWT_ALGORITHM": "HS256",
    "JWT_EXP_DAYS": "7",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "OPENROUTER_MODEL": "openai/gpt-oss-20b:free",
    "OPENROUTER_MAX_TOKENS": "5000",
    "OPENROUTER_MAX_ATTEMPTS": "3",
    "OUTPUT_REPAIR_ATTEMPTS": "2",
    "OPENROUTER_TIMEOUT_SECONDS": "240",
    "TRACE_ALLOW_REVIEW_WARNINGS": "true",
    "GAP_ALLOW_REVIEW_WARNINGS": "true",
}


def environment_with(
    **changes: str,
) -> dict[str, str]:
    environment = dict(VALID_ENVIRONMENT)
    environment.update(changes)
    return environment


def test_valid_configuration_is_loaded() -> None:
    settings = load_settings(
        VALID_ENVIRONMENT
    )

    assert settings.db_name == "clearspec_test"
    assert settings.openrouter_model == (
        "openai/gpt-oss-20b:free"
    )
    assert settings.openrouter_max_tokens == 5000
    assert settings.trace_allow_review_warnings is True
    assert settings.cors_origins == (
        "http://localhost:3000",
        "https://clearspec.example.com",
    )


def test_missing_required_variable_is_rejected() -> None:
    environment = dict(VALID_ENVIRONMENT)
    environment.pop("MONGO_URL")

    with pytest.raises(
        ConfigurationError,
        match="MONGO_URL environment variable is required",
    ):
        load_settings(environment)


def test_invalid_mongodb_scheme_is_rejected() -> None:
    with pytest.raises(
        ConfigurationError,
        match="MONGO_URL must begin",
    ):
        load_settings(
            environment_with(
                MONGO_URL="https://example.com/database",
            )
        )


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(
        ConfigurationError,
        match="cannot contain '\\*'",
    ):
        load_settings(
            environment_with(
                CORS_ORIGINS="*",
            )
        )


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(
        ConfigurationError,
        match="at least 32 characters",
    ):
        load_settings(
            environment_with(
                JWT_SECRET="too-short",
            )
        )


def test_invalid_integer_setting_is_rejected() -> None:
    with pytest.raises(
        ConfigurationError,
        match="OPENROUTER_MAX_ATTEMPTS must be an integer",
    ):
        load_settings(
            environment_with(
                OPENROUTER_MAX_ATTEMPTS="three",
            )
        )


def test_invalid_boolean_setting_is_rejected() -> None:
    with pytest.raises(
        ConfigurationError,
        match="TRACE_ALLOW_REVIEW_WARNINGS must be one of",
    ):
        load_settings(
            environment_with(
                TRACE_ALLOW_REVIEW_WARNINGS="sometimes",
            )
        )


def test_invalid_model_identifier_is_rejected() -> None:
    with pytest.raises(
        ConfigurationError,
        match="provider/model identifier",
    ):
        load_settings(
            environment_with(
                OPENROUTER_MODEL="invalid model name",
            )
        )
