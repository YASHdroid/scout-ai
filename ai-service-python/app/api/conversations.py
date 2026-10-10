from fastapi import APIRouter

from app.models.schemas import ConversationRequest
from app.services.conversation_service import create_conversation


router = APIRouter()


@router.post("/conversations")
async def create(request: ConversationRequest):

    conversation_id = create_conversation(
        request.document_id
    )

    return {
        "conversation_id": conversation_id,
        "document_id": request.document_id
    }