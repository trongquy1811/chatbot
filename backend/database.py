from collections.abc import Generator
from fastapi import Request
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from backend.config import Settings
from backend.models import Base


def get_engine(settings: Settings) -> Engine:
    """Create SQLAlchemy engine with appropriate dialect arguments."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    connect_args = (
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    )

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create session factory."""
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def init_db(engine: Engine) -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db(request: Request) -> Generator[Session, None, None]:
    """FastAPI dependency to acquire a database session."""
    session_factory = request.app.state.sessions
    with session_factory() as session:
        yield session
