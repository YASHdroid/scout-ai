import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest

from app.rag import pipeline
from app.rag.pipeline import (
    DOCUMENT_SEARCH_TOOL,
    WEB_SEARCH_TOOL,
    execute_tool,
    run_agent,
)
from app.rag.tool_args import InvalidToolArguments, parse_tool_arguments
from app.services import llm
from app.services.llm import ToolCallGenerationError

SCHEMA = WEB_SEARCH_TOOL["function"]["parameters"]


# ---------------------------------------------------------------- helpers

def make_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def make_response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls or None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def tool_use_failed_error():
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/x")
    response = httpx.Response(400, request=request)
    return openai.BadRequestError(
        "Failed to parse tool call arguments as JSON",
        response=response,
        body={
            "code": "tool_use_failed",
            "message": "Failed to parse tool call arguments as JSON",
            "failed_generation": '{"name": "web_search", "arguments": {"query":"secret user text", "})"}',
        },
    )


def other_bad_request_error():
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/x")
    response = httpx.Response(400, request=request)
    return openai.BadRequestError(
        "bad model", response=response, body={"code": "model_not_found"}
    )


@pytest.fixture
def mocks(monkeypatch):
    """Mock the LLM and every external tool; return the mocks."""
    llm_tools = MagicMock(name="chat_completion_with_tools")
    final = MagicMock(name="chat_completion", return_value="final answer")
    web = MagicMock(
        name="web_search",
        return_value=[{"title": "T", "url": "https://x.test", "content": "C"}],
    )
    doc = MagicMock(
        name="targeted_document_search",
        return_value=[
            {"chunk_id": 1, "chunk_index": 0, "content": "chunk", "similarity": 0.9}
        ],
    )
    monkeypatch.setattr(pipeline, "chat_completion_with_tools", llm_tools)
    monkeypatch.setattr(pipeline, "chat_completion", final)
    monkeypatch.setattr(pipeline, "web_search", web)
    monkeypatch.setattr(pipeline, "targeted_document_search", doc)
    return SimpleNamespace(llm=llm_tools, final=final, web=web, doc=doc)


# ------------------------------------------- 1, 2: valid arguments

def test_valid_web_search_arguments_parse():
    assert parse_tool_arguments('{"query": "  rag  "}', SCHEMA) == {"query": "rag"}


def test_valid_web_search_executes_and_collects_sources(mocks):
    mocks.llm.side_effect = [
        make_response(tool_calls=[make_call("c1", "web_search", '{"query": "rag"}')]),
        make_response(content="answer"),
    ]

    answer, sources = run_agent("what is rag today", document_id=None)

    assert answer == "answer"
    mocks.web.assert_called_once_with(query="rag", max_results=5)
    assert sources == [
        {"type": "web", "title": "T", "url": "https://x.test", "content": "C"}
    ]


def test_valid_document_search_executes(mocks):
    mocks.llm.side_effect = [
        make_response(
            tool_calls=[make_call("c1", "document_search", '{"query": "modules"}')]
        ),
        make_response(content="doc answer"),
    ]

    answer, sources = run_agent("explain section three", document_id=7)

    assert answer == "doc answer"
    mocks.doc.assert_called_once_with(query="modules", document_id=7, top_k=8)
    assert sources[0]["type"] == "document"
    mocks.web.assert_not_called()


# ------------------------------------- 3, 4, 5: invalid arguments

@pytest.mark.parametrize(
    "raw",
    [
        '{"query":"RAG works by retrieving", "})"}',  # the production failure
        '{"query": "unterminated',
        "not json",
    ],
)
def test_malformed_json_is_rejected(raw):
    with pytest.raises(InvalidToolArguments, match="not valid JSON"):
        parse_tool_arguments(raw, SCHEMA)


@pytest.mark.parametrize("raw", ["{}", '{"other": "x"}', '{"query": null}', '{"query": "   "}', None, ""])
def test_missing_or_empty_query_is_rejected(raw):
    with pytest.raises(InvalidToolArguments):
        parse_tool_arguments(raw, SCHEMA)


@pytest.mark.parametrize("raw", ["[]", '"query"', "42", "null", "true"])
def test_non_object_json_is_rejected(raw):
    with pytest.raises(InvalidToolArguments, match="JSON object"):
        parse_tool_arguments(raw, SCHEMA)


def test_wrong_type_is_rejected_and_extra_keys_dropped():
    with pytest.raises(InvalidToolArguments, match="type string"):
        parse_tool_arguments('{"query": 5}', SCHEMA)

    assert parse_tool_arguments('{"query": "a", "evil": "b"}', SCHEMA) == {"query": "a"}


