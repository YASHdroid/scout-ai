from tavily import TavilyClient
from app.core.config import TAVILY_API_KEY

tavily = TavilyClient(api_key=TAVILY_API_KEY)

def web_search(query: str, max_results: int = 5):
    response = tavily.search(
        query,
        max_results=max_results
    )

    return response.get("results", [])
