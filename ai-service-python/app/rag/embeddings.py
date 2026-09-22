from sentence_transformers import SentenceTransformer
from app.core.config import EMBEDDING_MODEL

model = SentenceTransformer(EMBEDDING_MODEL)

def create_embedding(text: str):
    return model.encode(text)

def create_embeddings(texts: list[str]):
    return model.encode(texts)
