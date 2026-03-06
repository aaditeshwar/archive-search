"""Vector search and optional answer generation."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from openai import OpenAI
from pymongo.collection import Collection

from src.shared.config import get_config
from src.shared.embeddings import embed_query, get_embedding_client
from src.shared.models import SearchChunk, SearchResponse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    logger.addHandler(_h)
VECTOR_INDEX_NAME = "chunks_vector_index"


def vector_search(
    chunks: Collection,
    query: str,
    *,
    top_k: int = 10,
    index_name: str = VECTOR_INDEX_NAME,
) -> list[dict[str, Any]]:
    t0 = time.perf_counter()
    client = get_embedding_client()
    t_embed_start = time.perf_counter()
    qvec = embed_query(client, query)
    embed_s = time.perf_counter() - t_embed_start

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
    t_atlas_start = time.perf_counter()
    raw = list(chunks.aggregate(pipeline))
    atlas_s = time.perf_counter() - t_atlas_start
    total_s = time.perf_counter() - t0
    logger.info(
        "search profile | vector_search: total=%.3fs embed_query=%.3fs atlas_aggregate=%.3fs",
        total_s,
        embed_s,
        atlas_s,
    )
    return raw


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
    t0 = time.perf_counter()
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
    elapsed = time.perf_counter() - t0
    logger.info("search profile | openai_chat: %.3fs", elapsed)
    return (resp.choices[0].message.content or "").strip() or None


def _generate_answer_ollama(query: str, chunks: list[SearchChunk]) -> str | None:
    cfg = get_config()
    base_url = (cfg.get("ollama_base_url") or "http://localhost:11434").rstrip("/")
    model = cfg.get("ollama_chat_model") or "qwen2.5:3b"
    context = _format_chunks_for_llm(chunks[:10])
    t0 = time.perf_counter()
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
    elapsed = time.perf_counter() - t0
    logger.info("search profile | ollama_chat: %.3fs model=%s", elapsed, model)
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
    t_total = time.perf_counter()
    t0 = time.perf_counter()
    raw = vector_search(chunks_coll, query, top_k=top_k)
    vector_search_s = time.perf_counter() - t0

    t0 = time.perf_counter()
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
    map_s = time.perf_counter() - t0

    answer = None
    generate_answer_s = 0.0
    if with_answer:
        t0 = time.perf_counter()
        answer = maybe_generate_answer(query, mapped)
        generate_answer_s = time.perf_counter() - t0

    total_s = time.perf_counter() - t_total
    logger.info(
        "search profile | total=%.3fs vector_search=%.3fs map_results=%.3fs generate_answer=%.3fs with_answer=%s",
        total_s,
        vector_search_s,
        map_s,
        generate_answer_s,
        with_answer,
    )
    return SearchResponse(chunks=mapped, answer=answer)

