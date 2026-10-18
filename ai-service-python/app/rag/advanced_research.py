
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from app.rag.pipeline import document_search
from app.rag.research_planner import create_research_plan
from app.rag.research_executor import execute_research_plan
from app.rag.research_analyzer import analyze_research_sources
from app.rag.research_synthesizer import synthesize_research_findings
from app.rag.research_verifier import verify_research_report

logger = logging.getLogger(__name__)

MAX_SOURCES = 10
MAX_PDF_CHUNKS = 8

DOCUMENT_ONLY_PHRASES = [
    "using only",
    "based only on",
    "based solely on",
    "only use",
    "use only",
    "do not use external",
    "without external sources",
    "no external sources",
    "document only",
    "pdf only",
    "paper only",
]


def is_document_only_query(query: str) -> bool:
    """Identify requests that explicitly prohibit external sources."""

    text = query.lower()

    asks_about_document = any(
        term in text
        for term in [
            "pdf",
            "paper",
            "document",
            "uploaded file",
            "uploaded survey",
        ]
    )

    prohibits_external = any(
        phrase in text
        for phrase in DOCUMENT_ONLY_PHRASES
    )

    return asks_about_document and prohibits_external


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def run_advanced_research(
    query,
    output_root="research_runs",
    document_id=None,
):
    query = query.strip()

    if len(query) < 5 or len(query) > 2000:
        raise ValueError(
            "Query must be between 5 and 2000 characters."
        )

    document_only = is_document_only_query(query)

    if document_only and document_id is None:
        raise ValueError(
            "This request requires an uploaded PDF, but no "
            "document_id was provided."
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        query.lower(),
    ).strip("-")[:40]

    run_id = f"{timestamp}_{slug}"
    run_dir = Path(output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    status_path = run_dir / "run_status.json"

    status = {
        "run_id": run_id,
        "status": "running",
        "current_stage": "planning",
        "document_only": document_only,
    }

    def update_stage(stage):
        status["current_stage"] = stage
        save_json(status_path, status)

        print(
            f"\n[Scout] {stage.replace('_', ' ').title()}...",
            flush=True,
        )

    try:
        # 1. Planning
        update_stage("planning")

        plan = create_research_plan(query)

        save_json(run_dir / "research_plan.json", plan)

        # 2. Run web research only when allowed.
        web_sources = []
        research_data = {
            "query": query,
            "research_goal": plan.get("research_goal", ""),
            "sources": [],
            "document_only": document_only,
        }

        if not document_only:
            update_stage("searching")

            research_data = execute_research_plan(plan)

            if not isinstance(research_data, dict):
                raise ValueError(
                    "Research executor returned invalid data."
                )

            raw_web_sources = research_data.get("sources", [])

            if not isinstance(raw_web_sources, list):
                raise ValueError(
                    "Research executor did not return a valid source list."
                )

            web_sources = [
                source
                for source in raw_web_sources
                if isinstance(source, dict)
                and isinstance(source.get("url"), str)
                and source["url"].strip()
                and isinstance(source.get("content"), str)
                and source["content"].strip()
            ]

        # 3. Retrieve PDF evidence.
        pdf_sources = []

        if document_id is not None:
            update_stage("reading_pdf")

            # Search focused topics separately to improve coverage.
            search_queries = [query]

            query_lower = query.lower()

            if any(
                term in query_lower
                for term in [
                    "modular rag",
                    "rag-fusion",
                    "task adapter",
                    "iterative retrieval",
                    "adaptive retrieval",
                ]
            ):
                search_queries = [
                    "C. Modular RAG",
                    "Modular RAG New Modules Search RAG-Fusion Memory Routing Predict Task Adapter",
                    "Modular RAG New Patterns iterative retrieval adaptive retrieval",
                    query,
                ]

            seen_chunks = {}

            for search_query in search_queries:
                chunks = document_search(
                    query=search_query,
                    document_id=document_id,
                    top_k=MAX_PDF_CHUNKS,
                )

                if not isinstance(chunks, list):
                    continue

                for chunk in chunks:
                    if not isinstance(chunk, dict):
                        continue

                    content = chunk.get("content", "")

                    if (
                        not isinstance(content, str)
                        or not content.strip()
                    ):
                        continue

                    chunk_id = chunk.get("chunk_id")

                    if chunk_id is not None:
                        key = str(chunk_id)
                    else:
                        key = (
                            str(chunk.get("chunk_index"))
                            + content[:100]
                        )

                    if key not in seen_chunks:
                        seen_chunks[key] = chunk

            for index, chunk in enumerate(
                seen_chunks.values(),
                start=1,
            ):
                chunk_id = chunk.get("chunk_id")
                chunk_index = chunk.get("chunk_index")
                content = chunk["content"].strip()

                chunk_ref = (
                    chunk_id
                    if chunk_id is not None
                    else chunk_index
                    if chunk_index is not None
                    else index
                )

                pdf_sources.append({
                    "type": "document",
                    "source_type": "pdf",
                    "title": f"Uploaded PDF - Chunk {index}",
                    "url": (
                        f"scout-pdf://document/"
                        f"{document_id}/chunk/{chunk_ref}"
                    ),
                    "content": content,
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                })

        # 4. Select sources.
        selected_pdf_sources = pdf_sources[:MAX_SOURCES]

        if document_only:
            # Hard boundary: external sources cannot enter this run.
            sources = selected_pdf_sources
        else:
            remaining_capacity = (
                MAX_SOURCES - len(selected_pdf_sources)
            )
            sources = (
                selected_pdf_sources
                + web_sources[:remaining_capacity]
            )

        if not sources:
            raise ValueError(
                "No usable sources were found. "
                "Check document attachment and retrieval results."
            )

        research_data["sources"] = sources
        research_data["document_only"] = document_only
        research_data["pdf_sources_included"] = len(
            selected_pdf_sources
        )
        research_data["web_sources_included"] = (
            0 if document_only
            else len(sources) - len(selected_pdf_sources)
        )

        if document_id is not None:
            research_data["document_id"] = document_id

        save_json(
            run_dir / "research_data.json",
            research_data,
        )

        # 5. Analyze the selected evidence.
        analysis_input = dict(research_data)
        analysis_input["sources"] = sources
        analysis_input["document_only"] = document_only

        update_stage("analyzing")

        analysis = analyze_research_sources(analysis_input)

        if not isinstance(analysis, dict):
            raise ValueError(
                "Research analyzer returned invalid data."
            )

        save_json(
            run_dir / "research_analysis.json",
            analysis,
        )

        failed_batches = analysis.get("failed_batches", [])
        analyzed_count = analysis.get(
            "analyzed_source_count", 0
        )

        if failed_batches or analyzed_count != len(sources):
            raise ValueError(
                "Source analysis was incomplete."
            )

        # 6. Synthesize findings.
        update_stage("synthesizing")

        synthesis = synthesize_research_findings(analysis)

        save_json(
            run_dir / "research_synthesis.json",
            synthesis,
        )

        # 7. Verify the report against the analysis.
        update_stage("verifying")

        verification = verify_research_report(
            report=synthesis,
            analysis_data=analysis,
        )

        save_json(
            run_dir / "research_verification.json",
            verification,
        )

        # 8. Save summary.
        summary = {
            "run_id": run_id,
            "status": "completed",
            "query": query,
            "document_only": document_only,
            "research_goal": plan.get("research_goal", ""),
            "sources_collected": len(sources),
            "web_sources_included": (
                0 if document_only
                else len(sources) - len(selected_pdf_sources)
            ),
            "pdf_sources_included": len(selected_pdf_sources),
            "sources_analyzed": analyzed_count,
            "key_findings": len(
                synthesis.get("key_findings", [])
            ),
            "comparisons": len(
                synthesis.get("comparisons", [])
            ),
            "candidate_research_gaps": len(
                synthesis.get("candidate_research_gaps", [])
            ),
            "verification_summary": verification.get(
                "verification_summary", {}
            ),
            "run_directory": str(run_dir),
        }

        save_json(run_dir / "summary.json", summary)

        status["status"] = "completed"
        status["current_stage"] = "completed"
        save_json(status_path, status)

        print("\n[Scout] Research completed successfully.")

        return summary

    except Exception as error:
        status["status"] = "failed"
        status["failed_stage"] = status["current_stage"]
        status["error"] = str(error)

        save_json(status_path, status)
        logger.exception("Advanced Research failed.")
        raise


if __name__ == "__main__":
    query = input("Enter your research question: ")

    try:
        result = run_advanced_research(query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as error:
        print(f"Research failed: {error}")
