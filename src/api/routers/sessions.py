"""Session endpoints (MongoDB-backed)."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import sessions_collection
from src.api.services.session_store import MongoSessionStore
from src.shared.models import SessionMessage, SessionResponse

router = APIRouter(prefix="/api", tags=["sessions"])


def _store(coll=Depends(sessions_collection)) -> MongoSessionStore:
    return MongoSessionStore(coll)


@router.post("/sessions", response_model=SessionResponse)
def create_session(store: MongoSessionStore = Depends(_store)) -> SessionResponse:
    return store.create()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, store: MongoSessionStore = Depends(_store)) -> SessionResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.post("/sessions/{session_id}/messages", response_model=SessionResponse)
def append_message(
    session_id: str,
    msg: SessionMessage,
    store: MongoSessionStore = Depends(_store),
) -> SessionResponse:
    if msg.role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="role must be user or assistant")
    if not msg.content.strip():
        raise HTTPException(status_code=400, detail="content is required")
    return store.append(session_id, msg)

