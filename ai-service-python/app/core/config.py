import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing")

if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY is missing")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing")