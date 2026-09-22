from app.services.llm import chat_completion
from app.rag.prompt import SYSTEM_PROMPT

def analyze_query(query: str) -> str:
    """
    Ask the LLM to classify the retrieval need.
    Returns one of: document, web, hybrid, direct.
    """

    response = chat_completion(
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT + """
For this routing task, return exactly one word:
document
web
hybrid
direct
"""
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )

    decision = (response or "").strip().lower()

    if "hybrid" in decision:
        return "hybrid"
    if "document" in decision:
        return "document"
    if "web" in decision:
        return "web"

    return "direct"
