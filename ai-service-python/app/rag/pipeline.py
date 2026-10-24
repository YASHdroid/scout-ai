
import json
import logging

from app.rag.retriever import retrieve_chunks
from app.rag.reranker import rerank_chunks
from app.services.search import web_search
from app.rag.tool_args import InvalidToolArguments, parse_tool_arguments
from app.services.llm import (
    ToolCallGenerationError,
    chat_completion,
    chat_completion_with_tools,
)

logger = logging.getLogger(__name__)

# Invalid tool calls tolerated per request. The first one is returned to the
# model as an error so it can correct itself; reaching this count aborts.
MAX_INVALID_TOOL_CALLS = 2


def document_search(
    query: str,
    document_id: int,
    top_k: int = 8,
):
    """
    Retrieve a wider set of chunks from the selected document,
    rerank them, and return the strongest matches.
    """

    chunks = retrieve_chunks(
        query=query,
        document_id=document_id,
        top_k=max(top_k * 4, 30),
        min_similarity=0.0,
    )

    print(f"[Scout] Retrieved {len(chunks)} chunks for: {query}")

    if not chunks:
        return []

    results = rerank_chunks(
        query=query,
        chunks=chunks,
        top_k=top_k,
    )

    print(f"[Scout] Reranked {len(results)} chunks")

    for i, chunk in enumerate(results, start=1):
        if not isinstance(chunk, dict):
            continue

        content = chunk.get("content", "")

        print(f"\n--- DOCUMENT CHUNK {i} ---")
        print("Chunk ID:", chunk.get("chunk_id"))
        print("Chunk index:", chunk.get("chunk_index"))
        print("Similarity:", chunk.get("similarity"))
        print("Content:", content[:700])

    return results


def targeted_document_search(
    query: str,
    document_id: int,
    top_k: int = 8,
):
    """
    For Modular RAG questions, search separately for the main
    section, modules, and retrieval patterns. Merge duplicate
    chunks before returning evidence to the agent.
    """

    query_lower = query.lower()

    modular_terms = [
        "modular rag",
        "new modules",
        "new patterns",
        "rag-fusion",
        "task adapter",
        "iterative retrieval",
        "adaptive retrieval",
    ]

    is_modular_question = any(
        term in query_lower for term in modular_terms
    )

    if not is_modular_question:
        return document_search(
            query=query,
            document_id=document_id,
            top_k=top_k,
        )

    focused_queries = [
        "C. Modular RAG architecture definition and workflow",
        "Modular RAG New Modules Search RAG-Fusion Memory Routing Predict Task Adapter",
        "Modular RAG New Patterns iterative retrieval adaptive retrieval",
        "Search module RAG-Fusion module Memory module Routing module Predict module Task Adapter module",
    ]

    collected = {}

    for focused_query in focused_queries:
        try:
            results = document_search(
                query=focused_query,
                document_id=document_id,
                top_k=top_k,
            )

            for item in results:
                if not isinstance(item, dict):
                    continue

                chunk_id = item.get("chunk_id")

                if chunk_id is not None:
                    collected[chunk_id] = item

        except Exception as exc:
            print(
                f"[Scout] Focused search failed for "
                f"'{focused_query}': {exc}"
            )

    # Fall back to the original query if focused searches
    # did not return usable evidence.
    if not collected:
        return document_search(
            query=query,
            document_id=document_id,
            top_k=top_k,
        )

    merged_chunks = list(collected.values())

    # Rerank the combined evidence against the user's actual query.
    final_results = rerank_chunks(
        query=query,
        chunks=merged_chunks,
        top_k=max(top_k, 12),
    )

    print(
        f"[Scout] Combined {len(merged_chunks)} unique chunks; "
        f"selected {len(final_results)}"
    )

    return final_results


# ---------------------------------------------------------
# TOOL DEFINITIONS
# ---------------------------------------------------------

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current, recent, external, "
            "or online information. Never use this tool when "
            "the user explicitly requests document-only research."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A clear, standalone search query.",
                }
            },
            "required": ["query"],
        },
    },
}


DOCUMENT_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "document_search",
        "description": (
            "Search the uploaded document for relevant evidence. "
            "Use focused queries for individual sections, headings, "
            "figures, modules, and technical concepts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A focused query describing the information "
                        "to find in the uploaded document."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}


# ---------------------------------------------------------
# AGENT SYSTEM PROMPT
# ---------------------------------------------------------

