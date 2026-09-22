from app.services.llm import chat_completion

def test_llm_import():
    assert callable(chat_completion)
