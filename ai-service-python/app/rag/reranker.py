from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder


@lru_cache(maxsize=1)
def get_reranker_model():
    """Load the reranker only when it is first needed."""
    return TextCrossEncoder(
        model_name="Xenova/ms-marco-MiniLM-L-6-v2"
    )


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5
):
    if not chunks:
        return []

    documents = [chunk["content"] for chunk in chunks]

    model = get_reranker_model()
    scores = list(model.rerank(query, documents))

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