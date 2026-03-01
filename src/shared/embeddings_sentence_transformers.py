"""Sentence-transformers embedding client (local)."""


class SentenceTransformerEmbeddings:
    """Local embeddings via sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts."""
        if not texts:
            return []
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query."""
        return self._model.encode(query, convert_to_numpy=True).tolist()
