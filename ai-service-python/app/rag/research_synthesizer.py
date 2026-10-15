
import json
import logging
from pathlib import Path
from typing import Any

from app.services.llm import chat_completion


logger = logging.getLogger(__name__)

MAX_KEY_FINDINGS = 6
MAX_COMPARISONS = 5
MAX_CONTRADICTIONS = 4
MAX_RESEARCH_GAPS = 4
MAX_LIMITATIONS = 5


SYNTHESIZER_PROMPT = """
You are Scout's evidence-grounded research synthesizer.

Create a detailed synthesis that directly answers the research
question using ONLY the supplied analyzed-source evidence.

Rules:
1. Never invent findings, experiments, statistics, citations, or URLs.
2. Source analyses may be based on snippets rather than full papers.
3. Clearly distinguish evidence, interpretation, hypotheses, and
   unresolved claims.
4. Explain why important findings matter, including relevant
   limitations and implications.
5. Compare approaches only when the supplied evidence supports it.
6. Never compare metrics from different experimental settings as
   though they came from the same experiment.
7. Do not generalize a single benchmark or vendor demonstration
   into a universal conclusion.
8. A numerical claim reported by a source is not independently
   verified unless the supplied evidence supports that conclusion.
9. Missing evidence is not a contradiction.
10. Research gaps are candidates for investigation, not proof that
    no prior work exists.
11. Use only source URLs supplied in the evidence.
12. Explain where evidence is insufficient.
13. Avoid repetitive or generic claims.
14. Return exactly the JSON schema below.

Required JSON structure:

{
  "research_overview": "Detailed synthesis answering the question",
  "key_findings": [
    {
      "finding": "Substantive finding with context and caveats",
      "source_urls": ["URL"],
      "confidence": "low, medium, or high"
    }
  ],
  "comparisons": [
    {
      "dimension": "Comparison dimension",
      "observation": "Evidence-based comparison and limitations",
      "source_urls": ["URL"]
    }
  ],
  "contradictions": [
    {
      "topic": "Topic of disagreement",
      "claims": ["Claim A", "Claim B"],
      "source_urls": ["URL"],
      "what_needs_verification": "Next verification step"
    }
  ],
  "candidate_research_gaps": [
    {
      "gap": "Potential research gap",
      "reasoning": "Evidence-based rationale",
      "source_urls": ["URL"],
      "confidence": "low, medium, or high",
      "validation_needed": "Further validation required"
    }
  ],
  "limitations": [
    "Specific limitation"
  ]
}

Research overview:
Write 3-5 substantive paragraphs when supported by the evidence.
Start with a direct answer. Synthesize the major themes, describe
important differences, and clearly state what remains uncertain.

Key findings:
Return at most 6. Explain meaningful findings rather than providing
only unexplained one-line assertions.

Comparisons:
Return at most 5. Explain differences and trade-offs. Include
quantitative results only when present in the input.

Contradictions:
Return at most 4 genuine disagreements. Otherwise return [].

Candidate research gaps:
Return at most 4. Never claim that a gap is proven across the
entire literature solely because the supplied sources omit it.

Limitations:
Return at most 5 limitations relevant to the supplied evidence.

Use empty lists for unsupported sections.
Return valid JSON only, without Markdown fences or extra text.
"""


def _text(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    return default


def _string_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []

    result = []

    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())

        if len(result) >= limit:
            break

    return result


def _parse_json_response(response: Any) -> dict:
    """Parse a complete JSON object returned by Groq."""

    if isinstance(response, dict):
        return response

    if not isinstance(response, str):
        raise ValueError(
            "Unexpected synthesizer response type: "
            f"{type(response).__name__}"
        )

    content = response.strip()

    if content.startswith("```"):
        lines = content.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    start = content.find("{")

    if start == -1:
        raise ValueError(
            "Synthesizer did not return a JSON object. "
            f"Response preview: {content[:400]!r}"
        )

    try:
        parsed, _ = json.JSONDecoder().raw_decode(
            content[start:]
        )
    except json.JSONDecodeError as error:
        position = start + error.pos

        preview = content[
            max(0, position - 180):
            min(len(content), position + 300)
        ]

        raise ValueError(
            "Synthesizer returned invalid or incomplete JSON. "
            f"Reason: {error.msg}; "
            f"line={error.lineno}, column={error.colno}; "
            f"nearby response={preview!r}"
        ) from error

    if not isinstance(parsed, dict):
        raise ValueError(
            "Synthesizer response must be a JSON object."
        )

    return parsed


