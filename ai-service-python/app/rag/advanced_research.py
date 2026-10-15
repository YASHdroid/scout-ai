
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from app.rag.research_planner import create_research_plan
from app.rag.research_executor import execute_research_plan
from app.rag.research_analyzer import analyze_research_sources
from app.rag.research_synthesizer import synthesize_research_findings
from app.rag.research_verifier import verify_research_report

logger = logging.getLogger(__name__)

MAX_SOURCES = 10


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def run_advanced_research(query, output_root="research_runs"):
    query = query.strip()

    if len(query) < 5 or len(query) > 2000:
        raise ValueError("Query must be between 5 and 2000 characters.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:40]
    run_id = f"{timestamp}_{slug}"

    run_dir = Path(output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    status_path = run_dir / "run_status.json"

    status = {
        "run_id": run_id,
        "status": "running",
        "current_stage": "planning"
    }

    def update_stage(stage):
        status["current_stage"] = stage
        save_json(status_path, status)
        print(f"\n[Scout] {stage.title()}...", flush=True)

    try:
        update_stage("planning")
        plan = create_research_plan(query)
        save_json(run_dir / "research_plan.json", plan)

        update_stage("searching")
        research_data = execute_research_plan(plan)
        save_json(run_dir / "research_data.json", research_data)

        sources = research_data.get("sources", [])

        if not sources:
            raise ValueError("No sources were found.")

        analysis_input = dict(research_data)
        analysis_input["sources"] = sources[:MAX_SOURCES]

        update_stage("analyzing")
        analysis = analyze_research_sources(analysis_input)
        save_json(run_dir / "research_analysis.json", analysis)

        failed_batches = analysis.get("failed_batches", [])
        analyzed_count = analysis.get("analyzed_source_count", 0)

        if failed_batches or analyzed_count != len(analysis_input["sources"]):
            raise ValueError("Source analysis was incomplete.")

        update_stage("synthesizing")
        synthesis = synthesize_research_findings(analysis)
        save_json(run_dir / "research_synthesis.json", synthesis)

        update_stage("verifying")
        verification = verify_research_report(
            report=synthesis,
            analysis_data=analysis
        )
        save_json(run_dir / "research_verification.json", verification)

        summary = {
            "run_id": run_id,
            "status": "completed",
            "query": query,
            "research_goal": plan.get("research_goal", ""),
            "sources_collected": len(sources),
            "sources_analyzed": analyzed_count,
            "key_findings": len(synthesis.get("key_findings", [])),
            "comparisons": len(synthesis.get("comparisons", [])),
            "candidate_research_gaps": len(
                synthesis.get("candidate_research_gaps", [])
            ),
            "verification_summary": verification.get(
                "verification_summary", {}
            ),
            "run_directory": str(run_dir)
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
