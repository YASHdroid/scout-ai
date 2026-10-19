
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_connection
from app.core.internal_auth import verify_internal_service
from app.models.schemas import ResearchRequest
from app.rag.pipeline import run_chat
from app.rag.advanced_research import run_advanced_research


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Research"])


class DeepResearchRequest(BaseModel):
    query: str = Field(min_length=5, max_length=2000)
    user_id: int = Field(gt=0)
    document_id: int | None = Field(default=None, gt=0)


def verify_document_owner(document_id: int, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM documents
            WHERE id = %s AND user_id = %s
            """,
            (document_id, user_id),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


@router.post("/research")
def standard_research(
    request: ResearchRequest,
    _: None = Depends(verify_internal_service),
):
    query = request.query.strip()

    if len(query) < 5 or len(query) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Research query must contain 5 to 2000 characters.",
        )

    try:
        answer, sources = run_chat(
            query=query,
            document_id=None,
            history=[],
        )

        return {
            "success": True,
            "mode": "standard",
            "query": query,
            "answer": answer,
            "sources": sources,
        }

    except Exception as error:
        logger.exception("Standard Research failed.")
        raise HTTPException(
            status_code=502,
            detail="Standard Research failed. Check the AI service logs.",
        ) from error


@router.post("/research/advanced")
def advanced_research(
    request: DeepResearchRequest,
    _: None = Depends(verify_internal_service),
):
    query = request.query.strip()
    document_id = request.document_id
    user_id = request.user_id

    if len(query) < 5 or len(query) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Research query must contain 5 to 2000 characters.",
        )

    if document_id is not None:
        try:
            owns_document = verify_document_owner(document_id, user_id)
        except Exception as error:
            logger.exception("Document ownership check failed.")
            raise HTTPException(
                status_code=500,
                detail="Could not verify document ownership.",
            ) from error

        if not owns_document:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

    try:
        result = run_advanced_research(
            query=query,
            document_id=document_id,
        )

        run_directory = Path(result["run_directory"])
        synthesis_path = run_directory / "research_synthesis.json"
        verification_path = run_directory / "research_verification.json"

        if not synthesis_path.exists():
            raise RuntimeError(
                "Research completed without a synthesis report."
            )

        if not verification_path.exists():
            raise RuntimeError(
                "Research completed without a verification report."
            )

        with synthesis_path.open("r", encoding="utf-8") as file:
            synthesis_report = json.load(file)

        with verification_path.open("r", encoding="utf-8") as file:
            verified_report = json.load(file)

        return {
            "success": True,
            "mode": "deep",
            "query": query,
            "run_id": result["run_id"],
            "summary": {
                "research_goal": result.get("research_goal", ""),
                "sources_collected": result.get("sources_collected", 0),
                "web_sources_included": result.get("web_sources_included", 0),
                "pdf_sources_included": result.get("pdf_sources_included", 0),
                "sources_analyzed": result.get("sources_analyzed", 0),
                "key_findings": result.get("key_findings", 0),
                "comparisons": result.get("comparisons", 0),
                "candidate_research_gaps": result.get(
                    "candidate_research_gaps", 0
                ),
                "verification": result.get("verification_summary", {}),
            },
            "report": synthesis_report,
            "verification": verified_report,
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Advanced Research API failed.")
        raise HTTPException(
            status_code=500,
            detail="Advanced Research failed. Check the Python service logs.",
        ) from error
