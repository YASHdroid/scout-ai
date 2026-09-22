import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing")

if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY is missing")

if not POSTGRES_PASSWORD:
    raise RuntimeError("POSTGRES_PASSWORD is missing")
