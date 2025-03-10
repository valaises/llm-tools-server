import os


MESSAGES_TOK_LIMIT = 32_000
LLM_PROXY_ADDRESS = os.environ.get(
    "LLM_PROXY_ADDRESS", "http://home.valerii.cc:7012/v1"
)