def test_invalid_call_is_not_executed_and_model_can_recover(mocks):
    bad = '{"query":"abc", "})"}'
    mocks.llm.side_effect = [
        make_response(tool_calls=[make_call("c1", "web_search", bad)]),
        make_response(tool_calls=[make_call("c2", "web_search", '{"query": "abc"}')]),
        make_response(content="recovered"),
    ]

    answer, sources = run_agent("what is the latest on rag", document_id=None)

    assert answer == "recovered"
    mocks.web.assert_called_once_with(query="abc", max_results=5)  # only the valid call

    # Second request: the malformed arguments are not echoed back.
    second_messages = mocks.llm.call_args_list[1].kwargs["messages"]
    assistant = [m for m in second_messages if m["role"] == "assistant"][0]
    assert assistant["tool_calls"][0]["function"]["arguments"] == "{}"
    tool_msg = [m for m in second_messages if m["role"] == "tool"][0]
    assert tool_msg["tool_call_id"] == "c1"
    assert "not executed" in json.loads(tool_msg["content"])["error"]


def test_repeated_invalid_calls_fail_in_a_controlled_way(mocks):
    mocks.llm.return_value = make_response(
        tool_calls=[make_call("c1", "web_search", "{}")]
    )

    with pytest.raises(ToolCallGenerationError):
        run_agent("what is the latest on rag", document_id=None)

    mocks.web.assert_not_called()
    assert mocks.llm.call_count == pipeline.MAX_INVALID_TOOL_CALLS  # bounded


def test_execute_tool_never_returns_silent_empty_search():
    result = execute_tool("web_search", {}, document_id=None)
    assert isinstance(result, dict) and "error" in result


# --------------------------- 6, 7: provider-side HTTP 400 handling

def test_provider_400_is_retried_once_then_succeeds(monkeypatch):
    create = MagicMock(side_effect=[tool_use_failed_error(), "ok-response"])
    monkeypatch.setattr(llm.client.chat.completions, "create", create)

    assert llm.chat_completion_with_tools([], [WEB_SEARCH_TOOL]) == "ok-response"
    assert create.call_count == 2


def test_provider_400_controlled_failure_when_retries_exhausted(monkeypatch, caplog):
    create = MagicMock(side_effect=tool_use_failed_error())
    monkeypatch.setattr(llm.client.chat.completions, "create", create)

    with pytest.raises(ToolCallGenerationError) as exc:
        llm.chat_completion_with_tools([], [WEB_SEARCH_TOOL])

    assert create.call_count == llm.TOOL_CALL_GENERATION_RETRIES + 1  # no infinite loop
    assert "secret user text" not in str(exc.value)
    assert "secret user text" not in caplog.text  # user text is not logged


def test_other_400_errors_are_not_retried(monkeypatch):
    create = MagicMock(side_effect=other_bad_request_error())
    monkeypatch.setattr(llm.client.chat.completions, "create", create)

    with pytest.raises(openai.BadRequestError):
        llm.chat_completion_with_tools([], [WEB_SEARCH_TOOL])

    assert create.call_count == 1


# ------------------------------------------- 8: message sequencing

def test_assistant_and_tool_messages_are_sequenced_across_rounds(mocks):
    mocks.llm.side_effect = [
        make_response(tool_calls=[make_call("a1", "web_search", '{"query": "one"}')]),
        make_response(tool_calls=[make_call("b1", "web_search", '{"query": "two"}')]),
        make_response(content="done"),
    ]
    run_agent("latest news on rag", document_id=None)

    # The messages list is mutated in place, so inspect the final call's view.
    messages = mocks.llm.call_args_list[-1].kwargs["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant", "tool"]

    for i in (2, 4):
        assistant, tool = messages[i], messages[i + 1]
        assert tool["tool_call_id"] == assistant["tool_calls"][0]["id"]


def test_every_tool_call_gets_a_reply_when_limit_is_hit(mocks, monkeypatch):
    calls = [make_call(f"c{i}", "web_search", '{"query": "q"}') for i in range(12)]
    mocks.llm.side_effect = [make_response(tool_calls=calls)]

    run_agent("latest news on rag", document_id=None)

    messages = mocks.final.call_args.kwargs["messages"]
    call_ids = [c["id"] for m in messages if m["role"] == "assistant" for c in m["tool_calls"]]
    reply_ids = [m["tool_call_id"] for m in messages if m["role"] == "tool"]

    assert call_ids == reply_ids  # no orphaned tool_calls sent to the provider
    assert mocks.web.call_count == 10  # limit still enforced


# --------------------------------------------- 9: document-only mode

def test_document_only_mode_does_not_expose_or_execute_web_search(mocks):
    mocks.llm.side_effect = [
        make_response(tool_calls=[make_call("c1", "web_search", '{"query": "x"}')]),
        make_response(content="doc only"),
    ]

    run_agent("using only the uploaded PDF, explain section 2", document_id=7)

    exposed = [t["function"]["name"] for t in mocks.llm.call_args_list[0].kwargs["tools"]]
    assert exposed == ["document_search"]
    mocks.web.assert_not_called()

    tool_msg = [
        m for m in mocks.llm.call_args_list[1].kwargs["messages"] if m["role"] == "tool"
    ][0]
    assert "not available" in json.loads(tool_msg["content"])["error"]


def test_execute_tool_blocks_web_search_in_document_only_mode():
    result = execute_tool("web_search", {"query": "x"}, document_id=1, document_only=True)
    assert "disabled" in result["error"]
