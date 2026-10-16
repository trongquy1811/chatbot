import logging
import threading
from contextlib import asynccontextmanager
from typing import Any
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api import chat, conversations, documents, memories
from backend.auth import get_current_user
from backend.config import Settings, get_settings
from backend.database import get_db, get_engine, get_session_factory, init_db
from backend.schemas import HealthResponse
from backend.services.cache import RetrievalCache
from backend.services.gemini import Gemini
from backend.services.sessions import SessionStore
from backend.services.vectors import Vectors

logger = logging.getLogger("docanalyzer.main")


def create_app(
    settings: Settings | None = None,
    ai: Gemini | None = None,
    vector_client: Any | None = None,
) -> FastAPI:
    """Create and configure FastAPI application instance with full Agent Harness lifecycle."""
    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        try:
            keys = cfg.keys()
        except Exception as exc:
            logger.error("LỖI CẤU HÌNH KHỞI ĐỘNG: %s", exc)
            raise RuntimeError(f"Khởi động thất bại do cấu hình: {exc}") from exc

        engine = get_engine(cfg)
        init_db(engine)
        session_factory = get_session_factory(engine)

        gemini_provider = ai or (Gemini(cfg) if cfg.google_api_key else None)

        application.state.cfg = cfg
        application.state.keys = keys
        application.state.engine = engine
        application.state.sessions = session_factory
        application.state.ai = gemini_provider

        application.state.vectors = Vectors(
            settings=cfg,
            embeddings=gemini_provider.embeddings if gemini_provider else None,
            client=vector_client,
        )

        application.state.cache = RetrievalCache(cfg.redis_url)

        application.state.sessions_store = SessionStore(
            redis_client=application.state.cache.client
        )

        application.state.operation_lock = threading.Lock()

        logger.info("Application lifespan started successfully")
        try:
            yield
        finally:
            logger.info("Shutting down application lifespan...")
            if hasattr(application.state.vectors, "client") and application.state.vectors.client:
                try:
                    application.state.vectors.client.close()
                except Exception:
                    pass

            if application.state.cache.client:
                try:
                    application.state.cache.client.close()
                except Exception:
                    pass

            engine.dispose()
            logger.info("Application resources disposed cleanly")

    application = FastAPI(
        title="Agent Harness Chatbot API",
        version="2.0.0",
        description="Core AI Agent Harness with FastAPI, Gemini, Qdrant, Redis & PostgreSQL",
        lifespan=lifespan,
    )

    # Health & Readiness Check Endpoints
    @application.get("/health", response_model=HealthResponse, tags=["health"])
    def health_check():
        return HealthResponse(status="ok")

    @application.get("/ready", response_model=HealthResponse, tags=["health"])
    def readiness_check(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
            application.state.vectors.client.get_collections()
        except Exception as exc:
            logger.warning("Readiness check failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage or vector backend unavailable",
            )
        return HealthResponse(status="ready")

    @application.get("/auth/verify", tags=["auth"])
    def verify_auth(identity: str = Depends(get_current_user)):
        """Fast check to verify access token validity without side-effects."""
        return {"status": "authenticated", "owner": identity}

    # Register API Routers
    application.include_router(documents.router)
    application.include_router(conversations.router)
    application.include_router(chat.router)
    application.include_router(memories.router)

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
