from pydantic import BaseModel

class ResearchRequest(BaseModel):
    query: str

class ConversationRequest(BaseModel):
    document_id: int

class ChatRequest(BaseModel):
    conversation_id: int
    query: str
