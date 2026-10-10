
import argparse
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


def save_json(path: Path, data: dict) -> None:
    """Save stage output as readable JSON."""
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def run_advanced_research(
    query: str,
    output_root: str = "research_runs",
) -> dict:
    """
    Run Scout's complete Advanced Research pipeline.

    Planner -> Executor -> Analyzer -> Synthesizer -> Verifier

    Every completed stage is saved so its results are
    available even if a later stage fails.
    """

    query = query.strip()

    if not query:
        raise ValueError(
            "Research question cannot be empty."
        )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        query.lower()
    ).strip("-")[:45]

    run_id = f"{timestamp}_{slug or 'research'}"

    run_dir = Path(output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    status = {
        "run_id": run_id,
        "query": query,
        "status": "running",
        "current_stage": "initializing",
        "started_at": datetime.now().astimezone().isoformat(),
    }

    status_path = run_dir / "run_status.json"

    def update_status(stage: str) -> None:
        status["current_stage"] = stage
        save_json(status_path, status)

    def progress(message: str) -> None:
        print(f"\n[Scout] {message}", flush=True)

    try:
        # 1. Plan the investigation
        update_status("planning")
        progress("Stage 1/5: Planning research...")

        plan = create_research_plan(query)

        save_json(
            run_dir / "research_plan.json",
            plan
        )

        progress(
            f"Research plan created with "
            f"{len(plan.get('sub_questions', []))} "
            f"sub-questions."
        )

        # 2. Search and collect sources
        update_status("executing")
        progress("Stage 2/5: Searching for sources...")

        research_data = execute_research_plan(plan)

        save_json(
            run_dir / "research_data.json",
            research_data
        )

        source_count = research_data.get(
            "source_count",
            len(research_data.get("sources", []))
        )

        progress(
            f"Collected {source_count} unique sources."
        )

        if not research_data.get("sources"):
            raise RuntimeError(
                "Research returned no sources. "
                "Check the search service and try again."
            )

        # 3. Analyze source evidence
        update_status("analyzing")
        progress("Stage 3/5: Analyzing source evidence...")

        analysis = analyze_research_sources(
            research_data
        )

        save_json(
            run_dir / "research_analysis.json",
            analysis
        )

        analyzed_count = analysis.get(
            "analyzed_source_count", 0
        )

        progress(
            f"Analyzed {analyzed_count} sources."
        )

        if not analysis.get("source_analyses"):
            raise RuntimeError(
                "No source analyses were produced. "
                "Check research_analysis.json."
            )

        # 4. Synthesize the collected evidence
        update_status("synthesizing")
        progress(
            "Stage 4/5: Synthesizing findings and comparisons..."
        )

        synthesis = synthesize_research_findings(
            analysis
        )

        save_json(
            run_dir / "research_synthesis.json",
            synthesis
        )

        finding_count = len(
            synthesis.get("key_findings", [])
        )

        gap_count = len(
            synthesis.get("candidate_research_gaps", [])
        )

        progress(
            f"Generated {finding_count} findings "
            f"and {gap_count} candidate research gaps."
        )

        # 5. Verify claims against retrieved source content
        update_status("verifying")
        progress(
            "Stage 5/5: Verifying claims and citations. "
            "This may take several minutes..."
        )

        verification = verify_research_report(
            report=synthesis,
            analysis_data=analysis,
        )

        save_json(
            run_dir / "research_verification.json",
            verification
        )

        verification_summary = verification.get(
            "verification_summary", {}
        )

        progress("Research verification finished.")

        # Final run summary
        summary = {
            "run_id": run_id,
            "status": "completed",
            "query": query,
            "research_goal": plan.get(
                "research_goal", ""
            ),
            "sources_collected": source_count,
            "sources_analyzed": analyzed_count,
            "key_findings": finding_count,
            "comparisons": len(
                synthesis.get("comparisons", [])
            ),
            "candidate_research_gaps": gap_count,
            "verification_summary": verification_summary,
            "run_directory": str(run_dir),
        }

        save_json(
            run_dir / "summary.json",
            summary
        )

        status.update({
            "status": "completed",
            "current_stage": "completed",
            "finished_at": datetime.now().astimezone().isoformat(),
        })

        save_json(status_path, status)

        progress("Advanced Research run completed successfully.")

        return summary

    except Exception as error:
        logger.exception(
            "Advanced Research failed during stage: %s",
            status["current_stage"]
        )

        status.update({
            "status": "failed",
            "error": f"{type(error).__name__}: {error}",
            "failed_at": datetime.now().astimezone().isoformat(),
        })

        save_json(status_path, status)

        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)

    parser = argparse.ArgumentParser(
        description="Run Scout Advanced Research."
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Research question"
    )

    parser.add_argument(
        "--output-dir",
        default="research_runs",
        help="Directory for saving research runs"
    )

    args = parser.parse_args()

    query = args.query or input(
        "Enter your research question: "
    )

    try:
        result = run_advanced_research(
            query=query,
            output_root=args.output_dir,
        )

        print("\nFinal run summary:")
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as error:
        print(
            f"\nResearch run failed: "
            f"{type(error).__name__}: {error}"
        )
        print(
            "Check run_status.json and saved stage files "
            "for details."
        )
