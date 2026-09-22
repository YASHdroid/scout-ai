import json

from app.rag.retriever import retrieve_chunks
from app.rag.reranker import rerank_chunks
from app.services.search import web_search
from app.services.llm import chat_completion_with_tools
from app.rag.prompt import SYSTEM_PROMPT


def document_search(
    query: str,
    document_id: int,
    top_k: int = 5
):
    chunks = retrieve_chunks(
        query=query,
        document_id=document_id,
        top_k=max(top_k * 2, 8)
    )

    return rerank_chunks(
        query=query,
        chunks=chunks,
        top_k=top_k
    )


def run_chat(
    query: str,
    document_id: int,
    history=None
):

    if history is None:
        history = []

    sources = []

    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web when current, recent, external, or online information is needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query."
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
                "description": "Search the user's uploaded document when the answer should come from that document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The document retrieval query."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    for role, content in history:
        messages.append(
            {
                "role": role,
                "content": content
            }
        )

    messages.append(
        {
            "role": "user",
            "content": query
        }
    )

    response = chat_completion_with_tools(
        messages=messages,
        tools=tools
    )

    while True:

        assistant_message = response.choices[0].message

        tool_calls = assistant_message.tool_calls

        if not tool_calls:
            return (
                assistant_message.content,
                _unique_sources(sources)
            )

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": call.type,
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments
                        }
                    }
                    for call in tool_calls
                ]
            }
        )

        for call in tool_calls:

            name = call.function.name

            args = json.loads(
                call.function.arguments
            )

            tool_query = args["query"]

            if name == "document_search":

                result = document_search(
                    query=tool_query,
                    document_id=document_id,
                    top_k=5
                )

                tool_result = [
                    {
                        "chunk_id": item["chunk_id"],
                        "chunk_index": item["chunk_index"],
                        "content": item["content"],
                        "score": item.get("rerank_score")
                    }
                    for item in result
                ]

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

            elif name == "web_search":

                result = web_search(tool_query)

                tool_result = [
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "content": item.get("content")
                    }
                    for item in result
                ]

                sources.extend(
                    [
                        {
                            "type": "web",
                            "title": item.get("title"),
                            "url": item.get("url")
                        }
                        for item in result
                    ]
                )

            else:

                tool_result = {
                    "error": "Unknown tool"
                }

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(tool_result)
                }
            )

        response = chat_completion_with_tools(
            messages=messages,
            tools=tools
        )


def _unique_sources(sources):

    result = []

    seen = set()

    for source in sources:

        if source.get("type") == "document":

            key = (
                "document",
                source.get("chunk_id")
            )

        else:

            key = (
                "web",
                source.get("url")
            )

        if key not in seen:

            seen.add(key)

            result.append(source)

    return result