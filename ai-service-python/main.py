import os
import json
import pymupdf

from db import conn
from groq import Groq
from dotenv import load_dotenv
from tavily import TavilyClient
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from tools.web_search import web_search
from tools.document_search import document_search


load_dotenv()


tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


groq = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


app = FastAPI()


@app.get("/health")
def health():
    return {
        "status": "AI service is running"
    }


class ResearchRequest(BaseModel):
    query: str


class ChatRequest(BaseModel):
    conversation_id: int
    document_id: int
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


@app.post("/documents")
async def upload_document(
    file: UploadFile = File(...)
):

    os.makedirs(
        "uploads",
        exist_ok=True
    )

    file_path = os.path.join(
        "uploads",
        file.filename
    )

    file_content = await file.read()

    with open(file_path, "wb") as f:
        f.write(file_content)

    pdf = pymupdf.open(file_path)

    text = ""

    for page in pdf:
        text += page.get_text()

    pdf.close()

    def chunk_text(
        text,
        chunk_size=1000
    ):

        chunks = []

        for i in range(
            0,
            len(text),
            chunk_size
        ):

            chunks.append(
                text[i:i + chunk_size]
            )

        return chunks

    chunks = chunk_text(text)

    chunks = [
        chunk.replace("\x00", "")
        for chunk in chunks
    ]

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documents (filename)
        VALUES (%s)
        RETURNING id
        """,
        (file.filename,)
    )

    document_id = cursor.fetchone()[0]

    for i, chunk in enumerate(chunks):

        embedding = model.encode(chunk)

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
                i,
                chunk,
                str(embedding.tolist())
            )
        )

    conn.commit()

    cursor.close()

    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunk_count": len(chunks)
    }


tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "document_search",
            "description": "Search uploaded documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query."
                    }
                },
                "required": ["query"]
            }
        }
    }
]


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

    chat_history = cursor.fetchall()[-2:]

    groq_messages = [
        {
            "role": "system",
            "content": """
You are an AI research assistant.

You have access to two tools:

1. web_search
   Use this when web information is required.

2. document_search
   Use this when information from uploaded documents is required.

Decide whether a tool is needed.

If a tool is not needed, answer directly.

Use tool results to produce the final answer.
"""
        }
    ]

    for role, content in chat_history:

        groq_messages.append(
            {
                "role": role,
                "content": content
            }
        )

    sources = []

    response = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=groq_messages,
        tools=tools,
        tool_choice="auto",
        reasoning_effort="low"
    )

    while True:

        assistant_message = response.choices[0].message

        tool_calls = assistant_message.tool_calls

        if not tool_calls:

            assistant_answer = assistant_message.content

            break

        groq_messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in tool_calls
                ]
            }
        )

        for tool_call in tool_calls:

            tool_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments
            )

            query = arguments["query"]

            if tool_name == "web_search":

                result = web_search(query)

                sources.extend(
                    [
                        {
                            "title": item["title"],
                            "url": item["url"]
                        }
                        for item in result
                    ]
                )

            elif tool_name == "document_search":

                result = document_search(
                    query,
                    request.document_id
                )

                sources.extend(
                    [
                        {
                            "type": "document",
                            "chunk_id": item["chunk_id"],
                            "chunk_index": item["chunk_index"],
                            "content": item["content"]
                        }
                        for item in result
                    ]
                )

            else:

                result = {
                    "error": "Unknown tool"
                }

            groq_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                }
            )

        response = groq.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=groq_messages,
            tools=tools,
            tool_choice="auto",
            reasoning_effort="low"
        )

    unique_sources = []

    seen_sources = set()

    for source in sources:

        if source.get("type") == "document":

            key = (
                source.get("type"),
                source.get("chunk_id")
            )

        else:

            key = source.get("url")

        if key not in seen_sources:

            seen_sources.add(key)

            unique_sources.append(source)

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
        "answer": assistant_answer,
        "sources": unique_sources
    }


@app.post("/research")
async def research(
    request: ResearchRequest
):

    response = tavily.search(
        request.query,
        max_results=5
    )

    sources = []

    for result in response["results"]:

        sources.append(
            {
                "title": result["title"],
                "url": result["url"],
                "content": result["content"]
            }
        )

    context = "\n\n".join(
        f"[{i}] Title: {source['title']}\n"
        f"Content: {source['content']}"
        for i, source in enumerate(
            sources,
            start=1
        )
    )

    llm_response = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": """
You are a research assistant.

Answer the user's question using only the provided sources.

Do not use outside knowledge.

If the provided sources do not contain enough information
to answer the question, clearly say that the sources are insufficient.
"""
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
        ],
        reasoning_effort="low"
    )

    answer = llm_response.choices[0].message.content

    return {
        "answer": answer,
        "sources": sources
    }