
from functools import lru_cache
from sentence_transformers import CrossEncoder


@lru_cache(maxsize=1)
def get_reranker_model():
    """Load the reranker only when it is first needed."""
    return CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5
):
    if not chunks:
        return []

    pairs = [
        (query, chunk["content"])
        for chunk in chunks
    ]

    model = get_reranker_model()

    scores = model.predict(
        pairs,
        batch_size=16
    )

    scored_chunks = []

    for chunk, score in zip(chunks, scores):
        item = dict(chunk)
        item["rerank_score"] = float(score)
        scored_chunks.append(item)

    scored_chunks.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return scored_chunks[:top_k]
