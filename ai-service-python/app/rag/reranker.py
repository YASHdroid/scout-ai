from sentence_transformers import CrossEncoder


model = CrossEncoder(
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
        (
            query,
            chunk["content"]
        )
        for chunk in chunks
    ]

    scores = model.predict(
        pairs,
        batch_size=16
    )

    scored_chunks = []

    for chunk, score in zip(
        chunks,
        scores
    ):

        item = dict(chunk)

        item["rerank_score"] = float(score)

        scored_chunks.append(item)

    scored_chunks.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return scored_chunks[:top_k]