
import json
import logging
import time

from app.services.llm import chat_completion


logger = logging.getLogger(__name__)


ANALYZER_PROMPT = """
You are Scout's research evidence analyzer.

Analyze only the source content supplied in the input.

Rules:
1. Never invent facts, findings, experiments, or citations.
2. Source snippets may not contain the complete article.
3. Clearly identify missing or uncertain information.
4. Preserve each source's exact title and URL.
5. Copy supporting excerpts exactly from the supplied content.
6. Do not claim a source is peer-reviewed unless established
   by the supplied information.
7. Use only URLs supplied in the input.
8. Return exactly one analysis for every supplied source.
9. Every source analysis must use the original source URL.
10. Return valid JSON, with no Markdown fences.

Return one JSON object with these keys:

{
  "source_analyses": [
    {
      "title": "Exact source title",
      "url": "Exact source URL",
      "relevance": "high, medium, or low",
      "summary": "Evidence-based summary",
      "key_points": [
        {
          "claim": "Supported claim",
          "supporting_excerpt": "Exact source excerpt"
        }
      ],
      "limitations": [
        "What cannot be established from this source"
      ],
      "evidence_quality": "insufficient, limited, or moderate"
    }
  ],
  "cross_source_observations": [
    {
      "observation": "Observation supported by sources",
      "supporting_urls": ["URL 1", "URL 2"],
      "confidence": "low, medium, or high"
    }
  ]
}

If evidence is insufficient, return an empty key_points list
and explain the limitations.

Do not manufacture evidence just to fill the requested fields.
"""


def _parse_json(response):
    """Parse a JSON object from the model response."""

    if isinstance(response, dict):
        return response

    if not isinstance(response, str):
        raise ValueError(
            "Analyzer returned unexpected response type: "
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
            "Analyzer did not return a JSON object. "
            f"Response preview: {content[:400]!r}"
        )

    try:
        result, _ = json.JSONDecoder().raw_decode(
            content[start:]
        )

    except json.JSONDecodeError as error:
        preview = content[
            max(start, start + error.pos - 150):
            min(len(content), start + error.pos + 250)
        ]

        raise ValueError(
            "Analyzer returned invalid or incomplete JSON. "
            f"Reason: {error.msg}; "
            f"line={error.lineno}, column={error.colno}; "
            f"nearby response={preview!r}"
        ) from error

    if not isinstance(result, dict):
        raise ValueError(
            "Analyzer response must be a JSON object."
        )

    return result


def _request_json(messages):
    """Request JSON and retry once if parsing fails."""

    response = chat_completion(
        messages=messages,
        reasoning_effort="low",
        max_completion_tokens=4096,
        json_mode=True,
    )

    try:
        return _parse_json(response)

    except ValueError as first_error:
        raw_response = (
            response
            if isinstance(response, str)
            else json.dumps(response, ensure_ascii=False)
        )

        logger.warning(
            "Analyzer JSON parsing failed. Retrying once: %s",
            first_error,
        )

        repair_messages = messages + [
            {
                "role": "assistant",
                "content": raw_response,
            },
            {
                "role": "user",
                "content": (
                    "The previous response was invalid or incomplete. "
                    "Return a complete, valid JSON object matching "
                    "the original schema. Include one analysis for "
                    "each supplied source, using the exact input URLs. "
                    "Do not invent content. Do not use Markdown fences."
                ),
            },
        ]

        repaired_response = chat_completion(
            messages=repair_messages,
            reasoning_effort="low",
            max_completion_tokens=8192,
            json_mode=True,
        )

        return _parse_json(repaired_response)


