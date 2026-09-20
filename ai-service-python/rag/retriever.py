from sentence_transformers import SentenceTransformer
from db import conn

model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve_chunks(query, document_id):

    query_embedding = model.encode(query)

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, chunk_index, chunk_text
        FROM document_chunks
        WHERE document_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT 3
        """,
        (
          document_id,
            str(query_embedding.tolist())
        )
    )

    relevant_chunks = cursor.fetchall()

    if not relevant_chunks:
        cursor.close()
        return []

    chunk_indexes = set()

    for chunk in relevant_chunks:

        chunk_index = chunk[1]

        if chunk_index >= 0:
            chunk_indexes.add(chunk_index)

    placeholders = ",".join(
        ["%s"] * len(chunk_indexes)
    )

    query_sql = f"""
        SELECT id, chunk_index, chunk_text
        FROM document_chunks
        WHERE document_id = %s
        AND chunk_index IN ({placeholders})
        ORDER BY chunk_index
    """

    cursor.execute(
        query_sql,
        [document_id] + list(chunk_indexes)
    )

    results = cursor.fetchall()

    cursor.close()

    return results