def _prepare_evidence(analysis_data: dict) -> list[dict]:
    """Prepare bounded evidence for synthesis."""

    analyses = analysis_data.get("source_analyses", [])

    if not isinstance(analyses, list) or not analyses:
        raise ValueError("No analyzed sources are available.")

    evidence = []

    for item in analyses:
        if not isinstance(item, dict):
            continue

        url = _text(item.get("url"))

        if not url:
            continue

        raw_points = item.get("key_points", [])

        if not isinstance(raw_points, list):
            raw_points = []

        key_points = []

        for point in raw_points:
            if not isinstance(point, dict):
                continue

            claim = _text(point.get("claim"))

            if not claim:
                continue

            # The analyzer uses "supporting_excerpt".
            # "evidence" is retained as a compatibility fallback.
            excerpt = _text(
                point.get("evidence")
                or point.get("supporting_excerpt")
            )

            key_points.append({
                "claim": claim[:300],
                "evidence": excerpt[:500],
                "confidence": _text(
                    point.get("confidence")
                )[:50],
            })

            if len(key_points) >= 5:
                break

        raw_limitations = item.get("limitations", [])

        if not isinstance(raw_limitations, list):
            raw_limitations = []

        limitations = [
            str(value).strip()[:250]
            for value in raw_limitations[:3]
            if value is not None and str(value).strip()
        ]

        evidence.append({
            "title": _text(item.get("title"))[:300],
            "url": url,
            "summary": _text(item.get("summary"))[:1000],
            "key_points": key_points,
            "limitations": limitations,
            "evidence_quality": _text(
                item.get("evidence_quality"),
                "unknown",
            )[:100],
        })

    if not evidence:
        raise ValueError("No usable source analyses were found.")

    return evidence


def _generate_synthesis(messages: list[dict]) -> dict:
    """Request JSON and retry once if the first result cannot be parsed."""

    response = chat_completion(
        messages=messages,
        reasoning_effort="medium",
        max_completion_tokens=8192,
        json_mode=True,
    )

    try:
        return _parse_json_response(response)

    except ValueError as first_error:
        logger.warning(
            "Initial synthesis response could not be parsed: %s",
            first_error,
        )

    # Retry using the original research evidence, not the possibly
    # truncated output. Ask for a shorter, complete report.
    retry_messages = [dict(message) for message in messages]

    last_message = retry_messages[-1]

    retry_messages[-1] = {
        "role": last_message["role"],
        "content": (
            last_message["content"]
            + "\n\nRetry instruction: your previous output was "
            "invalid or incomplete. Regenerate the entire JSON object "
            "from the supplied evidence. Make the overview concise, "
            "limit key findings to 4 and comparisons to 3, and ensure "
            "every JSON string, array, and object is closed. "
            "Return valid JSON only."
        ),
    }

    repaired_response = chat_completion(
        messages=retry_messages,
        reasoning_effort="medium",
        max_completion_tokens=8192,
        json_mode=True,
    )

    # If the retry is also invalid, let the detailed exception
    # identify the parsing location.
    return _parse_json_response(repaired_response)


