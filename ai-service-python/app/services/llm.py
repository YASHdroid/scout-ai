
import json
import logging

from groq import Groq
from openai import OpenAI

from app.core.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")

# Groq provides an OpenAI-compatible API.
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


def chat_completion(
    messages,
    reasoning_effort="low",
    max_completion_tokens=4096,
    json_mode=False,
):
    """Generate text using Groq."""

    kwargs = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    # Some Groq models support reasoning_effort; don't send it
    # unconditionally because unsupported parameters can cause errors.
    if reasoning_effort and "gpt-oss" in GROQ_MODEL.lower():
        kwargs["reasoning_effort"] = reasoning_effort

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Groq returned an empty response.")

    return content


def chat_completion_with_tools(
    messages,
    tools,
    tool_choice="auto",
):
    """Generate a Groq response with function calling enabled."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        max_completion_tokens=4096,
    )

    return response
