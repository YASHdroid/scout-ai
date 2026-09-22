from app.core.database import get_connection

def create_conversation(document_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO conversations (document_id)
        VALUES (%s)
        RETURNING id
        """,
        (document_id,)
    )

    conversation_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return conversation_id

def get_conversation_document(conversation_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT document_id
        FROM conversations
        WHERE id = %s
        """,
        (conversation_id,)
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row[0] if row else None

def save_message(conversation_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content)
        VALUES (%s, %s, %s)
        """,
        (conversation_id, role, content)
    )

    conn.commit()
    cursor.close()
    conn.close()

def get_recent_messages(conversation_id: int, limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = %s
        ORDER BY id DESC
        LIMIT %s
        """,
        (conversation_id, limit)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return list(reversed(rows))
