
import logging

from groq import Groq
from app.core.config import GROQ_API_KEY, LLM_MODEL


logger = logging.getLogger(__name__)

groq = Groq(api_key=GROQ_API_KEY)


def chat_completion(
    messages,
    reasoning_effort="low",
    max_completion_tokens=4096,
    json_mode=False,
):
    """Generate a completion with an explicit output-token limit."""

    params = {
        "model": LLM_MODEL,
        "messages": messages,
        "reasoning_effort": reasoning_effort,
        "max_completion_tokens": max_completion_tokens,
    }

    if json_mode:
        params["response_format"] = {"type": "json_object"}
        params["reasoning_format"] = "hidden"

    response = groq.chat.completions.create(**params)

    if not response.choices:
        raise RuntimeError("Groq returned no completion choices.")

    choice = response.choices[0]
    content = choice.message.content

    if choice.finish_reason == "length":
        logger.warning(
            "Groq response reached the token limit (%s).",
            max_completion_tokens,
        )

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            f"Groq returned empty content. "
            f"Finish reason: {choice.finish_reason!r}"
        )

    return content


def chat_completion_with_tools(
    messages,
    tools,
    tool_choice="auto",
):
    """Generate a completion using tool calling."""

    return groq.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        reasoning_effort="low",
        reasoning_format="hidden",
    )
