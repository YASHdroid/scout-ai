from app.rag.retriever import retrieve_chunks

def test_retriever_import():
    assert callable(retrieve_chunks)
