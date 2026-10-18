from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

from app.core.config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the embedding model only when first needed."""
    return TextEmbedding(model_name=EMBEDDING_MODEL)


def create_embedding(text: str):
    model = get_embedding_model()
    return next(iter(model.embed([text])))


def create_embeddings(texts: list[str]):
    model = get_embedding_model()
    return np.array(list(model.embed(texts)))