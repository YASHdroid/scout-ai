import os
import sys
from pathlib import Path

# Fake credentials so modules that validate env vars at import time load.
# No test makes a real network call: LLM and web search are always mocked.
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("INTERNAL_API_SECRET", "test-secret")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
