# Scout AI Service

Python AI/RAG service for Scout.

## Architecture

- FastAPI API layer
- PostgreSQL + pgvector
- Sentence Transformers embeddings
- Dynamic LLM tool routing
- Document retrieval
- Reranking
- Tavily web search
- Groq LLM

## Dynamic routing

Scout does not use a fixed keyword rule to choose the source.

The LLM receives two tools:

- `document_search`
- `web_search`

The model decides whether to use neither, one, or both.

The document retrieval pipeline then:

1. embeds the query
2. retrieves candidate chunks with pgvector
3. reranks candidates
4. returns the best context

## Run

Activate the virtual environment:

```powershell
.\venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add your existing keys.

Run:

```powershell
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Database

The existing Scout database should contain:

- `documents`
- `document_chunks`
- `conversations`
- `messages`

`document_chunks.embedding` should use the pgvector type.

Do not upload `.env` to GitHub.
