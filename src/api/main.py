"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.search import router as search_router
from src.api.routers.sessions import router as sessions_router


def create_app() -> FastAPI:
    app = FastAPI(title="Archive Search API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(search_router)
    app.include_router(sessions_router)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


app = create_app()

