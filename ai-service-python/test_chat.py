from db import conn
from groq import Groq

cursor = conn.cursor()

groq = Groq()

cursor.execute(
    """
    INSERT INTO conversations
    DEFAULT VALUES
    RETURNING id
    """
)

conversation_id = cursor.fetchone()[0]

while True:

    user_query = input("You: ")

    if user_query.lower() == "exit":
        break

    cursor.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content)
        VALUES (%s, %s, %s)
        """,
        (
            conversation_id,
            "user",
            user_query
        )
    )

    conn.commit()

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = %s
        ORDER BY id
        """,
        (conversation_id,)
    )

    chat_history = cursor.fetchall()

    groq_messages = []

    for role, content in chat_history:
        groq_messages.append({
            "role": role,
            "content": content
        })

    response = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=groq_messages
    )

    assistant_answer = response.choices[0].message.content

    cursor.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content)
        VALUES (%s, %s, %s)
        """,
        (
            conversation_id,
            "assistant",
            assistant_answer
        )
    )

    conn.commit()

    print(f"Assistant: {assistant_answer}")

cursor.close()
conn.close()