"""Validated application configuration for ClearSpec AI."""

from __future__ import annotations
from functools import lru_cache

import os
import re
from dataclasses import dataclass
from typing import Mapping


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is invalid."""


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_DB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_ALLOWED_JWT_ALGORITHMS = {
    "HS256",
    "HS384",
    "HS512",
}


@dataclass(frozen=True)
class Settings:
    mongo_url: str
    db_name: str
    cors_origins: tuple[str, ...]

    jwt_secret: str
    jwt_algorithm: str
    jwt_exp_days: int

    openrouter_api_key: str
    openrouter_model: str
    openrouter_max_tokens: int
    openrouter_max_attempts: int
    output_repair_attempts: int
    openrouter_timeout_seconds: float

    trace_allow_review_warnings: bool
    gap_allow_review_warnings: bool


def _required(
    source: Mapping[str, str],
    name: str,
) -> str:
    value = source.get(name, "").strip()

    if not value:
        raise ConfigurationError(
            f"{name} environment variable is required."
        )

    return value


def _integer(
    source: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = source.get(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"{name} must be an integer; received {raw_value!r}."
        ) from exc

    if not minimum <= value <= maximum:
        raise ConfigurationError(
            f"{name} must be between {minimum} and {maximum}; "
            f"received {value}."
        )

    return value


def _floating_point(
    source: Mapping[str, str],
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    raw_value = source.get(name, str(default)).strip()

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"{name} must be numeric; received {raw_value!r}."
        ) from exc

    if not minimum <= value <= maximum:
        raise ConfigurationError(
            f"{name} must be between {minimum} and {maximum}; "
            f"received {value}."
        )

    return value


def _boolean(
    source: Mapping[str, str],
    name: str,
    default: bool,
) -> bool:
    default_text = "true" if default else "false"
    raw_value = source.get(name, default_text).strip().lower()

    if raw_value in _TRUE_VALUES:
        return True

    if raw_value in _FALSE_VALUES:
        return False

    raise ConfigurationError(
        f"{name} must be one of true, false, 1, 0, yes, no, "
        f"on, or off; received {raw_value!r}."
    )


def _cors_origins(
    source: Mapping[str, str],
) -> tuple[str, ...]:
    raw_value = _required(
        source,
        "CORS_ORIGINS",
    )

    origins = tuple(
        origin.strip().rstrip("/")
        for origin in raw_value.split(",")
        if origin.strip()
    )

    if not origins:
        raise ConfigurationError(
            "CORS_ORIGINS must contain at least one origin."
        )

    if "*" in origins:
        raise ConfigurationError(
            "CORS_ORIGINS cannot contain '*' while credentialed "
            "requests are enabled."
        )

    invalid_origins = [
        origin
        for origin in origins
        if not origin.startswith(
            (
                "http://",
                "https://",
            )
        )
    ]

    if invalid_origins:
        raise ConfigurationError(
            "Every CORS_ORIGINS value must begin with http:// or "
            f"https://. Invalid values: {invalid_origins!r}."
        )

    return origins


def load_settings(
    source: Mapping[str, str] | None = None,
) -> Settings:
    """
    Read and validate ClearSpec AI configuration.

    Passing a mapping allows deterministic configuration testing without
    modifying the process environment.
    """

    environment = os.environ if source is None else source

    mongo_url = _required(
        environment,
        "MONGO_URL",
    )

    if not mongo_url.startswith(
        (
            "mongodb://",
            "mongodb+srv://",
        )
    ):
        raise ConfigurationError(
            "MONGO_URL must begin with mongodb:// or mongodb+srv://."
        )

    db_name = _required(
        environment,
        "DB_NAME",
    )

    if not _DB_NAME_PATTERN.fullmatch(db_name):
        raise ConfigurationError(
            "DB_NAME may contain only letters, numbers, periods, "
            "underscores, and hyphens."
        )

    jwt_secret = _required(
        environment,
        "JWT_SECRET",
    )

    if len(jwt_secret) < 32:
        raise ConfigurationError(
            "JWT_SECRET must contain at least 32 characters."
        )

    jwt_algorithm = environment.get(
        "JWT_ALGORITHM",
        "HS256",
    ).strip().upper()

    if jwt_algorithm not in _ALLOWED_JWT_ALGORITHMS:
        raise ConfigurationError(
            "JWT_ALGORITHM must be HS256, HS384, or HS512."
        )

    openrouter_api_key = _required(
        environment,
        "OPENROUTER_API_KEY",
    )

    if len(openrouter_api_key) < 10:
        raise ConfigurationError(
            "OPENROUTER_API_KEY appears to be incomplete."
        )

    openrouter_model = environment.get(
        "OPENROUTER_MODEL",
        "openai/gpt-oss-20b:free",
    ).strip()

    if (
        "/" not in openrouter_model
        or " " in openrouter_model
    ):
        raise ConfigurationError(
            "OPENROUTER_MODEL must use a provider/model identifier "
            "such as openai/gpt-oss-20b:free."
        )

    return Settings(
        mongo_url=mongo_url,
        db_name=db_name,
        cors_origins=_cors_origins(environment),
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        jwt_exp_days=_integer(
            environment,
            "JWT_EXP_DAYS",
            7,
            minimum=1,
            maximum=365,
        ),
        openrouter_api_key=openrouter_api_key,
        openrouter_model=openrouter_model,
        openrouter_max_tokens=_integer(
            environment,
            "OPENROUTER_MAX_TOKENS",
            5000,
            minimum=256,
            maximum=32768,
        ),
        openrouter_max_attempts=_integer(
            environment,
            "OPENROUTER_MAX_ATTEMPTS",
            3,
            minimum=1,
            maximum=10,
        ),
        output_repair_attempts=_integer(
            environment,
            "OUTPUT_REPAIR_ATTEMPTS",
            2,
            minimum=0,
            maximum=5,
        ),
        openrouter_timeout_seconds=_floating_point(
            environment,
            "OPENROUTER_TIMEOUT_SECONDS",
            240,
            minimum=10,
            maximum=600,
        ),
        trace_allow_review_warnings=_boolean(
            environment,
            "TRACE_ALLOW_REVIEW_WARNINGS",
            True,
        ),
        gap_allow_review_warnings=_boolean(
            environment,
            "GAP_ALLOW_REVIEW_WARNINGS",
            True,
        ),
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return one validated Settings instance for the application process.
    """

    return load_settings()

__all__ = [
    "ConfigurationError",
    "Settings",
    "get_settings",
    "load_settings",
]
