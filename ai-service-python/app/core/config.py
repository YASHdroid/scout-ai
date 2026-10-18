
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")


if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY is missing")

if not POSTGRES_PASSWORD:
    raise RuntimeError("POSTGRES_PASSWORD is missing")
