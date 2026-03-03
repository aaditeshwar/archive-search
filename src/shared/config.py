"""Application configuration from environment."""

import os

from dotenv import load_dotenv

load_dotenv()


def get_config() -> dict:
    """Return config dict from environment (and defaults)."""
    return {
        "mongodb_uri": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        "mongodb_db": os.getenv("MONGODB_DB", "archive_search"),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "openai"),
        "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "1536")),
        "sentence_transformers_model": os.getenv("SENTENCE_TRANSFORMERS_MODEL", "all-MiniLM-L6-v2"),
        "ollama_embed_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        "ollama_chat_model": os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "enable_llm_answer": os.getenv("ENABLE_LLM_ANSWER", "false").lower() in ("true", "1", "yes"),
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama").lower(),  # openai | ollama
        "redis_url": os.getenv("REDIS_URL", ""),
        "group_url": os.getenv("GROUP_URL", "https://groups.google.com/g/core-stack-nrm/"),
        "topic_urls_file": os.getenv("TOPIC_URLS_FILE", "data/topic_urls.txt"),
        "chunks_collection": "chunks",
        "messages_collection": "messages",
        "linked_docs_collection": "linked_docs",
        "state_collection": "state",
        "sessions_collection": "sessions",
    }
