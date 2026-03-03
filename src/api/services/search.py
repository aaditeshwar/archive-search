"""Vector search and optional answer generation."""

from __future__ import annotations

from typing import Any

import requests
from openai import OpenAI
from pymongo.collection import Collection

from src.shared.config import get_config
from src.shared.embeddings import embed_query, get_embedding_client
from src.shared.models import SearchChunk, SearchResponse

VECTOR_INDEX_NAME = "chunks_vector_index"


def vector_search(
    chunks: Collection,
    query: str,
    *,
    top_k: int = 10,
    index_name: str = VECTOR_INDEX_NAME,
) -> list[dict[str, Any]]:
    client = get_embedding_client()
    qvec = embed_query(client, query)

    pipeline = [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": "embedding",
                "queryVector": qvec,
                "numCandidates": max(50, top_k * 10),
                "limit": top_k,
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "source_type": 1,
                "message_id": 1,
                "message_url": 1,
                "linked_url": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    return list(chunks.aggregate(pipeline))


def _format_chunks_for_llm(results: list[SearchChunk]) -> str:
    parts = []
    for i, c in enumerate(results, start=1):
        title = c.title or ""
        src = c.message_url or c.linked_url or ""
        parts.append(f"[{i}] {title} {src}\n{c.text}")
    return "\n\n".join(parts)


def _generate_answer_openai(query: str, chunks: list[SearchChunk]) -> str | None:
    cfg = get_config()
    if not cfg.get("openai_api_key"):
        return None
    context = _format_chunks_for_llm(chunks[:10])
    oai = OpenAI(api_key=cfg["openai_api_key"])
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Answer using only the provided context. If unsure, say you don't know.",
            },
            {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip() or None


def _generate_answer_ollama(query: str, chunks: list[SearchChunk]) -> str | None:
    cfg = get_config()
    base_url = (cfg.get("ollama_base_url") or "http://localhost:11434").rstrip("/")
    model = cfg.get("ollama_chat_model") or "qwen2.5:3b"
    context = _format_chunks_for_llm(chunks[:10])
    response = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Answer using only the provided context. If unsure, say you don't know.",
                },
                {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
            ],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return (data.get("message", {}).get("content") or "").strip() or None


def maybe_generate_answer(query: str, chunks: list[SearchChunk]) -> str | None:
    cfg = get_config()
    if not cfg.get("enable_llm_answer"):
        return None
    provider = cfg.get("llm_provider", "ollama").lower()
    if provider == "openai" and cfg.get("openai_api_key"):
        return _generate_answer_openai(query, chunks)
    return _generate_answer_ollama(query, chunks)


def search(
    chunks_coll: Collection,
    query: str,
    *,
    top_k: int = 10,
    with_answer: bool = False,
) -> SearchResponse:
    raw = vector_search(chunks_coll, query, top_k=top_k)
    mapped: list[SearchChunk] = []
    for r in raw:
        md = r.get("metadata") or {}
        mapped.append(
            SearchChunk(
                text=r.get("text", ""),
                source_type=r.get("source_type", ""),
                message_id=r.get("message_id", ""),
                message_url=r.get("message_url", ""),
                linked_url=r.get("linked_url", ""),
                title=md.get("title") or md.get("subject") or "",
                score=float(r.get("score") or 0.0),
            )
        )
    answer = maybe_generate_answer(query, mapped) if with_answer else None
    return SearchResponse(chunks=mapped, answer=answer)

