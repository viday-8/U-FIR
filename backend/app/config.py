import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ufir.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret")
STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # anthropic | openai (openai also works with Ollama via OPENAI_BASE_URL)
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5" if LLM_PROVIDER == "anthropic" else "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
EXTRACTOR = os.getenv("EXTRACTOR", "rules")  # rules (open-source, offline) | llm
MODEL_LABEL = "rules-v1" if EXTRACTOR == "rules" else LLM_MODEL
COPILOT_LLM = os.getenv("COPILOT_LLM", "0") == "1"  # optional LLM phrasing of answers; retrieval and citations are always local
ENV = os.getenv("ENV", "demo")  # set ENV=production to refuse the default JWT secret
if ENV == "production" and JWT_SECRET == "dev-only-secret":
    raise RuntimeError("Set JWT_SECRET to a long random value when ENV=production")
