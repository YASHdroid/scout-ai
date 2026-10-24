
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.internal_auth import verify_internal_service
from app.services.conversation_service import (
    get_conversation_document,
    get_recent_messages,
    save_message,
)
from app.rag.pipeline import run_chat
from app.services.llm import ToolCallGenerationError

router = APIRouter()


class OwnedChatRequest(BaseModel):
    conversation_id: int = Field(gt=0)
    query: str = Field(min_length=1, max_length=2000)
    user_id: int = Field(gt=0)


@router.post("/chat")
def chat(
    request: OwnedChatRequest,
    _: None = Depends(verify_internal_service),
):
    document_id, conversation_exists = get_conversation_document(
        request.conversation_id,
        request.user_id,
    )

    if not conversation_exists:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    save_message(
        request.conversation_id,
        "user",
        request.query,
    )

    history = get_recent_messages(
        request.conversation_id,
        limit=10,
    )

    previous_history = history[:-1]

    try:
        answer, sources = run_chat(
            query=request.query,
            document_id=document_id,
            history=previous_history,
        )
    except ToolCallGenerationError:
        raise HTTPException(
            status_code=502,
            detail=(
                "The AI model failed to produce a valid search request. "
                "Please try again."
            ),
        ) from None

    save_message(
        request.conversation_id,
        "assistant",
        answer,
    )

    return {
        "conversation_id": request.conversation_id,
        "query": request.query,
        "answer": answer,
        "sources": sources,
    }
