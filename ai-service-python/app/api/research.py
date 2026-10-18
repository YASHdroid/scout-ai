
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import ResearchRequest
from app.rag.pipeline import run_chat
from app.rag.advanced_research import run_advanced_research


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Research"])


class DeepResearchRequest(BaseModel):
    query: str = Field(
        min_length=5,
        max_length=2000,
        description="The research question to investigate.",
    )

    document_id: int | None = Field(
        default=None,
        gt=0,
        description="Optional ID of the uploaded PDF.",
    )


@router.post("/research")
def standard_research(request: ResearchRequest):
    query = request.query.strip()

    if len(query) < 5:
        raise HTTPException(
            status_code=422,
            detail="Please provide a meaningful research question.",
        )

    if len(query) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Research query cannot exceed 2000 characters.",
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
            detail=(
                "Standard Research failed. "
                "Check the AI service logs."
            ),
        ) from error


@router.post("/research/advanced")
def advanced_research(request: DeepResearchRequest):
    """
    Run Advanced Research using web sources and, optionally,
    evidence retrieved from an uploaded PDF.
    """
    query = request.query.strip()
    document_id = request.document_id

    if len(query) < 5:
        raise HTTPException(
            status_code=422,
            detail="Please provide a meaningful research question.",
        )

    if len(query) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Research query cannot exceed 2000 characters.",
        )

    try:
        # Pass the optional PDF document ID into the research pipeline.
        result = run_advanced_research(
            query=query,
            document_id=document_id,
        )

        run_directory = Path(result["run_directory"])

        synthesis_path = (
            run_directory / "research_synthesis.json"
        )
        verification_path = (
            run_directory / "research_verification.json"
        )

        if not synthesis_path.exists():
            raise RuntimeError(
                "Research completed without a synthesis report."
            )

        if not verification_path.exists():
            raise RuntimeError(
                "Research completed without a verification report."
            )

        with synthesis_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            synthesis_report = json.load(file)

        with verification_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            verified_report = json.load(file)

        return {
            "success": True,
            "mode": "deep",
            "query": query,
            "run_id": result["run_id"],
            "summary": {
                "research_goal": result.get(
                    "research_goal", ""
                ),
                "sources_collected": result.get(
                    "sources_collected", 0
                ),
                "web_sources_included": result.get(
                    "web_sources_included", 0
                ),
                "pdf_sources_included": result.get(
                    "pdf_sources_included", 0
                ),
                "sources_analyzed": result.get(
                    "sources_analyzed", 0
                ),
                "key_findings": result.get(
                    "key_findings", 0
                ),
                "comparisons": result.get(
                    "comparisons", 0
                ),
                "candidate_research_gaps": result.get(
                    "candidate_research_gaps", 0
                ),
                "verification": result.get(
                    "verification_summary", {}
                ),
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
            detail=(
                "Advanced Research failed. "
                "Check the Python service logs for details."
            ),
        ) from error
