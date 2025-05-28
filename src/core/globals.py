import os
import json

from pathlib import Path


BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"

LLM_PROXY_ADDRESS = os.environ["LLM_PROXY_ADDRESS"]
DEFAULT_MCPL_SERVERS = json.loads(os.environ.get("DEFAULT_MCPL_SERVERS", "[]"))
