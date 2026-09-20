from rag.retriever import retrieve_chunks


def document_search(query, document_id):

    results = retrieve_chunks(
        query,
        document_id
    )

    return [
        {
            "chunk_id": item[0],
            "chunk_index": item[1],
            "content": item[2]
        }
        for item in results
    ]