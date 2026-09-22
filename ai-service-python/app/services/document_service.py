import os
import pymupdf

from app.core.config import UPLOAD_DIR
from app.core.database import get_connection
from app.rag.chunker import chunk_text
from app.rag.embeddings import create_embedding

def save_document(file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as output:
        output.write(file.file.read())

    pdf = pymupdf.open(file_path)
    text = ""

    for page in pdf:
        text += page.get_text()

    pdf.close()

    chunks = chunk_text(text)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO documents (filename)
            VALUES (%s)
            RETURNING id
            """,
            (safe_filename,)
        )

        document_id = cursor.fetchone()[0]

        for index, chunk in enumerate(chunks):
            embedding = create_embedding(chunk)

            cursor.execute(
                """
                INSERT INTO document_chunks
                (
                    document_id,
                    chunk_index,
                    chunk_text,
                    embedding
                )
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (document_id, chunk_index)
                DO NOTHING
                """,
                (
                    document_id,
                    index,
                    chunk,
                    str(embedding.tolist())
                )
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    return {
        "document_id": document_id,
        "filename": safe_filename,
        "chunk_count": len(chunks)
    }
