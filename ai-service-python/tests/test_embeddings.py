from app.rag.embeddings import create_embedding

def test_embedding_import():
    assert callable(create_embedding)
