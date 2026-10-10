
import logging

from app.services.search import web_search

logger = logging.getLogger(__name__)


def execute_research_plan(
    plan: dict,
    max_results_per_query: int = 3
) -> dict:

    sources_by_url = {}
    executed_queries = []
    failed_queries = []

    search_groups = [
        (
            "web",
            plan.get("web_search_queries", []),
            5
        ),
        (
            "paper_discovery",
            plan.get("paper_search_queries", []),
            4
        )
    ]

    for search_type, queries, max_queries in search_groups:

        if not isinstance(queries, list):
            continue

        for query in queries[:max_queries]:

            if not isinstance(query, str) or not query.strip():
                continue

            try:
                results = web_search(
                    query=query.strip(),
                    max_results=max_results_per_query
                )

                executed_queries.append(query)

                for result in results:
                    title = result.get("title") or "Untitled source"
                    url = result.get("url") or ""
                    content = result.get("content") or ""

                    key = (
                        url.strip().rstrip("/").lower()
                        if url
                        else f"{title.lower()}|{content[:100].lower()}"
                    )

                    if key not in sources_by_url:
                        sources_by_url[key] = {
                            "title": title,
                            "url": url,
                            "content": content,
                            "found_via": []
                        }

                    sources_by_url[key]["found_via"].append({
                        "search_type": search_type,
                        "query": query
                    })

            except Exception:
                logger.exception(
                    "Research search failed for query: %s",
                    query
                )

                failed_queries.append({
                    "query": query,
                    "search_type": search_type
                })

    sources = list(sources_by_url.values())

    return {
        "research_goal": plan.get("research_goal", ""),
        "sub_questions": plan.get("sub_questions", []),
        "sources": sources,
        "queries_executed": len(executed_queries),
        "source_count": len(sources),
        "failed_queries": failed_queries
    }
