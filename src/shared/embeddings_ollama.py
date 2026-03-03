"""Ollama embedding client (local)."""

import ollama

class OllamaEmbeddings:
    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        return [
            ollama.embeddings(model=self.model_name, prompt=text)["embedding"]
            for text in texts
        ]

    def embed_query(self, query: str) -> list[float]:
        response = ollama.embeddings(
            model=self.model_name,
            prompt=query,
        )
        return response["embedding"]