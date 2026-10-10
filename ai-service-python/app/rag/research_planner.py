
import json

from app.services.llm import chat_completion


RESEARCH_PLANNER_PROMPT = """
You are Scout's research planning engine.

Your job is to create a research plan for a given question.
Do not answer the research question yet.

Break the question into smaller investigations that
together can produce a thorough, evidence-based answer.

Focus on relevant research papers, technical approaches,
methods, experiments, datasets, results and limitations
when appropriate.

Create:
1. One clear research goal.
2. Three to six focused sub-questions.
3. Three to five web search queries.
4. Two to four academic paper search queries.
5. A list of evidence that should be collected.
6. A list of sections for the final research report.

Search queries must be specific, standalone and useful.
Avoid duplicate queries.

Do not invent research findings or citations.
This stage creates a plan only; it does not perform searches.

Return only a valid JSON object with these exact keys:

{
  "research_goal": "string",
  "sub_questions": ["string"],
  "web_search_queries": ["string"],
  "paper_search_queries": ["string"],
  "evidence_to_collect": ["string"],
  "report_sections": ["string"]
}
"""


def create_research_plan(query: str) -> dict:
    query = query.strip()

    if not query:
        raise ValueError("Research question cannot be empty.")

    response = chat_completion(
        messages=[
            {
                "role": "system",
                "content": RESEARCH_PLANNER_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "Create a detailed research plan for "
                    "the following question:\n\n"
                    f"{query}"
                )
            }
        ],
        reasoning_effort="low"
    )

    content = response.strip()

    # Handle cases where the model wraps JSON in code fences.
    if content.startswith("```"):
        content = content.strip("`").strip()

        if content.lower().startswith("json"):
            content = content[4:].strip()


    start = content.find("{")
    end = content.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "Research planner did not return valid JSON."
        )

    plan = json.loads(content[start:end + 1])

    required_keys = [
        "research_goal",
        "sub_questions",
        "web_search_queries",
        "paper_search_queries",
        "evidence_to_collect",
        "report_sections"
    ]

    for key in required_keys:
        if key not in plan:
            raise ValueError(
                f"Research plan is missing the '{key}' field."
            )

    return plan
