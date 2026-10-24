
import json
import logging

from groq import Groq
from openai import BadRequestError, OpenAI

from app.core.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

# Groq rejects the request with HTTP 400 / code "tool_use_failed" when the
# model emits a tool call that is not valid JSON. The request itself is not
# at fault, and sampling is non-deterministic, so a single retry can succeed.
# It is bounded because a retry cannot fix a deterministic model weakness and
# every attempt costs tokens.
TOOL_CALL_GENERATION_RETRIES = 1


class ToolCallGenerationError(RuntimeError):
    """The provider could not produce a valid tool call after bounded retries."""

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


def _is_tool_use_failed(error: BadRequestError) -> bool:
    """True when Groq rejected the model's own malformed tool call."""

    code = getattr(error, "code", None)

    if code is None:
        body = getattr(error, "body", None)

        if isinstance(body, dict):
            inner = body.get("error", body)
            code = inner.get("code") if isinstance(inner, dict) else None

    return code == "tool_use_failed"


def chat_completion_with_tools(
    messages,
    tools,
    tool_choice="auto",
    max_retries=TOOL_CALL_GENERATION_RETRIES,
):
    """
    Generate a Groq response with function calling enabled.

    If the provider rejects the model's generated tool call
    (400 tool_use_failed), the identical request is retried up to
    `max_retries` times, then ToolCallGenerationError is raised.
    Any other provider error is re-raised unchanged.
    """

    attempts = max_retries + 1

    for attempt in range(1, attempts + 1):
        try:
            return client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                max_completion_tokens=4096,
            )
        except BadRequestError as error:
            if not _is_tool_use_failed(error):
                raise

            # Log metadata only: failed_generation can contain user text.
            body = getattr(error, "body", None)
            inner = body.get("error", body) if isinstance(body, dict) else {}
            failed = inner.get("failed_generation") if isinstance(inner, dict) else None

            logger.warning(
                "Groq tool_use_failed (model=%s, attempt=%d/%d, "
                "failed_generation_chars=%s)",
                GROQ_MODEL,
                attempt,
                attempts,
                len(failed) if isinstance(failed, str) else "unknown",
            )

            if attempt == attempts:
                raise ToolCallGenerationError(
                    "The language model repeatedly produced a malformed "
                    "tool call. Please try again."
                ) from None
