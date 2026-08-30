from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "AI service is running"}

class ResearchRequest(BaseModel):
    query: str


@app.post("/research")
async def research(request: ResearchRequest):
    return {
        "answer": f"Received query: {request.query}",
        "sources": []
    }