AGENT_SYSTEM_PROMPT = """
You are Scout, an AI research agent.

Your priority is factual accuracy, evidence traceability, and
answering the user's actual question.

You have two tools:
1. document_search: search the user's uploaded document.
2. web_search: search the public web.

TOOL SELECTION
- If the user asks about an uploaded PDF, paper, file, figure,
  table, or section, search the uploaded document.
- If the user asks for current or external information, use web search.
- If the user explicitly requests both document evidence and
  external research, use both unless document-only restrictions apply.
- Never claim a tool was used unless it was actually called.

DOCUMENT-ONLY MODE
When the user says "using only the uploaded PDF", "based only on
the paper", "do not use external sources", or equivalent:
- Use only retrieved document evidence.
- Do not call web_search.
- Do not add external URLs or external citations.
- Do not fill gaps with general knowledge or assumptions.
- Preserve the paper's terminology and organization.
- If a detail is missing from one search, search again with a
  narrower query before saying it could not be verified.
- If evidence remains unavailable, say:
  "This detail could not be verified from the retrieved PDF text."
- Do not claim the entire PDF lacks information just because
  the current chunks do not contain it.

DOCUMENT EVIDENCE
- Read the actual content of retrieved chunks.
- Every substantive claim about the paper must be supported
  by the retrieved text.
- Do not infer a module's function from its name alone.
- Do not invent implementation details, APIs, algorithms,
  experimental results, or performance claims.
- Distinguish statements explicitly made by the paper from
  interpretations.
- If the evidence supports only part of a claim, state only
  the supported part.
- Search for each important subtopic separately when needed.

MODULAR RAG
For questions about Modular RAG, search for:
- C. Modular RAG
- New Modules
- New Patterns
- Search
- RAG-Fusion
- Memory
- Routing
- Predict
- Task Adapter
- iterative retrieval
- adaptive retrieval

Explain each requested module only to the extent supported
by the retrieved passages. Do not invent missing details.

PAGE NUMBERS
- Never use chunk_index as a page number.
- Never invent printed page numbers.
- Distinguish printed page numbers from PDF viewer page numbers.
- If page metadata or visible printed page numbers cannot be
  verified, explicitly say the page number could not be verified.
- Do not fabricate quotations, citations, or page references.

FINAL ANSWER
- Answer the question directly with clear headings.
- Use a comparison table when it improves clarity.
- Include relevant evidence and page references only when verified.
- Identify specific unverified details without dismissing the
  whole document.
- Do not add external sources in document-only mode.
- Do not claim the research is complete when requested evidence
  is still missing.
"""


# ---------------------------------------------------------
# SOURCE CONVERSION
# ---------------------------------------------------------

