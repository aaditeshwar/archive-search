"""Embedding client: OpenAI or sentence-transformers."""

from src.shared.config import get_config


def get_embedding_client():
    """Return an embedding client (OpenAI or sentence-transformers)."""
    cfg = get_config()
    model = cfg["embedding_model"]
    if model == "sentence-transformers":
        from src.shared.embeddings_sentence_transformers import SentenceTransformerEmbeddings

        return SentenceTransformerEmbeddings(
            model_name=cfg.get("sentence_transformers_model", "all-MiniLM-L6-v2")
        )
    elif model == "ollama":
        from src.shared.embeddings_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model_name=cfg.get("ollama_embed_model", "nomic-embed-text"))

    # default: openai
    from src.shared.embeddings_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        api_key=cfg.get("openai_api_key", ""),
        model="text-embedding-3-small",
        dimension=cfg.get("embedding_dimension", 1536),
    )


def embed_texts(client, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns list of embedding vectors."""
    return client.embed_documents(texts)


def embed_query(client, query: str) -> list[float]:
    """Embed a single query string."""
    return client.embed_query(query)
