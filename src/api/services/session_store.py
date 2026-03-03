"""Session storage (MongoDB-backed)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pymongo.collection import Collection

from src.shared.models import SessionMessage, SessionResponse


class MongoSessionStore:
    def __init__(self, coll: Collection):
        self.coll = coll

    def create(self) -> SessionResponse:
        session_id = uuid4().hex
        doc = {"session_id": session_id, "messages": [], "created_at": datetime.utcnow()}
        self.coll.insert_one(doc)
        return SessionResponse(session_id=session_id, messages=[], created_at=doc["created_at"])

    def get(self, session_id: str) -> SessionResponse | None:
        doc = self.coll.find_one({"session_id": session_id})
        if not doc:
            return None
        msgs = [SessionMessage(**m) for m in doc.get("messages", [])]
        return SessionResponse(
            session_id=session_id,
            messages=msgs,
            created_at=doc.get("created_at") or datetime.utcnow(),
        )

    def append(self, session_id: str, message: SessionMessage) -> SessionResponse:
        self.coll.update_one(
            {"session_id": session_id},
            {"$push": {"messages": message.model_dump()}},
            upsert=True,
        )
        session = self.get(session_id)
        if session is None:
            # should not happen due to upsert, but keep safe
            return SessionResponse(session_id=session_id, messages=[message])
        return session

