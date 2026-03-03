# Archive Search

Web app to search a mailing list archive (Google Groups) using natural language. Indexes message content and linked articles/PDFs, then supports semantic search and optional LLM-generated answers via a chat UI. Embeddings and chat can use **OpenAI** or **Ollama** (local); see [docs/INSTALL.md](docs/INSTALL.md).

## Components

- **Indexer CLI**: Fetches messages from the CoRE stack NRM Google Group, extracts links, fetches and chunks linked content, embeds and stores in MongoDB.
- **Query API**: FastAPI app exposing search and session endpoints; vector search + optional LLM answer.
- **Frontend**: Chat interface to query the archive.

## Quick start

See [docs/INSTALL.md](docs/INSTALL.md) for full installation and run instructions.

```bash
# Backend
pip install -e .
cp .env.example .env   # edit .env
python -m src.indexer build --full   # first-time index
uvicorn src.api.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## License

AGPL version 3
