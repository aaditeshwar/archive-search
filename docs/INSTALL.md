# Installation and setup

(To be completed: prerequisites, env vars, run commands.)

## System prerequisites

- Python 3.11+
- Node 18+ (for frontend)
- MongoDB 6+ with vector search (local or Atlas)

## Python setup

```bash
python -m venv .venv
# Activate: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Unix)
pip install -e .
# Optional local embeddings: pip install -e ".[local-embeddings]"
```

Copy `.env.example` to `.env` and set `MONGODB_URI`, `OPENAI_API_KEY` (if using OpenAI), etc.

## Running

- Indexer (full): `python -m src.indexer build --full`
- Indexer (incremental): `python -m src.indexer update`
- API: `uvicorn src.api.main:app --reload --port 8000`
- Frontend: `cd frontend && npm install && npm run dev`
