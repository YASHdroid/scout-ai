from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


def web_search(query):

    response = tavily.search(
        query,
        max_results=5
    )

    return response["results"]