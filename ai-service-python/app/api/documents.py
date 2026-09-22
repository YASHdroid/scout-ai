from fastapi import APIRouter, File, UploadFile

from app.services.document_service import save_document

router = APIRouter()


@router.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    return save_document(file)