import json

from app.rag.retriever import retrieve_chunks
from app.rag.reranker import rerank_chunks
from app.services.search import web_search
from app.services.llm import (
    chat_completion,
    chat_completion_with_tools
)


def document_search(
    query: str,
    document_id: int,
    top_k: int = 5
):
    chunks = retrieve_chunks(
        query=query,
        document_id=document_id,
        top_k=max(top_k * 2, 8),
        min_similarity=0.0
    )

    print("RETRIEVED CHUNKS:", len(chunks))

    results = rerank_chunks(
        query=query,
        chunks=chunks,
        top_k=top_k
    )

    print("RERANKED CHUNKS:", len(results))

    return results

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current, recent, external, "
            "or online information. Use this when the user "
            "needs information that may not be available "
            "inside the uploaded document."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A clear standalone search query."
                    )
                }
            },
            "required": ["query"]
        }
    }
}


DOCUMENT_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "document_search",
        "description": (
            "Search the user's uploaded document for "
            "information relevant to the user's question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A clear query describing what "
                        "information to find in the document."
                    )
                }
            },
            "required": ["query"]
        }
    }
}


AGENT_SYSTEM_PROMPT = """
You are Scout, an AI research agent.

Your job is to research the user's question and provide
a grounded, useful answer.

You have access to these tools:

1. web_search
   - Search the web for current, recent, external,
     or online information.

2. document_search
   - Search the user's uploaded document for relevant
     information.

Decision rules:

- Use document_search when the user asks about the
  uploaded document, paper, PDF, or information that
  should come from the uploaded document.

- If the user explicitly refers to an uploaded paper,
  uploaded document, uploaded PDF, or says
  "according to the paper/document/PDF", you MUST use
  document_search before providing the final answer,
  even if the conversation history already contains
  information about the topic.

- Use web_search when current, recent, external, or
  online information is required.

- Use both tools when the question requires both
  information from the uploaded document and external
  information.

- You may call a tool multiple times when additional
  information is genuinely needed.

- Do not use a tool when the question can be answered
  from the available conversation context alone.

- Never claim that you searched the web unless
  web_search was actually used.

- Never claim that you searched the uploaded document
  unless document_search was actually used.

- Use the retrieved evidence to construct the final answer.

- When enough information has been collected, stop using
  tools and provide the final answer.

Keep the final answer clear and directly related to
the user's question.
"""


def execute_tool(
    tool_name: str,
    arguments: dict,
    document_id: int | None
):
    if tool_name == "web_search":

        query = arguments.get("query", "")

        results = web_search(
            query=query,
            max_results=5
        )

        tool_sources = []

        for item in results:
            tool_sources.append(
                {
                    "type": "web",
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get(
                        "content",
                        ""
                    )
                }
            )

        return tool_sources

    if tool_name == "document_search":

        if document_id is None:
            return {
                "error": (
                    "No uploaded document is attached "
                    "to this conversation."
                )
            }

        query = arguments.get("query", "")

        results = document_search(
            query=query,
            document_id=document_id,
            top_k=5
        )

        tool_sources = []

        for item in results:
            tool_sources.append(
                {
                    "type": "document",
                    "chunk_id": item.get("chunk_id"),
                    "chunk_index": item.get(
                        "chunk_index"
                    ),
                    "content": item.get(
                        "content",
                        ""
                    )
                }
            )

        return tool_sources

    return {
        "error": f"Unknown tool: {tool_name}"
    }


def run_agent(
    query: str,
    document_id: int | None = None,
    history=None
):

    if history is None:
        history = []

    document_available = document_id is not None

    explicit_document_request = any(
        phrase in query.lower()
        for phrase in [
            "uploaded paper",
            "uploaded document",
            "uploaded pdf",
            "uploaded file",
            "according to the paper",
            "according to the document",
            "according to the pdf",
            "according to the file",
            "in the paper",
            "in the document",
            "in the pdf",
            "in the file",
            "my paper",
            "my document",
            "my pdf",
            "my file"
        ]
    )

    messages = [
        {
            "role": "system",
            "content": (
                AGENT_SYSTEM_PROMPT
                +
                (
                    "\nAn uploaded document IS available."
                    if document_available
                    else
                    "\nNO uploaded document is available."
                )
            )
        }
    ]

    for role, content in history[-6:]:
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

    tools = [
        WEB_SEARCH_TOOL
    ]

    if document_available:
        tools.append(
            DOCUMENT_SEARCH_TOOL
        )

    all_sources = []
    tool_call_count = 0
    max_tool_calls = 5

    if (
        explicit_document_request
        and document_available
    ):

        document_results = execute_tool(
            tool_name="document_search",
            arguments={
                "query": query
            },
            document_id=document_id
        )

        tool_call_count += 1

        if isinstance(document_results, list):
            for source in document_results:
                all_sources.append(source)

        document_context = json.dumps(
            document_results,
            ensure_ascii=False
        )

        messages.append(
            {
                "role": "system",
                "content": f"""
A document search was executed because the user
explicitly asked about the uploaded document.

Here are the retrieved document results:

{document_context}

Use these retrieved document results when answering
the user's question.
"""
            }
        )

    while tool_call_count < max_tool_calls:

        response = chat_completion_with_tools(
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        if not assistant_message.tool_calls:

            answer = assistant_message.content

            return (
                answer,
                _unique_sources(all_sources)
            )

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in assistant_message.tool_calls
                ]
            }
        )

        for tool_call in assistant_message.tool_calls:

            if tool_call_count >= max_tool_calls:
                break

            tool_name = (
                tool_call.function.name
            )

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )
            except json.JSONDecodeError:
                arguments = {}

            result = execute_tool(
                tool_name=tool_name,
                arguments=arguments,
                document_id=document_id
            )

            tool_call_count += 1

            if isinstance(result, list):
                for source in result:
                    all_sources.append(source)

            tool_content = json.dumps(
                result,
                ensure_ascii=False
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_content
                }
            )

    final_response = chat_completion(
        messages=messages,
        reasoning_effort="low"
    )

    return (
        final_response,
        _unique_sources(all_sources)
    )


def run_chat(
    query: str,
    document_id=None,
    history=None
):

    if history is None:
        history = []

    document_phrases = [
        "uploaded paper",
        "uploaded document",
        "uploaded pdf",
        "uploaded file",
        "according to the paper",
        "according to the document",
        "according to the pdf",
        "according to the file",
        "in the paper",
        "in the document",
        "in the pdf",
        "in the file",
        "my paper",
        "my document",
        "my pdf",
        "my file"
    ]

    explicit_document_request = any(
        phrase in query.lower()
        for phrase in document_phrases
    )

    if (
        explicit_document_request
        and document_id is None
    ):
        return (
            "I don't have an uploaded document attached "
            "to this conversation. Please upload a document "
            "and start a conversation with it.",
            []
        )

    return run_agent(
        query=query,
        document_id=document_id,
        history=history
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