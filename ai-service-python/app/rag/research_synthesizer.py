
import json
from pathlib import Path

from app.services.llm import chat_completion


SYNTHESIZER_PROMPT = """
You are Scout's research synthesizer.

Your job is to combine evidence analyses from multiple
sources into a coherent research synthesis.

The supplied analyses may be based on search snippets,
not complete papers. Respect this limitation.

Rules:
1. Do not invent research findings or citations.
2. Distinguish evidence-backed findings from hypotheses.
3. Compare approaches only when the supplied evidence
   supports the comparison.
4. Identify conflicting claims where evidence supports
   a disagreement.
5. Research gaps are candidates, not proven absences
   of previous research.
6. Never claim that no research exists merely because
   these sources did not mention a topic.
7. Cite only URLs present in the supplied input.
8. Explain when evidence is insufficient.
9. Keep conclusions specific and useful.

Return only one valid JSON object with these keys:

{
  "research_overview": "Overall synthesis",
  "key_findings": [
    {
      "finding": "Evidence-backed finding",
      "source_urls": ["URL"],
      "confidence": "low, medium, or high"
    }
  ],
  "comparisons": [
    {
      "dimension": "Comparison dimension",
      "observation": "Evidence-supported comparison",
      "source_urls": ["URL"]
    }
  ],
  "contradictions": [
    {
      "topic": "Topic of disagreement",
      "claims": ["Claim A", "Claim B"],
      "source_urls": ["URL"],
      "what_needs_verification": "What to check next"
    }
  ],
  "candidate_research_gaps": [
    {
      "gap": "Potential research gap",
      "reasoning": "Why it might be worth investigating",
      "source_urls": ["URL"],
      "confidence": "low, medium, or high",
      "validation_needed": "What further research is required"
    }
  ],
  "limitations": [
    "Limitation of this synthesis"
  ]
}

Keep the report focused. Return at most:
6 key findings, 5 comparisons, 4 contradictions,
4 candidate research gaps, and 5 limitations.

If the sources do not support a section, return
an empty list for that section.
"""


def synthesize_research_findings(
    analysis_data: dict
) -> dict:

    analyses = analysis_data.get(
        "source_analyses", []
    )

    if not isinstance(analyses, list) or not analyses:
        raise ValueError(
            "No analyzed sources are available."
        )

    # Send concise evidence summaries instead of entire
    # source contents to control token usage.
    evidence = []

    for item in analyses:
        if not isinstance(item, dict):
            continue

        url = item.get("url")

        if not url:
            continue

        points = item.get("key_points", [])

        if not isinstance(points, list):
            points = []

        evidence.append({
            "title": item.get("title", ""),
            "url": url,
            "summary": (
                item.get("summary") or ""
            )[:250],
            "key_points": [
                point.get("claim", "")[:150]
                for point in points[:2]
                if isinstance(point, dict)
                and point.get("claim")
            ],
            "limitations": [
                str(limitation)[:120]
                for limitation in (
                    item.get("limitations", [])[:1]
                    if isinstance(
                        item.get("limitations", []), list
                    )
                    else []
                )
            ],
            "evidence_quality": item.get(
                "evidence_quality", "unknown"
            )
        })

    if not evidence:
        raise ValueError(
            "No usable source analyses were found."
        )

    allowed_urls = {
        item["url"] for item in evidence
    }

    messages = [
        {
            "role": "system",
            "content": SYNTHESIZER_PROMPT
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "research_goal": analysis_data.get(
                        "research_goal", ""
                    ),
                    "analysis_scope_note": analysis_data.get(
                        "analysis_scope_note", ""
                    ),
                    "evidence": evidence
                },
                ensure_ascii=False
            )
        }
    ]

    response = chat_completion(
        messages=messages,
        reasoning_effort="low"
    )

    start = response.find("{")
    end = response.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "Synthesizer did not return valid JSON."
        )

    synthesis = json.loads(
        response[start:end + 1]
    )

    if not isinstance(synthesis, dict):
        raise ValueError(
            "Synthesis must be a JSON object."
        )

    # Keep only URLs that appeared in our input evidence.
    for field in [
        "key_findings",
        "comparisons",
        "contradictions",
        "candidate_research_gaps"
    ]:
        items = synthesis.get(field, [])

        if not isinstance(items, list):
            synthesis[field] = []
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            urls = item.get("source_urls", [])

            if not isinstance(urls, list):
                urls = []

            item["source_urls"] = list(dict.fromkeys(
                url for url in urls
                if isinstance(url, str)
                and url in allowed_urls
            ))

    synthesis["sources_considered"] = len(evidence)

    synthesis["scope_note"] = (
        "This synthesis combines analyzed search results. "
        "Findings, comparisons and candidate research gaps "
        "require verification against original papers "
        "and broader academic literature."
    )

    return synthesis


if __name__ == "__main__":
    input_path = Path("research_analysis.json")
    output_path = Path("research_synthesis.json")

    if not input_path.exists():
        raise FileNotFoundError(
            "research_analysis.json not found. "
            "Save the analyzer output to that file first."
        )

    analysis_data = json.loads(
        input_path.read_text(encoding="utf-8")
    )

    result = synthesize_research_findings(
        analysis_data
    )

    output_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("Sources considered:", result["sources_considered"])
    print("Findings:", len(result.get("key_findings", [])))
    print("Comparisons:", len(result.get("comparisons", [])))
    print(
        "Candidate gaps:",
        len(result.get("candidate_research_gaps", []))
    )
    print("Saved report:", output_path)
