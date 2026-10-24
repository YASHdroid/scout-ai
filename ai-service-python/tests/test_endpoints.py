import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import research as research_api
from app.services.llm import ToolCallGenerationError

HEADERS = {"x-internal-secret": "test-secret"}


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(research_api.router)
    return TestClient(app, raise_server_exceptions=False)


def test_standard_research_still_returns_answer_and_sources(client, monkeypatch):
    monkeypatch.setattr(
        research_api, "run_chat", MagicMock(return_value=("answer", [{"url": "u"}]))
    )
    r = client.post("/research", json={"query": "what is rag"}, headers=HEADERS)

    assert r.status_code == 200
    assert r.json()["answer"] == "answer"
    assert r.json()["sources"] == [{"url": "u"}]


def test_standard_research_returns_controlled_502_on_tool_failure(client, monkeypatch):
    monkeypatch.setattr(
        research_api, "run_chat", MagicMock(side_effect=ToolCallGenerationError("x"))
    )
    r = client.post("/research", json={"query": "what is rag"}, headers=HEADERS)

    assert r.status_code == 502
    assert "valid search request" in r.json()["detail"]


def test_advanced_research_is_unaffected_by_tool_calling(client, monkeypatch, tmp_path):
    (tmp_path / "research_synthesis.json").write_text(json.dumps({"s": 1}))
    (tmp_path / "research_verification.json").write_text(json.dumps({"v": 1}))
    monkeypatch.setattr(
        research_api,
        "run_advanced_research",
        MagicMock(return_value={"run_directory": str(tmp_path), "run_id": "r1"}),
    )
    r = client.post(
        "/research/advanced",
        json={"query": "what is rag", "user_id": 1},
        headers=HEADERS,
    )

    assert r.status_code == 200
    assert r.json()["report"] == {"s": 1}


def test_advanced_pipeline_does_not_use_tool_calling():
    import pathlib

    for name in ("advanced_research", "research_executor", "research_planner",
                 "research_analyzer", "research_synthesizer", "research_verifier"):
        source = pathlib.Path(f"app/rag/{name}.py").read_text()
        assert "chat_completion_with_tools" not in source
