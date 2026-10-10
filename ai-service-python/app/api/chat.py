from fastapi import APIRouter

from app.models.schemas import ChatRequest

from app.services.conversation_service import (
    get_conversation_document,
    get_recent_messages,
    save_message
)

from app.rag.pipeline import run_chat


router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):

    document_id, conversation_exists = get_conversation_document(
        request.conversation_id
    )

    if not conversation_exists:

        return {
            "error": "Conversation not found"
        }

    save_message(
        request.conversation_id,
        "user",
        request.query
    )

    history = get_recent_messages(
        request.conversation_id,
        limit=10
    )

    previous_history = history[:-1]

    answer, sources = run_chat(
        query=request.query,
        document_id=document_id,
        history=previous_history
    )

    save_message(
        request.conversation_id,
        "assistant",
        answer
    )

    return {
        "conversation_id": request.conversation_id,
        "query": request.query,
        "answer": answer,
        "sources": sources
    }