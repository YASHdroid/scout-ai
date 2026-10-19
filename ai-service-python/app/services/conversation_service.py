
from app.core.database import get_connection


def create_conversation(document_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Only allow a user to create a conversation for their own PDF.
        cursor.execute(
            """
            SELECT id
            FROM documents
            WHERE id = %s AND user_id = %s
            """,
            (document_id, user_id),
        )

        if cursor.fetchone() is None:
            return None

        cursor.execute(
            """
            INSERT INTO conversations (document_id, user_id)
            VALUES (%s, %s)
            RETURNING id
            """,
            (document_id, user_id),
        )

        conversation_id = cursor.fetchone()[0]
        conn.commit()
        return conversation_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def get_conversation_document(
    conversation_id: int,
    user_id: int,
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT document_id
            FROM conversations
            WHERE id = %s AND user_id = %s
            """,
            (conversation_id, user_id),
        )

        row = cursor.fetchone()

        if row is None:
            return None, False

        return row[0], True

    finally:
        cursor.close()
        conn.close()


def save_message(
    conversation_id: int,
    role: str,
    content: str,
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, role, content),
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def get_recent_messages(
    conversation_id: int,
    limit: int = 10,
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (conversation_id, limit),
        )

        rows = cursor.fetchall()
        return list(reversed(rows))

    finally:
        cursor.close()
        conn.close()
