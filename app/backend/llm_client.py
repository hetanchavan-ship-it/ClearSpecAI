"""
Universal LLM wrapper using OpenRouter.
"""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in environment.")

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# You can change this to any OpenRouter model later.
MODEL_NAME = "openai/gpt-4.1"


async def call_llm(system_msg: str, user_msg: str) -> str:
    """
    Send a single prompt to the LLM and return the generated text.
    """

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_msg,
            },
            {
                "role": "user",
                "content": user_msg,
            },
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    return response.choices[0].message.content.strip()