"""OpenAI embedding client."""

from openai import OpenAI


class OpenAIEmbeddings:
    """OpenAI embeddings (text-embedding-3-small or similar)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimension: int = 1536):
        self.client = OpenAI(api_key=api_key or None)  # None uses OPENAI_API_KEY from env
        self.model = model
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts."""
        if not texts:
            return []
        resp = self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimension,
        )
        return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query."""
        resp = self.client.embeddings.create(
            model=self.model,
            input=query,
            dimensions=self.dimension,
        )
        return resp.data[0].embedding
