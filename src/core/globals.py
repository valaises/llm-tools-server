import os
from pathlib import Path


BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"

MESSAGES_TOK_LIMIT = 128_000

LLM_PROXY_ADDRESS = os.environ["LLM_PROXY_ADDRESS"]
