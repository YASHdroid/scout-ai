
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
            detail="Standard Research failed. Check the AI service logs.",
        ) from error


@router.post("/research/advanced")
def advanced_research(request: DeepResearchRequest):
    """
    Run Scout's advanced research pipeline.

    Return the synthesized research report separately from
    the evidence verification results.
    """
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
        # Run the existing planning, search, analysis,
        # synthesis, and verification pipeline.
        result = run_advanced_research(query)

        run_directory = Path(result["run_directory"])

        synthesis_path = (
            run_directory / "research_synthesis.json"
        )
        verification_path = (
            run_directory / "research_verification.json"
        )

        # The synthesized report contains the research findings.
        if not synthesis_path.exists():
            raise RuntimeError(
                "Research completed without a synthesis report."
            )

        # Verification is returned separately from the report.
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
                "research_goal": result["research_goal"],
                "sources_collected": result["sources_collected"],
                "sources_analyzed": result["sources_analyzed"],
                "key_findings": result["key_findings"],
                "comparisons": result["comparisons"],
                "candidate_research_gaps": (
                    result["candidate_research_gaps"]
                ),
                "verification": result["verification_summary"],
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
