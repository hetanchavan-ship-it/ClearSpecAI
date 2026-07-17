"""
Reliable asynchronous OpenRouter client with deterministic output validation
for the ClearSpec AI pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import HTTPException
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)

from output_validator import (
    ValidationResult,
    build_repair_user_message,
    validate_output,
)

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env", override=True)

logger = logging.getLogger(__name__)

StageName = Literal["stories", "gap", "trace"]

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY was not found in app/backend/.env."
    )

MODEL_NAME = os.getenv(
    "OPENROUTER_MODEL",
    "tencent/hy3:free",
)

MAX_COMPLETION_TOKENS = int(
    os.getenv("OPENROUTER_MAX_TOKENS", "5000")
)

MAX_ATTEMPTS = int(
    os.getenv("OPENROUTER_MAX_ATTEMPTS", "3")
)

OUTPUT_REPAIR_ATTEMPTS = int(
    os.getenv("OUTPUT_REPAIR_ATTEMPTS", "1")
)

TIMEOUT_SECONDS = float(
    os.getenv("OPENROUTER_TIMEOUT_SECONDS", "240")
)

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=TIMEOUT_SECONDS,
)


def _extract_text(content: Any) -> str:
    """
    Extract visible text from an OpenAI-compatible response.
    """

    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return ""

    parts: list[str] = []

    for item in content:
        if isinstance(item, str):
            text = item.strip()

            if text:
                parts.append(text)

            continue

        if isinstance(item, dict):
            text = item.get("text")

            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

            continue

        text = getattr(item, "text", None)

        if isinstance(text, str) and text.strip():
            parts.append(text.strip())

    return "\n".join(parts).strip()


def _read_provider_error(error: APIStatusError) -> str:
    """
    Extract the OpenRouter or provider error body.
    """

    try:
        response_text = error.response.text.strip()

        if response_text:
            return response_text[:1500]

    except Exception:
        pass

    return str(error)


def _status_detail(
    status_code: int,
    provider_message: str = "",
) -> str:
    if status_code == 400:
        detail = "OpenRouter rejected one or more request parameters."

        if provider_message:
            detail += f" Provider response: {provider_message}"

        return detail

    if status_code == 401:
        return (
            "The OpenRouter API key is invalid or inactive. "
            "Check OPENROUTER_API_KEY in app/backend/.env."
        )

    if status_code == 402:
        return (
            "OpenRouter rejected the request because the selected model "
            "requires credits or the account has insufficient balance."
        )

    if status_code == 403:
        return (
            "OpenRouter refused access to the selected model or provider."
        )

    if status_code == 404:
        return (
            f"The OpenRouter model '{MODEL_NAME}' was not found."
        )

    if status_code == 422:
        detail = "OpenRouter could not process the request."

        if provider_message:
            detail += f" Provider response: {provider_message}"

        return detail

    if status_code == 429:
        return (
            "The OpenRouter free-model rate limit was reached. "
            "Wait briefly before trying again."
        )

    return f"OpenRouter request failed with status {status_code}."


async def _request_completion(
    *,
    system_message: str,
    user_message: str,
) -> str:
    """
    Send one logical completion request.

    Transient provider failures and empty responses are retried according to
    OPENROUTER_MAX_ATTEMPTS.
    """

    last_problem = "No usable AI response was returned."

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": system_message,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                max_tokens=MAX_COMPLETION_TOKENS,
                temperature=0.2,
                extra_body={
                    "reasoning": {
                        "effort": "none",
                        "exclude": True,
                    }
                },
            )

            selected_model = getattr(
                response,
                "model",
                MODEL_NAME,
            )

            if not response.choices:
                last_problem = (
                    f"OpenRouter model {selected_model} returned "
                    "no response choices."
                )

                logger.warning(
                    "%s Attempt %s/%s.",
                    last_problem,
                    attempt,
                    MAX_ATTEMPTS,
                )

            else:
                choice = response.choices[0]
                content = _extract_text(
                    choice.message.content
                )

                if content:
                    logger.info(
                        "OpenRouter completed request using model %s "
                        "on attempt %s/%s.",
                        selected_model,
                        attempt,
                        MAX_ATTEMPTS,
                    )

                    return content

                finish_reason = getattr(
                    choice,
                    "finish_reason",
                    None,
                )

                usage = getattr(
                    response,
                    "usage",
                    None,
                )

                last_problem = (
                    f"OpenRouter model {selected_model} returned an empty "
                    f"response. Finish reason: {finish_reason}."
                )

                logger.warning(
                    "%s Usage: %s. Attempt %s/%s.",
                    last_problem,
                    usage,
                    attempt,
                    MAX_ATTEMPTS,
                )

        except APITimeoutError:
            last_problem = (
                "The selected OpenRouter provider timed out."
            )

            logger.warning(
                "%s Attempt %s/%s.",
                last_problem,
                attempt,
                MAX_ATTEMPTS,
            )

        except APIConnectionError:
            last_problem = (
                "Could not connect to OpenRouter."
            )

            logger.warning(
                "%s Attempt %s/%s.",
                last_problem,
                attempt,
                MAX_ATTEMPTS,
            )

        except APIStatusError as error:
            status_code = error.status_code
            provider_message = _read_provider_error(
                error
            )

            logger.error(
                "OpenRouter status %s: %s",
                status_code,
                provider_message,
            )

            if status_code in {
                400,
                401,
                402,
                403,
                404,
                422,
            }:
                raise HTTPException(
                    status_code=502,
                    detail=_status_detail(
                        status_code,
                        provider_message,
                    ),
                ) from error

            last_problem = _status_detail(
                status_code,
                provider_message,
            )

        if attempt < MAX_ATTEMPTS:
            await asyncio.sleep(
                2 ** (attempt - 1)
            )

    raise HTTPException(
        status_code=502,
        detail=(
            f"{last_problem} ClearSpec AI tried "
            f"{MAX_ATTEMPTS} provider attempts."
        ),
    )


def _validation_failure_detail(
    *,
    stage: str,
    validation_result: ValidationResult,
) -> str:
    return (
        f"The generated {stage} artifact failed deterministic validation "
        f"after automatic correction. "
        f"{validation_result.formatted_issues()}"
    )


async def call_llm(
    system_msg: str,
    user_msg: str,
    stage: StageName | None = None,
) -> str:
    """
    Generate one ClearSpec AI artifact.

    When stage is stories, gap, or trace, the result is validated
    deterministically. An invalid result is sent back to the model for one or
    more complete correction attempts before it can reach the frontend or
    MongoDB.
    """

    enhanced_system_message = (
        f"{system_msg}\n\n"
        "RESPONSE REQUIREMENT:\n"
        "Return a complete visible final answer in Markdown. "
        "Do not return an empty response. "
        "Do not return hidden reasoning instead of the final answer."
    )

    generated_output = await _request_completion(
        system_message=enhanced_system_message,
        user_message=user_msg,
    )

    if stage is None:
        return generated_output

    validation_result = validate_output(
    stage,
    generated_output,
    source_text=user_msg,
)

    if validation_result.ok:
        logger.info(
            "Deterministic validation passed for stage '%s'.",
            stage,
        )

        return generated_output

    logger.warning(
        "Deterministic validation failed for stage '%s':\n%s",
        stage,
        validation_result.formatted_issues(),
    )

    current_output = generated_output
    current_validation = validation_result

    for repair_attempt in range(
        1,
        OUTPUT_REPAIR_ATTEMPTS + 1,
    ):
        repair_message = build_repair_user_message(
            stage=stage,
            original_user_message=user_msg,
            invalid_output=current_output,
            validation_result=current_validation,
        )

        logger.info(
            "Requesting automatic correction for stage '%s' "
            "(repair attempt %s/%s).",
            stage,
            repair_attempt,
            OUTPUT_REPAIR_ATTEMPTS,
        )

        repaired_output = await _request_completion(
            system_message=enhanced_system_message,
            user_message=repair_message,
        )

        repaired_validation = validate_output(
    stage,
    repaired_output,
    source_text=user_msg,
)

        if repaired_validation.ok:
            logger.info(
                "Automatic correction passed validation for stage '%s' "
                "on repair attempt %s/%s.",
                stage,
                repair_attempt,
                OUTPUT_REPAIR_ATTEMPTS,
            )

            return repaired_output

        logger.warning(
            "Automatic correction still failed for stage '%s' "
            "on repair attempt %s/%s:\n%s",
            stage,
            repair_attempt,
            OUTPUT_REPAIR_ATTEMPTS,
            repaired_validation.formatted_issues(),
        )

        current_output = repaired_output
        current_validation = repaired_validation

    raise HTTPException(
        status_code=502,
        detail=_validation_failure_detail(
            stage=stage,
            validation_result=current_validation,
        ),
    )


__all__ = [
    "MODEL_NAME",
    "MAX_COMPLETION_TOKENS",
    "MAX_ATTEMPTS",
    "OUTPUT_REPAIR_ATTEMPTS",
    "TIMEOUT_SECONDS",
    "call_llm",
]