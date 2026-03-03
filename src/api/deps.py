"""FastAPI dependencies and shared instances."""

from functools import lru_cache

from pymongo.collection import Collection

from src.shared.config import get_config
from src.shared.db import get_chunks_collection, get_sessions_collection
from src.shared.embeddings import get_embedding_client


@lru_cache(maxsize=1)
def embedding_client():
    return get_embedding_client()


def chunks_collection() -> Collection:
    return get_chunks_collection()


def sessions_collection() -> Collection:
    return get_sessions_collection()


def config() -> dict:
    return get_config()