def _normalise_synthesis(
    synthesis: dict,
    allowed_urls: set[str],
    evidence_count: int,
) -> dict:
    """Validate the expected fields and allowed source URLs."""

    overview = _text(synthesis.get("research_overview"))

    if not overview:
        raise ValueError(
            "Synthesizer returned an empty research overview."
        )

    limits = {
        "key_findings": MAX_KEY_FINDINGS,
        "comparisons": MAX_COMPARISONS,
        "contradictions": MAX_CONTRADICTIONS,
        "candidate_research_gaps": MAX_RESEARCH_GAPS,
    }

    normalized = {
        "research_overview": overview,
    }

    for field, max_items in limits.items():
        raw_items = synthesis.get(field, [])

        if not isinstance(raw_items, list):
            raw_items = []

        cleaned_items = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            urls = _string_list(
                item.get("source_urls"),
                limit=10,
            )

            valid_urls = list(dict.fromkeys(
                url for url in urls
                if url in allowed_urls
            ))

            if field == "key_findings":
                finding = _text(item.get("finding"))

                if not finding:
                    continue

                confidence = _text(
                    item.get("confidence")
                ).lower()

                if confidence not in {"low", "medium", "high"}:
                    confidence = "low"

                cleaned_items.append({
                    "finding": finding,
                    "source_urls": valid_urls,
                    "confidence": confidence,
                })

            elif field == "comparisons":
                dimension = _text(item.get("dimension"))
                observation = _text(item.get("observation"))

                if not dimension or not observation:
                    continue

                cleaned_items.append({
                    "dimension": dimension,
                    "observation": observation,
                    "source_urls": valid_urls,
                })

            elif field == "contradictions":
                topic = _text(item.get("topic"))
                claims = _string_list(
                    item.get("claims"),
                    limit=4,
                )

                if not topic or len(claims) < 2:
                    continue

                cleaned_items.append({
                    "topic": topic,
                    "claims": claims,
                    "source_urls": valid_urls,
                    "what_needs_verification": _text(
                        item.get("what_needs_verification")
                    ),
                })

            elif field == "candidate_research_gaps":
                gap = _text(item.get("gap"))
                reasoning = _text(item.get("reasoning"))

                if not gap or not reasoning:
                    continue

                confidence = _text(
                    item.get("confidence")
                ).lower()

                if confidence not in {"low", "medium", "high"}:
                    confidence = "low"

                cleaned_items.append({
                    "gap": gap,
                    "reasoning": reasoning,
                    "source_urls": valid_urls,
                    "confidence": confidence,
                    "validation_needed": _text(
                        item.get("validation_needed")
                    ),
                })

            if len(cleaned_items) >= max_items:
                break

        normalized[field] = cleaned_items

    normalized["limitations"] = _string_list(
        synthesis.get("limitations"),
        limit=MAX_LIMITATIONS,
    )

    normalized["sources_considered"] = evidence_count

    normalized["scope_note"] = (
        "This synthesis combines the analyzed sources supplied to "
        "the model. Source coverage and evidence quality limit the "
        "strength of its conclusions. Candidate research gaps are "
        "not proof that no prior research exists. Important claims "
        "should be checked against their original sources."
    )

    return normalized


def synthesize_research_findings(
    analysis_data: dict,
) -> dict:
    """Create a detailed synthesis compatible with Scout's verifier."""

    evidence = _prepare_evidence(analysis_data)

    allowed_urls = {
        item["url"] for item in evidence
    }

    input_data = {
        "research_question": _text(
            analysis_data.get("query")
            or analysis_data.get("research_question")
            or analysis_data.get("research_goal")
        ),
        "research_goal": _text(
            analysis_data.get("research_goal")
        ),
        "analysis_scope_note": _text(
            analysis_data.get("analysis_scope_note")
        ),
        "number_of_sources_supplied": len(evidence),
        "evidence": evidence,
    }

    messages = [
        {
            "role": "system",
            "content": SYNTHESIZER_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                input_data,
                ensure_ascii=False,
            ),
        },
    ]

    synthesis = _generate_synthesis(messages)

    result = _normalise_synthesis(
        synthesis=synthesis,
        allowed_urls=allowed_urls,
        evidence_count=len(evidence),
    )

    logger.info(
        "Research synthesis completed: %d sources, "
        "%d findings, %d comparisons.",
        result["sources_considered"],
        len(result["key_findings"]),
        len(result["comparisons"]),
    )

    return result


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

    result = synthesize_research_findings(analysis_data)

    output_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("Sources considered:", result["sources_considered"])
    print("Findings:", len(result["key_findings"]))
    print("Comparisons:", len(result["comparisons"]))
    print(
        "Candidate gaps:",
        len(result["candidate_research_gaps"]),
    )
    print("Saved report:", output_path)
