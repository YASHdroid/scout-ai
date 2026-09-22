from app.rag.chunker import chunk_text

def test_chunk_text():
    result = chunk_text("hello world", chunk_size=5)
    assert result
