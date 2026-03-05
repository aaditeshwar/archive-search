# Installation and setup

This repo has three main parts:

- **Indexer CLI**: scrapes the Google Group, extracts links, fetches linked content, chunks+embeds, writes to MongoDB
- **API**: FastAPI query API using MongoDB vector search
- **Frontend**: Vite+React chat UI calling the API

## System prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend build and dev server)
- **MongoDB** – local Community Server or **MongoDB Atlas** (vector search is supported on Atlas; see below)
- **Selenium + Chrome** for Google Groups scraping (Chrome + ChromeDriver on PATH)
- **Ollama** (optional) for local embeddings/chat – [ollama.ai](https://ollama.ai), default `http://localhost:11434`

---

## Installing development tools

### Python and uvicorn

- Install **Python 3.11+** from [python.org](https://www.python.org/downloads/) or your OS package manager (e.g. `sudo apt install python3.11 python3.11-venv` on Ubuntu).
- Create and activate a virtualenv, then install the project (this pulls in **uvicorn** and all app deps):
  ```bash
  python -m venv .venv
  .venv\Scripts\activate   # Windows
  # source .venv/bin/activate   # Linux/macOS
  pip install -e .
  ```
- Run the API with uvicorn (included; no separate install):
  ```bash
  uvicorn src.api.main:app --reload --port 8000
  ```

### Node.js and npm

- Install **Node.js 18+** (includes **npm**):
  - [nodejs.org](https://nodejs.org/) (LTS), or
  - Ubuntu/Debian: `sudo apt install nodejs npm`
  - Windows: use the Node installer or Chocolatey (`choco install nodejs-lts`).
- From the project root, install frontend deps and run the dev server:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```

---

## MongoDB installation

You can use **MongoDB Atlas** (cloud, with vector search) or **MongoDB Community Server** (local). Vector search (`$vectorSearch`) is available on **Atlas**; for a local-only setup you may need to rely on Atlas or a MongoDB build that supports it.

### Option A: MongoDB Atlas cloud

1. Sign up at [mongodb.com/atlas](https://www.mongodb.com/atlas) and create a free cluster (e.g. M0).
2. Under **Database** → **Connect** → **Drivers**, copy the connection string (e.g. `mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`).
3. In **Database** → **Browse Collections**, create a database (e.g. `archive_search`) and collections as needed (the indexer and API will create `messages`, `linked_docs`, `chunks`, `state`, `sessions` when you run them).
4. Create the **vector search index** on the `chunks` collection:
  - Go to **Atlas Search** (or **Search** in the left menu) → **Create Search Index**.
  - Choose **JSON Editor** and use an index definition like (adjust `numDimensions` to your embedding size, e.g. 768 for nomic-embed-text):
5. Set in `.env`:
  ```
   MONGODB_URI=mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   MONGODB_DB=archive_search
  ```
   Replace `user`/`password` and cluster host with your values. Restrict Atlas **Network Access** (e.g. your server IP or `0.0.0.0/0` for dev only).

### Option B: MongoDB Community Server through Atlas (local)

~~1. Install **MongoDB Community Server**:~~
  - [Installation docs](https://www.mongodb.com/docs/manual/installation/)
  - Windows: [Windows install](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/)
  - Ubuntu: `sudo apt install mongodb` or follow the official repo setup for your version.
~~2. Start the service:~~
  - Windows: run **MongoDB** service from Services (or `net start MongoDB`).
  - Linux (to create a service): `sudo systemctl enable mongod` (or `mongodb`).
  - Linux: `sudo systemctl start mongod` (or `mongodb`).
3. Install MongoDB via Atlas docker
  - `curl -L https://repo.mongodb.org -o atlas-cli.deb`
  - `sudo dpkg -i mongodb-atlas-cli_<version>_linux_amd64.deb`
  - Create `docker-compose.yaml`
  - `docker compose up -d`
4. Create the database and indexes (the app will create collections on first use). Run:
  ```bash
   python scripts/create_vector_index.py
  ```
   If the script reports that the **vector** index could not be created (common on plain Community Server), vector search will not work until you use **Atlas** or a MongoDB build that supports it. The script still creates the regular (B-tree) indexes.
5. Set in `.env`:
  ```
   MONGODB_URI=mongodb://localhost:27017
   MONGODB_DB=archive_search
  ```

## Ollama setup (local embeddings and chat)

If you use `EMBEDDING_MODEL=ollama` and/or `LLM_PROVIDER=ollama`:

1. Install [Ollama](https://ollama.ai) and start the server (usually runs in the background after install).
2. Pull the embedding model (must match `EMBEDDING_DIMENSION` in `.env`):
  ```bash
   ollama pull nomic-embed-text
  ```
   For `nomic-embed-text`, set `EMBEDDING_DIMENSION=768` and `OLLAMA_EMBED_MODEL=nomic-embed-text`.
3. Pull a chat model for generated answers (when `ENABLE_LLM_ANSWER=true`):
  ```bash
   ollama pull qwen2.5:3b
  ```
   Set `OLLAMA_CHAT_MODEL=qwen2.5:3b` in `.env` (or another model you prefer).
4. Optional: set `OLLAMA_BASE_URL` if Ollama runs elsewhere (e.g. `http://192.168.1.10:11434`).

## Python setup

```bash
python -m venv .venv
# Activate: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Unix)
pip install -e .
# Optional: pip install -e ".[local-embeddings]" for sentence-transformers
# Optional: pip install -e ".[ollama]" for Ollama (ollama is in main deps by default)
```

Copy `.env.example` to `.env` and set at least:

- `MONGODB_URI`, `MONGODB_DB`
- For **Ollama**: `EMBEDDING_MODEL=ollama`, `OLLAMA_EMBED_MODEL=nomic-embed-text`, `EMBEDDING_DIMENSION=768`, and optionally `ENABLE_LLM_ANSWER=true`, `LLM_PROVIDER=ollama`, `OLLAMA_CHAT_MODEL=qwen2.5:3b`
- For **OpenAI**: `OPENAI_API_KEY`, `EMBEDDING_MODEL=openai`, `EMBEDDING_DIMENSION=1536`, and optionally `LLM_PROVIDER=openai`

## MongoDB indexes (required)

Create the unique indexes and the vector search index:

```bash
python scripts/create_vector_index.py
```

If the script cannot create the vector index automatically (common when not using Atlas / not enabled),
it will print the JSON definition you should create manually in your MongoDB UI.

## Running

- **Indexer (full)**:

```bash
python -m src.indexer build --full --limit 10 --start-index 0 --no-headless
```

Or if you are just fetching the messages and their links.

```bash
python -m src.indexer build --full --load-urls-from-file --limit 10 --start-index 0 --no-headless
```

- **Indexer (incremental)**:

```bash
python -m src.indexer update --limit 10
```

Add `--no-headless` if you want to watch the Selenium browser while debugging.

- **API**:

```bash
uvicorn src.api.main:app --reload --port 8000
```

- **Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Optionally set `VITE_API_BASE` in `frontend/.env` to point at a non-local API base URL.

## Quick test (API)

After indexing and starting the API:

- `GET http://localhost:8000/healthz`
- `POST http://localhost:8000/api/search` with JSON:

```json
{ "query": "wetlands restoration floods China", "top_k": 5, "with_answer": false }
```

---

## Production deployment behind Apache

For production, run the FastAPI app with a stable ASGI server and put **Apache** in front as a reverse proxy. Serve the built frontend as static files and proxy `/api` (and optionally `/healthz`) to the backend.

### 1. Build the frontend

From the project root:

```bash
cd frontend
npm ci
npm run build
```

This creates `frontend/dist/` with static assets. The app expects the API at the same origin or set `VITE_API_BASE` before building (e.g. in `frontend/.env.production`: `VITE_API_BASE=https://yourdomain.com` so requests go to `https://yourdomain.com/api`).

### 2. Run the API as a service

Run uvicorn (or gunicorn with uvicorn workers) so it keeps running and listens on a port (e.g. `127.0.0.1:8000`). Examples:

**Using systemd (Linux):**

Create `/etc/systemd/system/archive-search-api.service`:

```ini
[Unit]
Description=Archive Search FastAPI app
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/archive-search
Environment="PATH=/path/to/archive-search/.venv/bin"
ExecStart=/path/to/archive-search/.venv/bin/uvicorn src.api.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable archive-search-api
sudo systemctl start archive-search-api
```

**Using a process manager (e.g. Gunicorn + Uvicorn):**

```bash
pip install gunicorn
gunicorn src.api.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
```

Run this via systemd or your preferred supervisor.

### 3. Apache configuration

Enable proxy modules and site config:

```bash
sudo a2enmod proxy proxy_http headers
```

Create a VirtualHost (e.g. `/etc/apache2/sites-available/archive-search.conf`) that:

- Proxies `/api` and `/healthz` to the backend (e.g. `http://127.0.0.1:8000`).
- Serves the frontend static files from `frontend/dist/` and uses a fallback to `index.html` for client-side routing.

Example (adjust paths and domain):

```apache
<VirtualHost *:80>
    ServerName yourdomain.com
    # Optional: redirect HTTP to HTTPS
    # Redirect permanent / https://yourdomain.com/

    # Backend API
    ProxyPreserveHost On
    ProxyPass /api http://127.0.0.1:8000/api
    ProxyPassReverse /api http://127.0.0.1:8000/api
    ProxyPass /healthz http://127.0.0.1:8000/healthz
    ProxyPassReverse /healthz http://127.0.0.1:8000/healthz

    # Frontend (SPA): serve static files, fallback to index.html for client-side routes
    DocumentRoot /path/to/archive-search/frontend/dist
    <Directory /path/to/archive-search/frontend/dist>
        Require all granted
        Options -Indexes
        FallbackResource /index.html
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/archive-search-error.log
    CustomLog ${APACHE_LOG_DIR}/archive-search-access.log combined
</VirtualHost>
```

If you use **HTTPS** (recommended in production), add a `<VirtualHost *:443>` block with `SSLEngine on`, `SSLCertificateFile` / `SSLCertificateKeyFile`, and the same `ProxyPass` and `DocumentRoot` as above. Enable `ssl` and `proxy` modules.

Enable the site and reload Apache:

```bash
sudo a2ensite archive-search
sudo systemctl reload apache2
```

### 4. Production checklist

- Set a strong `MONGODB_URI` and restrict Atlas network access to the server IP.
- In `.env` on the server, do not use `OPENAI_API_KEY` (or any secrets) in logs; keep `.env` outside the web root and readable only by the app user.
- Ensure the API runs as a dedicated user (e.g. `www-data`) and that file permissions on the repo and `.venv` are restrictive.
- If the frontend is built with `VITE_API_BASE` unset, the browser will call the API on the same host (the one Apache serves), so the proxy to `127.0.0.1:8000` is enough. If you use a different API URL, set `VITE_API_BASE` before `npm run build`.

