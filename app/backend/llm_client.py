"""
Reliable asynchronous OpenRouter client for ClearSpec AI.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY was not found in app/backend/.env."
    )

MODEL_NAME = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free",
)

MAX_COMPLETION_TOKENS = int(
    os.getenv("OPENROUTER_MAX_TOKENS", "3000")
)

MAX_ATTEMPTS = int(
    os.getenv("OPENROUTER_MAX_ATTEMPTS", "3")
)

TIMEOUT_SECONDS = float(
    os.getenv("OPENROUTER_TIMEOUT_SECONDS", "180")
)

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=TIMEOUT_SECONDS,
)


def _extract_text(content: Any) -> str:
    """
    Extract visible text from either a plain string or a multipart
    OpenAI-compatible message response.
    """

    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return ""

    parts: list[str] = []

    for item in content:
        if isinstance(item, str):
            if item.strip():
                parts.append(item.strip())
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


def _status_detail(status_code: int) -> str:
    if status_code == 401:
        return (
            "The OpenRouter API key is invalid or inactive. "
            "Check OPENROUTER_API_KEY in app/backend/.env."
        )

    if status_code == 402:
        return (
            "OpenRouter rejected the request because the selected "
            "model requires more credits. Keep OPENROUTER_MODEL set "
            "to openrouter/free or add OpenRouter credits."
        )

    if status_code == 403:
        return (
            "OpenRouter refused access to the selected model or provider."
        )

    if status_code == 429:
        return (
            "The OpenRouter free-model rate limit was reached. "
            "Wait briefly and run the pipeline again."
        )

    return f"OpenRouter request failed with status {status_code}."


async def call_llm(system_msg: str, user_msg: str) -> str:
    """
    Generate a visible Markdown response through OpenRouter.

    Empty responses and transient provider errors are retried because
    the free router may choose a different model for each request.
    """

    last_problem = "No usable AI response was returned."

    enhanced_system_message = (
        f"{system_msg}\n\n"
        "RESPONSE REQUIREMENT:\n"
        "Return a complete, visible final answer in Markdown. "
        "Do not return an empty response. Do not provide only hidden "
        "reasoning or analysis."
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": enhanced_system_message,
                    },
                    {
                        "role": "user",
                        "content": user_msg,
                    },
                ],
                temperature=0.2,
                max_completion_tokens=MAX_COMPLETION_TOKENS,

                # Reduce the chance that a reasoning model consumes its
                # output allowance without returning visible final text.
                extra_body={
                    "reasoning": {
                        "effort": "low",
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
                content = _extract_text(choice.message.content)

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
                    f"OpenRouter model {selected_model} returned an "
                    f"empty response. Finish reason: {finish_reason}."
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

            # Invalid credentials and payment failures will not improve
            # by retrying, so return them immediately.
            if status_code in {400, 401, 402, 403}:
                raise HTTPException(
                    status_code=502,
                    detail=_status_detail(status_code),
                ) from error

            last_problem = _status_detail(status_code)

            logger.warning(
                "%s Attempt %s/%s.",
                last_problem,
                attempt,
                MAX_ATTEMPTS,
            )

        if attempt < MAX_ATTEMPTS:
            # Brief exponential delay: 1 second, then 2 seconds.
            await asyncio.sleep(2 ** (attempt - 1))

    raise HTTPException(
        status_code=502,
        detail=(
            f"{last_problem} ClearSpec AI tried "
            f"{MAX_ATTEMPTS} times. Please run the pipeline again."
        ),
    )