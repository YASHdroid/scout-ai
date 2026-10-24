Scout — AI Research & Evidence Engine

Ask a research question. Scout investigates web sources, extracts evidence, surfaces where sources disagree, and produces a citation-grounded research report where every claim traces back to a source.

Live demo: scout-ai-umber.vercel.app

Why Scout

Most AI research tools return a fluent summary and leave you to guess what's actually backed up. Scout is built around a different principle:

Claim → Supporting Evidence → Source → URL
Every claim in the report is linked to the evidence that supports it.
When sources disagree, Scout shows the conflict instead of silently picking a side.
It is a research pipeline, not a chat wrapper or a generic summarizer.
How It Works

Scout runs each question through five stages:

Stage	What happens
Plan	Breaks the question into focused sub-questions
Search	Finds and fetches relevant web sources
Analyze	Extracts evidence passages from each source
Synthesize	Combines evidence into a structured report
Verify	Checks claims against sources and flags conflicts
Architecture

Scout is a polyglot, three-service system. Node owns the data; Python owns the AI logic and stays stateless.

┌──────────────┐     ┌────────────────────┐     ┌──────────────────────┐
│   Frontend   │ ──▶ │   Node.js Backend  │ ──▶ │  Python AI Service   │
│   (Next.js)  │     │  Express · Auth    │     │  Agentic RAG logic   │
│              │ ◀── │  Orchestration     │ ◀── │  Retrieval · LLM     │
└──────────────┘     └─────────┬──────────┘     └──────────────────────┘
                               │
                         ┌─────▼─────┐
                         │ PostgreSQL │
                         └───────────┘

Request flow

User submits a question from the frontend.
Node receives it at POST /api/research.
Node forwards it to the Python service at POST /research.
Python runs the research pipeline and returns the structured result.
Node saves the result to PostgreSQL and responds to the user.

Design decisions

Node.js / TypeScript backend — auth, HTTP API, orchestration, database ownership.
Python AI service — agentic logic, retrieval, embeddings. Stateless, no database access.
API-based models — no local model hosting required.
Repository Structure
scout-ai/
├── scout-frontend/      # Next.js research workspace and landing page
├── backend-node/        # Express API: auth, orchestration, persistence
├── ai-service-python/   # Research pipeline: retrieval, synthesis, verification
└── .gitignore
Tech Stack
Layer	Technology
Frontend	Next.js (App Router), React, Tailwind CSS, Motion, lucide-react
Backend	Node.js, TypeScript, Express
AI Service	Python
Database	PostgreSQL
Deployment	Vercel (frontend)
Getting Started
Prerequisites
Node.js 18+
Python 3.10+
PostgreSQL
API keys for your LLM provider and search provider
1. Clone
bash
git clone https://github.com/YASHdroid/scout-ai.git
cd scout-ai
2. Python AI service
bash
cd ai-service-python
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your API keys

Run the service (adjust to your entry point):

bash
uvicorn main:app --reload --port 8000
3. Node backend
bash
cd backend-node
npm install
cp .env.example .env            # DB URL, JWT secret, AI service URL
npm run dev
4. Frontend
bash
cd scout-frontend
npm install
cp .env.example .env.local      # backend API URL
npm run dev

Open http://localhost:3000.

Environment Variables
Variable	Service	Description
DATABASE_URL	backend-node	PostgreSQL connection string
JWT_SECRET	backend-node	Secret for signing auth tokens
AI_SERVICE_URL	backend-node	Base URL of the Python service
LLM_API_KEY	ai-service-python	LLM provider API key
SEARCH_API_KEY	ai-service-python	Web search provider API key
NEXT_PUBLIC_API_URL	scout-frontend	Base URL of the Node backend

Variable names above are the expected defaults — match them to your actual .env.example files.

API
POST /api/research (Node)
json
{ "question": "Does intermittent fasting improve longevity?" }

Returns the saved research report: findings, evidence, sources, and any detected conflicts.

POST /research (Python, internal)

Called only by the Node backend. Runs the pipeline and returns structured results. Not exposed publicly.

Roadmap
 Foundation: polyglot services and request flow
 RAG core
 Web research
 Better retrieval (hybrid search + reranking)
 Research engine (question decomposition, synthesis)
 Trust layer (citation grounding, conflict detection)
 Agentic research (tool calling)
 Evaluation suite
 Full research workspace UI
 Production hardening (Docker, deployment, observability)

Update the checkboxes to reflect your actual progress.

Author

Yash — B.Tech CSE, MAIT New Delhi GitHub: @YASHdroid
