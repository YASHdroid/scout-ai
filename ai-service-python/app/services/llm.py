
import json
import logging

from google import genai
from google.genai import types

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL


logger = logging.getLogger(__name__)

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to your .env file."
    )

client = genai.Client(api_key=GEMINI_API_KEY)


def _convert_messages(messages):
    """Convert OpenAI-style messages into Gemini contents."""

    system_parts = []
    contents = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content") or ""

        # Tool-call messages need their function calls preserved.
        if role == "system":
            if content:
                system_parts.append(content)
            continue

        if role == "assistant":
            gemini_role = "model"
        else:
            gemini_role = "user"

        if isinstance(content, str) and content.strip():
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content)],
                )
            )

        elif not content and role == "assistant":
            # An assistant tool-call message can have no text.
            pass

    system_instruction = "\n\n".join(system_parts) or None

    return contents, system_instruction


def _generation_config(
    system_instruction=None,
    max_completion_tokens=4096,
    json_mode=False,
    tools=None,
):
    config = {
        "max_output_tokens": max_completion_tokens,
        "temperature": 0.2,
    }

    if system_instruction:
        config["system_instruction"] = system_instruction

    if json_mode:
        config["response_mime_type"] = "application/json"

    if tools:
        config["tools"] = tools

    return types.GenerateContentConfig(**config)


def chat_completion(
    messages,
    reasoning_effort="low",
    max_completion_tokens=4096,
    json_mode=False,
):
    """Generate text using Gemini."""

    contents, system_instruction = _convert_messages(messages)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=_generation_config(
            system_instruction=system_instruction,
            max_completion_tokens=max_completion_tokens,
            json_mode=json_mode,
        ),
    )

    content = response.text

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Gemini returned an empty response. "
            "Check the model, quota, and safety feedback."
        )

    return content


def chat_completion_with_tools(
    messages,
    tools,
    tool_choice="auto",
):
    """Generate a Gemini response with function calling enabled."""

    contents, system_instruction = _convert_messages(messages)

    declarations = []

    for tool in tools or []:
        function = tool.get("function", {})
        name = function.get("name")

        if not name:
            continue

        declarations.append(
            types.FunctionDeclaration(
                name=name,
                description=function.get("description", ""),
                parameters=function.get(
                    "parameters",
                    {"type": "object", "properties": {}},
                ),
            )
        )

    gemini_tools = (
        [types.Tool(function_declarations=declarations)]
        if declarations
        else None
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=_generation_config(
            system_instruction=system_instruction,
            max_completion_tokens=4096,
            tools=gemini_tools,
        ),
    )

    # Keep a simple response object compatible with pipeline.py.
    class Function:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = json.dumps(arguments)

    class ToolCall:
        def __init__(self, call, index):
            self.id = f"gemini_call_{index}"
            self.type = "function"
            self.function = Function(
                call.name,
                call.args or {},
            )

    class Message:
        def __init__(self, text, tool_calls):
            self.content = text
            self.tool_calls = tool_calls

    class Choice:
        def __init__(self, message):
            self.message = message
            self.finish_reason = "stop"

    class Response:
        def __init__(self, message):
            self.choices = [Choice(message)]

    function_calls = []

    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            if part.function_call:
                function_calls.append(part.function_call)

    tool_calls = [
        ToolCall(call, index)
        for index, call in enumerate(function_calls, start=1)
    ]

    return Response(
        Message(
            text=response.text or "",
            tool_calls=tool_calls or None,
        )
    )
