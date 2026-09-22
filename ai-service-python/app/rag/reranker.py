import re

def _tokens(text: str):
    return set(re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower()))

def rerank_chunks(query: str, chunks: list[dict], top_k: int = 5):
    query_tokens = _tokens(query)

    scored = []

    for chunk in chunks:
        content_tokens = _tokens(chunk["content"])

        overlap = len(query_tokens & content_tokens)
        semantic_score = 1.0 / (1.0 + chunk.get("distance", 1.0))
        lexical_score = overlap / max(len(query_tokens), 1)

        final_score = (0.65 * semantic_score) + (0.35 * lexical_score)

        item = dict(chunk)
        item["rerank_score"] = final_score
        scored.append(item)

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)

    return scored[:top_k]