def execute_tool(
    tool_name: str,
    arguments: dict,
    document_id: int | None,
    document_only: bool = False,
):
    if tool_name == "web_search":
        if document_only:
            return {
                "error": (
                    "Web search is disabled because the user "
                    "requested document-only research."
                )
            }

        query = arguments.get("query")

        if not isinstance(query, str) or not query.strip():
            return {"error": "A non-empty 'query' string is required."}

        query = query.strip()

        results = web_search(
            query=query,
            max_results=5,
        )

        tool_sources = []

        for item in results or []:
            tool_sources.append(
                {
                    "type": "web",
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content", ""),
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

        query = arguments.get("query")

        if not isinstance(query, str) or not query.strip():
            return {"error": "A non-empty 'query' string is required."}

        query = query.strip()

        results = targeted_document_search(
            query=query,
            document_id=document_id,
            top_k=8,
        )

        tool_sources = []

        for item in results:
            if not isinstance(item, dict):
                continue

            tool_sources.append(
                {
                    "type": "document",
                    "chunk_id": item.get("chunk_id"),
                    "chunk_index": item.get("chunk_index"),
                    "content": item.get("content", ""),
                    "similarity": item.get("similarity"),
                    "rerank_score": item.get("rerank_score"),
                }
            )

        return tool_sources

    return {"error": f"Unknown tool: {tool_name}"}



DOCUMENT_PHRASES = [
    "uploaded paper",
    "uploaded document",
    "uploaded pdf",
    "uploaded file",
    "uploaded survey",
    "uploaded research paper",
    "according to the paper",
    "according to the document",
    "according to the pdf",
    "according to the file",
    "according to the survey",
    "in the paper",
    "in the document",
    "in the pdf",
    "in the file",
    "in the survey",
    "my paper",
    "my document",
    "my pdf",
    "my file",
    "this paper",
    "this document",
    "this pdf",
    "this survey",
    "section ii-c",
    "figure in the paper",
    "table in the paper",
]

DOCUMENT_ONLY_PHRASES = [
    "using only",
    "based only on",
    "based solely on",
    "only use the",
    "use only the",
    "do not use external",
    "without external sources",
    "document only",
    "pdf only",
    "paper only",
    "no external sources",
]


def is_explicit_document_request(query: str) -> bool:
    query_lower = query.lower()

    return any(
        phrase in query_lower
        for phrase in DOCUMENT_PHRASES
    )


def is_document_only_request(query: str) -> bool:
    query_lower = query.lower()

    return (
        any(
            phrase in query_lower
            for phrase in DOCUMENT_ONLY_PHRASES
        )
        and (
            is_explicit_document_request(query)
            or "pdf" in query_lower
            or "paper" in query_lower
            or "document" in query_lower
            or "survey" in query_lower
            or "source" in query_lower
        )
    )


def run_agent(
    query: str,
    document_id: int | None = None,
    history=None,
):
    if history is None:
        history = []

    document_available = document_id is not None
    explicit_document_request = is_explicit_document_request(query)
    document_only = is_document_only_request(query)

    system_prompt = AGENT_SYSTEM_PROMPT

    if document_available:
        system_prompt += "\nAn uploaded document IS available."
    else:
        system_prompt += "\nNO uploaded document is available."

    if document_only:
        system_prompt += (
            "\n\nSTRICT MODE ACTIVE: DOCUMENT ONLY. "
            "Do not call web_search. Use only evidence "
            "retrieved from the uploaded document."
        )

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    for role, content in history[-6:]:
        if role in ("user", "assistant"):
            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    tools = []

    # Never expose the web tool to the model in document-only mode.
    if not document_only:
        tools.append(WEB_SEARCH_TOOL)

    if document_available:
        tools.append(DOCUMENT_SEARCH_TOOL)

    all_sources = []
    tool_call_count = 0
    invalid_tool_call_count = 0
    max_tool_calls = 10

    exposed_tools = {
        tool["function"]["name"]: tool["function"]["parameters"]
        for tool in tools
    }

    if explicit_document_request and document_available:
        document_results = targeted_document_search(
            query=query,
            document_id=document_id,
            top_k=8,
        )

        tool_call_count += 1

        all_sources.extend(
            document_results if isinstance(document_results, list) else []
        )

        document_context = json.dumps(
            document_results,
            ensure_ascii=False,
        )

        messages.append(
            {
                "role": "system",
                "content": (
                    "Document evidence retrieved for the user's "
                    "question is provided below. Inspect the actual "
                    "content. If evidence is incomplete, use "
                    "document_search with narrower queries. "
                    "Do not invent page numbers or unsupported facts.\n\n"
                    f"{document_context}"
                ),
            }
        )

    while tool_call_count < max_tool_calls:
        # May raise ToolCallGenerationError after bounded retries.
        response = chat_completion_with_tools(
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else "none",
        )

        assistant_message = response.choices[0].message

        if not assistant_message.tool_calls:
            answer = assistant_message.content or ""

            return (
                answer,
                _unique_sources(all_sources),
            )

        # Validate every call BEFORE building history, so malformed
        # arguments are never echoed back to the provider.
        validated = []

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name

            try:
                if tool_name not in exposed_tools:
                    raise InvalidToolArguments(
                        f"Tool '{tool_name}' is not available."
                    )

                arguments = parse_tool_arguments(
                    tool_call.function.arguments,
                    exposed_tools[tool_name],
                )
                error = None
            except InvalidToolArguments as exc:
                arguments = None
                error = str(exc)

            validated.append((tool_call, arguments, error))

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
                            "arguments": (
                                tool_call.function.arguments
                                if error is None
                                else "{}"
                            ),
                        },
                    }
                    for tool_call, _, error in validated
                ],
            }
        )

        # Every tool_call id gets exactly one tool reply.
        for tool_call, arguments, error in validated:
            tool_name = tool_call.function.name

            if error is not None:
                invalid_tool_call_count += 1
                tool_call_count += 1

                logger.warning(
                    "Rejected tool call '%s': %s (invalid=%d/%d)",
                    tool_name,
                    error,
                    invalid_tool_call_count,
                    MAX_INVALID_TOOL_CALLS,
                )

                result = {
                    "error": (
                        f"{error} The tool was not executed. "
                        "Call it again with valid JSON arguments "
                        "that match the schema."
                    )
                }
            elif tool_call_count >= max_tool_calls:
                result = {
                    "error": (
                        "Tool call limit reached; this call was "
                        "not executed."
                    )
                }
            else:
                result = execute_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    document_id=document_id,
                    document_only=document_only,
                )

                tool_call_count += 1

                if isinstance(result, list):
                    all_sources.extend(result)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                        default=str,
                    ),
                }
            )

        if invalid_tool_call_count >= MAX_INVALID_TOOL_CALLS:
            raise ToolCallGenerationError(
                "The language model repeatedly produced invalid tool "
                "arguments. Please try again."
            )

    final_response = chat_completion(
        messages=messages,
        reasoning_effort="low",
    )

    # Support either a plain string or an SDK-style response object.
    if isinstance(final_response, str):
        answer = final_response
    elif hasattr(final_response, "choices"):
        answer = (
            final_response.choices[0].message.content
            if final_response.choices
            else ""
        )
    else:
        answer = str(final_response)

    return (
        answer,
        _unique_sources(all_sources),
    )



def run_chat(
    query: str,
    document_id=None,
    history=None,
):
    if history is None:
        history = []

    explicit_document_request = is_explicit_document_request(query)

    if explicit_document_request and document_id is None:
        return (
            "I don't have an uploaded document attached to this "
            "conversation. Please upload the document and try again.",
            [],
        )

    return run_agent(
        query=query,
        document_id=document_id,
        history=history,
    )


# ---------------------------------------------------------
# DEDUPLICATE SOURCES
# ---------------------------------------------------------

def _unique_sources(sources):
    result = []
    seen = set()

    for source in sources:
        if not isinstance(source, dict):
            continue

        if source.get("type") == "document":
            key = (
                "document",
                source.get("chunk_id"),
            )
        else:
            key = (
                "web",
                source.get("url"),
            )

        if key in seen:
            continue

        seen.add(key)
        result.append(source)

    return result
