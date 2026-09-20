from sentence_transformers import SentenceTransformer
from db import conn
from groq import Groq


model = SentenceTransformer("all-MiniLM-L6-v2")
groq = Groq()


def retrieve_chunks(query):

    query_embedding = model.encode(query)

    cursor = conn.cursor()

    # Step 1: Find top relevant chunks
    cursor.execute(
        """
        SELECT id, chunk_index, chunk_text
        FROM document_chunks
        WHERE document_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT 1
        """,
        (
            1,
            str(query_embedding.tolist())
        )
    )

    relevant_chunks = cursor.fetchall()

    if not relevant_chunks:
        cursor.close()
        return []

    # Step 2: Collect nearby chunks
    chunk_indexes = set()

    for chunk in relevant_chunks:
        chunk_index = chunk[1]

        for i in range(chunk_index - 2, chunk_index + 3):
            if i >= 0:
                chunk_indexes.add(i)

    # Step 3: Retrieve all nearby chunks
    placeholders = ",".join(["%s"] * len(chunk_indexes))

    query_sql = f"""
        SELECT id, chunk_index, chunk_text
        FROM document_chunks
        WHERE document_id = %s
        AND chunk_index IN ({placeholders})
        ORDER BY chunk_index
    """

    cursor.execute(
        query_sql,
        [1] + list(chunk_indexes)
    )

    results = cursor.fetchall()

    cursor.close()

    return results


query = "What datasets were used for evaluation"

results = retrieve_chunks(query)


print("\nRelevant chunks:")

for result in results:

    print(
        f"\nChunk ID: {result[0]}"
        f"\nChunk Index: {result[1]}"
        f"\n{result[2]}"
    )


context = "\n\n".join(
    f"[Chunk {result[1]}]\n{result[2]}"
    for result in results
)


llm_response = groq.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "system",
            "content": """
You are a helpful assistant.

Answer the user's question using only the provided context.

Follow the user's instructions carefully.

Do not add information that is not present in the context.

If the context is insufficient to answer the question,
clearly say that the context is insufficient.
"""
        },
        {
            "role": "user",
            "content": f"""
Question:
{query}

Context:
{context}
"""
        }
    ]
)


answer = llm_response.choices[0].message.content


print("\nFinal Answer:")
print(answer)


conn.close()