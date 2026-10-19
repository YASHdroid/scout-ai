
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.internal_auth import verify_internal_service
from app.services.conversation_service import create_conversation

router = APIRouter()


class OwnedConversationRequest(BaseModel):
    document_id: int = Field(gt=0)
    user_id: int = Field(gt=0)


@router.post("/conversations")
def create(
    request: OwnedConversationRequest,
    _: None = Depends(verify_internal_service),
):
    conversation_id = create_conversation(
        request.document_id,
        request.user_id,
    )

    if conversation_id is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "conversation_id": conversation_id,
        "document_id": request.document_id,
    }
