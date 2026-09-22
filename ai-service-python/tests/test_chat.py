from app.rag.pipeline import run_chat

def test_pipeline_import():
    assert callable(run_chat)
