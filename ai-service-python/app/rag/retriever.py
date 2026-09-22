from app.core.database import get_connection
from app.rag.embeddings import create_embedding

def retrieve_chunks(query: str, document_id: int, top_k: int = 8):
    query_embedding = create_embedding(query)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, chunk_index, chunk_text, embedding <=> %s::vector AS distance
        FROM document_chunks
        WHERE document_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (
            str(query_embedding.tolist()),
            document_id,
            str(query_embedding.tolist()),
            top_k
        )
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "chunk_id": row[0],
            "chunk_index": row[1],
            "content": row[2],
            "distance": float(row[3])
        }
        for row in rows
    ]
