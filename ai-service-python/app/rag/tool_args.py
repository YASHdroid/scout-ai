"""Strict parsing and validation of model-generated tool arguments."""

import json

_JSON_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


class InvalidToolArguments(ValueError):
    """Tool arguments are missing, malformed, or of the wrong type.

    The message is safe to send back to the model and to log: it never
    includes the raw arguments.
    """


def parse_tool_arguments(raw_arguments, parameters_schema: dict) -> dict:
    """
    Parse `raw_arguments` (a JSON string from the provider) and validate it
    against a JSON-schema-style `parameters` block.

    Returns a dict containing only the properties declared in the schema.
    Raises InvalidToolArguments instead of guessing or repairing.
    """

    if raw_arguments is None or (
        isinstance(raw_arguments, str) and not raw_arguments.strip()
    ):
        raw_arguments = "{}"

    try:
        arguments = json.loads(raw_arguments)
    except (json.JSONDecodeError, TypeError):
        raise InvalidToolArguments(
            "Tool arguments were not valid JSON."
        ) from None

    if not isinstance(arguments, dict):
        raise InvalidToolArguments(
            "Tool arguments must be a JSON object."
        )

    properties = parameters_schema.get("properties", {})
    required = parameters_schema.get("required", [])
    cleaned = {}

    for name in required:
        if name not in arguments or arguments[name] is None:
            raise InvalidToolArguments(
                f"Missing required argument '{name}'."
            )

    for name, spec in properties.items():
        if name not in arguments:
            continue

        value = arguments[name]
        expected = _JSON_TYPES.get(spec.get("type"))

        if expected is not None:
            # bool is a subclass of int; don't accept True as an integer.
            wrong_bool = isinstance(value, bool) and spec.get("type") in (
                "integer",
                "number",
            )

            if wrong_bool or not isinstance(value, expected):
                raise InvalidToolArguments(
                    f"Argument '{name}' must be of type {spec.get('type')}."
                )

        if isinstance(value, str):
            value = value.strip()

            if not value and name in required:
                raise InvalidToolArguments(
                    f"Argument '{name}' must not be empty."
                )

        cleaned[name] = value

    # Unexpected extra keys are dropped, never forwarded to the tool.
    return cleaned
