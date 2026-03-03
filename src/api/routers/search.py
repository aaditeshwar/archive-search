"""Search/query endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import chunks_collection
from src.api.services.search import search as run_search
from src.shared.models import SearchRequest, SearchResponse

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def post_search(req: SearchRequest, chunks=Depends(chunks_collection)) -> SearchResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    return run_search(chunks, req.query, top_k=req.top_k, with_answer=req.with_answer)

