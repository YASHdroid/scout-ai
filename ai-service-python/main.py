import os

from db import conn
from groq import Groq
from dotenv import load_dotenv
from tavily import TavilyClient
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

groq = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "AI service is running"}


class ResearchRequest(BaseModel):
    query: str


class ChatRequest(BaseModel):
    conversation_id: int
    query: str

@app.post("/conversations")
async def create_conversation():

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO conversations
        DEFAULT VALUES
        RETURNING id
        """
    )

    conversation_id = cursor.fetchone()[0]

    conn.commit()

    cursor.close()

    return {
        "conversation_id": conversation_id
    }

@app.post("/chat")
async def chat(request: ChatRequest):

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content)
        VALUES (%s, %s, %s)
        """,
        (
            request.conversation_id,
            "user",
            request.query
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
        (request.conversation_id,)
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
            request.conversation_id,
            "assistant",
            assistant_answer
        )
    )

    conn.commit()

    cursor.close()

    return {
        "conversation_id": request.conversation_id,
        "query": request.query,
        "answer": assistant_answer
    }


@app.post("/research")
async def research(request: ResearchRequest):

    response = tavily.search(
        request.query,
        max_results=5
    )

    sources = []

    for result in response["results"]:
        sources.append({
            "title": result["title"],
            "url": result["url"],
            "content": result["content"]
        })

    context = "\n\n".join(
        f"[{i}] Title: {source['title']}\nContent: {source['content']}"
        for i, source in enumerate(sources, start=1)
    )

    llm_response = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "You are a research assistant. Answer the user's question using only the provided sources. Do not use outside knowledge. If the provided sources do not contain enough information to answer the question, clearly say that the sources are insufficient."
            },
            {
                "role": "user",
                "content": f"""
User Question:
{request.query}

Research Sources:
{context}
"""
            }
        ]
    )

    answer = llm_response.choices[0].message.content

    return {
        "answer": answer,
        "sources": sources
    }