
from app.core.database import get_connection
from app.rag.embeddings import create_embedding


def retrieve_chunks(
    query: str,
    document_id: int,
    top_k: int = 8,
    min_similarity: float = 0.0,
):
    """
    Retrieve the most relevant chunks for a specific document.

    Args:
        query: User's search query.
        document_id: ID of the uploaded document.
        top_k: Maximum number of chunks to return.
        min_similarity: Minimum cosine similarity score (0.0 to 1.0).

    Returns:
        A list of dictionaries containing chunk metadata and content.
    """

    if top_k <= 0:
        return []

    # 1. Create the embedding for the search query.
    query_embedding = create_embedding(query)
    embedding_str = str(query_embedding.tolist())

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 2. Fetch a wider candidate pool from this document only.
        # pgvector's <=> operator returns cosine distance.
        cursor.execute(
            """
            SELECT
                id,
                chunk_index,
                chunk_text,
                embedding <=> %s::vector AS distance
            FROM document_chunks
            WHERE document_id = %s
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector ASC
            LIMIT %s
            """,
            (
                embedding_str,
                document_id,
                embedding_str,
                max(top_k * 4, 30),
            ),
        )

        rows = cursor.fetchall()

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None:
            conn.close()

    # 3. Convert database rows into a consistent format.
    results = []

    for row in rows:
        distance = float(row[3])
        similarity = 1.0 - distance

        # Keep the threshold configurable.
        if similarity < min_similarity:
            continue

        results.append(
            {
                "chunk_id": row[0],
                "chunk_index": row[1],
                "content": row[2],
                "distance": distance,
                "similarity": similarity,
            }
        )

    # 4. Return at most top_k chunks.
    return results[:top_k]