def _clean_analysis(analysis, original):
    """Validate an analysis and preserve the original source identity."""

    if not isinstance(analysis, dict):
        raise ValueError("A source analysis is not a JSON object.")

    content = (original.get("content") or "")[:800]

    relevance = analysis.get("relevance", "low")

    if relevance not in {"high", "medium", "low"}:
        relevance = "low"

    quality = analysis.get("evidence_quality", "insufficient")

    if quality not in {"insufficient", "limited", "moderate"}:
        quality = "insufficient"

    raw_points = analysis.get("key_points", [])

    if not isinstance(raw_points, list):
        raw_points = []

    points = []

    for point in raw_points:
        if not isinstance(point, dict):
            continue

        claim = point.get("claim", "")
        excerpt = point.get("supporting_excerpt", "")

        if not isinstance(claim, str) or not claim.strip():
            continue

        if not isinstance(excerpt, str):
            excerpt = ""

        # Only retain an excerpt that appears verbatim
        # in the source content sent to the model.
        if excerpt and excerpt not in content:
            excerpt = ""

        points.append({
            "claim": claim.strip(),
            "supporting_excerpt": excerpt,
        })

    raw_limitations = analysis.get("limitations", [])

    if not isinstance(raw_limitations, list):
        raw_limitations = []

    limitations = [
        item.strip()
        for item in raw_limitations
        if isinstance(item, str) and item.strip()
    ]

    summary = analysis.get("summary", "")

    if not isinstance(summary, str):
        summary = ""

    return {
        "title": original.get("title", ""),
        "url": original["url"],
        "relevance": relevance,
        "summary": summary.strip(),
        "key_points": points,
        "limitations": limitations,
        "evidence_quality": quality,
    }


def analyze_research_sources(
    research_data: dict,
    batch_size: int = 2,
) -> dict:

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")

    sources = research_data.get("sources", [])

    if not isinstance(sources, list):
        raise ValueError("Sources must be a list.")

    source_analyses = []
    cross_source_observations = []
    failed_batches = []

    for start in range(0, len(sources), batch_size):
        batch = sources[start:start + batch_size]
        batch_number = start // batch_size + 1

        valid_batch = [
            source for source in batch
            if isinstance(source, dict) and source.get("url")
        ]

        source_lookup = {
            source["url"]: source
            for source in valid_batch
        }

        if not source_lookup:
            continue

        input_sources = [
            {
                "title": source.get("title", ""),
                "url": source["url"],
                "content": (source.get("content") or "")[:800],
            }
            for source in valid_batch
        ]

        messages = [
            {
                "role": "system",
                "content": ANALYZER_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "research_goal": research_data.get(
                            "research_goal", ""
                        ),
                        "sub_questions": research_data.get(
                            "sub_questions", []
                        ),
                        "sources": input_sources,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        try:
            time.sleep(1)

            result = _request_json(messages)

            analyses = result.get("source_analyses")

            if not isinstance(analyses, list):
                raise ValueError(
                    "source_analyses must be a list."
                )

            batch_analyses = {}

            for analysis in analyses:
                if not isinstance(analysis, dict):
                    continue

                url = analysis.get("url")

                if url not in source_lookup:
                    continue

                # Do not let duplicate analyses inflate the count.
                if url in batch_analyses:
                    continue

                batch_analyses[url] = _clean_analysis(
                    analysis,
                    source_lookup[url],
                )

            missing_urls = (
                set(source_lookup) - set(batch_analyses)
            )

            if missing_urls:
                raise ValueError(
                    "Analyzer omitted source(s) from batch: "
                    + ", ".join(sorted(missing_urls))
                )

            # Commit the batch only after every source is validated.
            source_analyses.extend(batch_analyses.values())

            observations = result.get(
                "cross_source_observations", []
            )

            if isinstance(observations, list):
                valid_urls = set(source_lookup)

                for observation in observations:
                    if not isinstance(observation, dict):
                        continue

                    urls = observation.get("supporting_urls", [])

                    if not isinstance(urls, list):
                        continue

                    valid_observation_urls = [
                        url for url in urls
                        if url in valid_urls
                    ]

                    if not valid_observation_urls:
                        continue

                    confidence = observation.get(
                        "confidence", "low"
                    )

                    if confidence not in {"low", "medium", "high"}:
                        confidence = "low"

                    text = observation.get("observation", "")

                    if not isinstance(text, str) or not text.strip():
                        continue

                    cross_source_observations.append({
                        "observation": text.strip(),
                        "supporting_urls": valid_observation_urls,
                        "confidence": confidence,
                    })

        except Exception as error:
            logger.exception(
                "Research analysis failed for batch %s",
                batch_number,
            )

            failed_batches.append({
                "batch": batch_number,
                "error": str(error),
            })

    return {
        "research_goal": research_data.get(
            "research_goal", ""
        ),
        "total_sources": len(sources),
        "analyzed_source_count": len(source_analyses),
        "source_analyses": source_analyses,
        "cross_source_observations": cross_source_observations,
        "failed_batches": failed_batches,
        "analysis_scope_note": (
            "Analysis is based on supplied source snippets, "
            "not necessarily complete source documents. "
            "Findings require further verification."
        ),
    }
