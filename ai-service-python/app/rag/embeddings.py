
from functools import lru_cache

from sentence_transformers import SentenceTransformer
from app.core.config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the embedding model only when first needed."""
    return SentenceTransformer(EMBEDDING_MODEL)


def create_embedding(text: str):
    model = get_embedding_model()
    return model.encode(text)


def create_embeddings(texts: list[str]):
    model = get_embedding_model()
    return model.encode(texts)
