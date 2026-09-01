import os

from groq import Groq
from dotenv import load_dotenv
from tavily import TavilyClient
from fastapi import FastAPI
from pydantic import BaseModel
load_dotenv()

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)
groq = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "AI service is running"}

class ResearchRequest(BaseModel):
    query: str


@app.post("/research")
async def research(request: ResearchRequest):

    response = tavily.search(
        request.query,
        max_results=5
    )

    sources = []

    for result in response["results"]:
        sources.append({
            "title": result["title"],
            "url": result["url"],
            "content": result["content"]
        })
    context = "\n\n".join(
        f"Title: {source['title']}\nContent: {source['content']}"
        for source in sources
    )

    llm_response = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "You are a research assistant. Answer the user's question using the provided sources."
            },
            {
                "role": "user",
                "content": f"""
User Question:
{request.query}

Research Sources:
{context}
"""
            }
        ]
    )

    answer = llm_response.choices[0].message.content
    return {
          "answer": answer,
        "sources": sources
    }