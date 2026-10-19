
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.internal_auth import verify_internal_service
from app.services.document_service import save_document

router = APIRouter()


@router.post("/documents")
async def upload_document(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(verify_internal_service),
):
    return save_document(file, user_id)
