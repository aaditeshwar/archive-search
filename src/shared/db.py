"""MongoDB connection and collection accessors."""

from pymongo import MongoClient
from pymongo.database import Database

from src.shared.config import get_config


def get_db() -> Database:
    """Return MongoDB database instance."""
    cfg = get_config()
    client = MongoClient(cfg["mongodb_uri"])
    return client[cfg["mongodb_db"]]


def get_messages_collection():
    """Return messages collection."""
    cfg = get_config()
    return get_db()[cfg["messages_collection"]]


def get_linked_docs_collection():
    """Return linked_docs collection."""
    cfg = get_config()
    return get_db()[cfg["linked_docs_collection"]]


def get_chunks_collection():
    """Return chunks collection (for vector search)."""
    cfg = get_config()
    return get_db()[cfg["chunks_collection"]]


def get_state_collection():
    """Return state collection (last update cursor)."""
    cfg = get_config()
    return get_db()[cfg["state_collection"]]


def get_sessions_collection():
    """Return sessions collection (for API session store in MongoDB)."""
    cfg = get_config()
    return get_db()[cfg["sessions_collection"]]
