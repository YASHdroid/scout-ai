
import json
import logging
import time

from app.services.llm import chat_completion

logger = logging.getLogger(__name__)


ANALYZER_PROMPT = """
You are Scout's research evidence analyzer.

Analyze only the information provided in the supplied
search-result snippets.

Rules:
1. Never invent facts, findings, experiments, or citations.
2. Search snippets may not contain the complete article.
3. Clearly identify missing or uncertain information.
4. Preserve each source's exact title and URL.
5. Copy supporting excerpts exactly from supplied content.
6. Do not claim a source is peer-reviewed unless this
   is established by the supplied information.
7. Use only URLs supplied in the input.
8. Return one analysis for each supplied source.

Return only valid JSON with these keys:

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

If evidence is insufficient, return empty key_points
and explain the limitations.
"""


def _parse_json(content: str) -> dict:
    start = content.find("{")
    end = content.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "Analyzer did not return valid JSON."
        )

    result = json.loads(content[start:end + 1])

    if not isinstance(result, dict):
        raise ValueError(
            "Analyzer response must be a JSON object."
        )

    return result


def analyze_research_sources(
    research_data: dict,
    batch_size: int = 2
) -> dict:

    if batch_size < 1:
        raise ValueError(
            "batch_size must be at least 1."
        )

    sources = research_data.get("sources", [])

    if not isinstance(sources, list):
        raise ValueError("Sources must be a list.")

    source_analyses = []
    cross_source_observations = []
    failed_batches = []

    for start in range(0, len(sources), batch_size):
        batch = sources[start:start + batch_size]
        batch_number = start // batch_size + 1

        source_lookup = {
            source.get("url"): source
            for source in batch
            if isinstance(source, dict)
            and source.get("url")
        }

        input_sources = [
            {
                "title": source.get("title", ""),
                "url": source.get("url", ""),
                "content": (
                    source.get("content") or ""
                )[:800]
            }
            for source in batch
            if isinstance(source, dict)
            and source.get("url")
        ]

        messages = [
            {
                "role": "system",
                "content": ANALYZER_PROMPT
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
                        "sources": input_sources
                    },
                    ensure_ascii=False
                )
            }
        ]

        try:
            # Small delay between analysis requests.
            time.sleep(3)

            response = chat_completion(
                messages=messages,
                reasoning_effort="low"
            )

            result = _parse_json(response)

            analyses = result.get(
                "source_analyses", []
            )

            if not isinstance(analyses, list):
                raise ValueError(
                    "source_analyses must be a list."
                )

            for analysis in analyses:
                if not isinstance(analysis, dict):
                    continue

                url = analysis.get("url")
                original = source_lookup.get(url)

                # Accept only sources included in this batch.
                if original is None:
                    continue

                analysis["title"] = original.get(
                    "title", ""
                )
                analysis["url"] = url

                content = (
                    original.get("content") or ""
                )[:800]

                points = analysis.get("key_points", [])

                if not isinstance(points, list):
                    points = []

                for point in points:
                    if not isinstance(point, dict):
                        continue

                    excerpt = point.get(
                        "supporting_excerpt", ""
                    )

                    if (
                        not isinstance(excerpt, str)
                        or (
                            excerpt
                            and excerpt not in content
                        )
                    ):
                        point["supporting_excerpt"] = ""

                analysis["key_points"] = points
                source_analyses.append(analysis)

            observations = result.get(
                "cross_source_observations", []
            )

            if isinstance(observations, list):
                valid_urls = set(source_lookup)

                for observation in observations:
                    if not isinstance(observation, dict):
                        continue

                    urls = observation.get(
                        "supporting_urls", []
                    )

                    if not isinstance(urls, list):
                        continue

                    observation["supporting_urls"] = [
                        url for url in urls
                        if url in valid_urls
                    ]

                    cross_source_observations.append(
                        observation
                    )

        except Exception as error:
            logger.exception(
                "Research analysis failed for batch %s",
                batch_number
            )

            failed_batches.append({
                "batch": batch_number,
                "error": str(error)
            })

    return {
        "research_goal": research_data.get(
            "research_goal", ""
        ),
        "total_sources": len(sources),
        "analyzed_source_count": len(source_analyses),
        "source_analyses": source_analyses,
        "cross_source_observations": (
            cross_source_observations
        ),
        "failed_batches": failed_batches,
        "analysis_scope_note": (
            "Analysis is based on supplied search snippets, "
            "not necessarily full source documents. "
            "Findings require further verification."
        )
    }
