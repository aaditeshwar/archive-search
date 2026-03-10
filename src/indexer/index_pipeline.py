"""Orchestrate: fetch messages -> extract links -> fetch linked content -> chunk -> embed -> upsert."""

import hashlib
import logging
from datetime import datetime

from src.shared.config import get_config
from src.shared.db import (
    get_chunks_collection,
    get_linked_docs_collection,
    get_messages_collection,
    get_state_collection,
)
from src.shared.embeddings import get_embedding_client, embed_texts
from src.shared.chunking import chunk_text
from src.shared.models import Message

from src.indexer.fetch_groups import fetch_group_messages
from src.indexer.extract_links import extract_links
from src.indexer.fetch_linked import fetch_and_extract, normalize_url, fetch_with_selenium

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _chunk_id(source_type: str, message_id: str, linked_url: str, index: int) -> str:
    """Stable chunk id for upsert."""
    raw = f"{source_type}:{message_id}:{linked_url}:{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _get_last_message_cursor() -> str | None:
    """Return last seen message_id from state collection."""
    state = get_state_collection().find_one({"_id": "indexer"})
    return (state or {}).get("last_message_id")


def _set_last_message_cursor(message_id: str) -> None:
    """Persist last seen message_id."""
    get_state_collection().update_one(
        {"_id": "indexer"},
        {"$set": {"last_message_id": message_id, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


def run_pipeline(
    full_rebuild: bool = False,
    group_url: str | None = None,
    load_urls_from_file: bool = False,
    skip_linked: bool = False,
    limit_topics: int | None = None,
    start_index: int | None = None,
    headless: bool = True,
    proxy_url: str | None = None,
) -> None:
    """
    Run full index pipeline: fetch messages (incremental unless full_rebuild),
    extract links, fetch linked docs, chunk, embed, upsert to MongoDB.
    """
    cfg = get_config()
    group_url = group_url or cfg["group_url"]
    topic_urls_file = cfg["topic_urls_file"]
    messages_coll = get_messages_collection()
    linked_coll = get_linked_docs_collection()
    chunks_coll = get_chunks_collection()

    since_id = None if full_rebuild else _get_last_message_cursor()
    logger.info("Fetching messages from %s (full=%s)", group_url, full_rebuild)
    messages = fetch_group_messages(
        group_url,
        load_urls_from_file,
        topic_urls_file,
        limit_topics=limit_topics,
        start_index=start_index,
        since_message_id=since_id,
        headless=headless,
        proxy_url=proxy_url,
    )
    if not messages:
        logger.warning("No messages fetched. Group may be JS-rendered; consider using Playwright.")
        return

    # Extract links and optionally fetch linked content
    all_chunk_docs = []
    latest_message_id = None
    for msg in messages:
        links = extract_links(msg.body)
        msg.links = links
        messages_coll.update_one(
            {"message_id": msg.message_id},
            {"$set": msg.model_dump()},
            upsert=True,
        )
        if msg.message_id:
            latest_message_id = msg.message_id

        if skip_linked or not links:
            # Chunk message body only
            text = f"Subject: {msg.subject}\n\n{msg.body}".strip()
            if not text:
                continue
            for i, chunk_text_val in enumerate(chunk_text(text)):
                all_chunk_docs.append({
                    "chunk_id": _chunk_id("message", msg.message_id, "", i),
                    "text": chunk_text_val,
                    "source_type": "message",
                    "message_id": msg.message_id,
                    "message_url": msg.url,
                    "linked_url": "",
                    "metadata": {"subject": msg.subject, "chunk_index": i},
                })
            continue

        # Chunk message
#        text = f"Subject: {msg.subject}\n\n{msg.body}".strip()
        text = msg.body.strip()
        if text:
            for i, ct in enumerate(chunk_text(text)):
                all_chunk_docs.append({
                    "chunk_id": _chunk_id("message", msg.message_id, "", i),
                    "text": ct + "\n" + msg.subject,
                    "source_type": "message",
                    "message_id": msg.message_id,
                    "message_url": msg.url,
                    "linked_url": links[0],
                    "metadata": {"subject": msg.subject, "chunk_index": i},
                })

        # Fetch and chunk linked docs
        for url in links:
            norm = normalize_url(url)
            existing = linked_coll.find_one({"url": norm})
            if existing and existing.get("raw_text"):
                title = existing.get("title", "")
                raw_text = existing["raw_text"]
            else:
                try:
                    # @aseth - use selenium with head to download
#                    title, raw_text = fetch_and_extract(url)
                    dummy, raw_text = fetch_with_selenium(url)
                    prev = linked_coll.find_one({"url": norm}) or {}
                    msg_ids = list(set(prev.get("message_ids", []) + [msg.message_id]))
                    linked_coll.update_one(
                        {"url": norm},
                        {
                            "$set": {
                                "url": norm,
                                "title": title,
                                "content_type": "html",
                                "raw_text": raw_text,
                                "message_ids": msg_ids,
                                "fetched_at": datetime.utcnow(),
                                "fetch_failed": False,
                            }
                        },
                        upsert=True,
                    )
                except Exception as e:
                    logger.warning("Failed to fetch %s: %s", url, e)
                    linked_coll.update_one(
                        {"url": norm},
                        {"$set": {"fetch_failed": True, "message_ids": [msg.message_id]}},
                        upsert=True,
                    )
                    continue
            if not raw_text or len(raw_text.strip()) < 50:
                continue
            for j, ct in enumerate(chunk_text(raw_text)):
                all_chunk_docs.append({
                    "chunk_id": _chunk_id("linked_page", msg.message_id, norm, j),
                    "text": ct + "\n" + msg.subject,
                    "source_type": "linked_page",
                    "message_id": msg.message_id,
                    "message_url": msg.url,
                    "linked_url": norm,
                    "metadata": {"title": title or url, "chunk_index": j},
                })

    if latest_message_id:
        _set_last_message_cursor(latest_message_id)

    if not all_chunk_docs:
        logger.info("No chunks to embed.")
        return

    # Embed and upsert chunks
    logger.info("Embedding %d chunks", len(all_chunk_docs))
    client = get_embedding_client()
    texts = [d["text"] for d in all_chunk_docs]
    embeddings = embed_texts(client, texts)
    for d, emb in zip(all_chunk_docs, embeddings):
        d["embedding"] = emb
        chunks_coll.update_one(
            {"chunk_id": d["chunk_id"]},
            {"$set": d},
            upsert=True,
        )
    logger.info("Indexed %d chunks.", len(all_chunk_docs))
