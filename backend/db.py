from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# DB SQLite su file nella root del progetto (accanto a streamlit_app.py)
DB_PATH = Path(__file__).resolve().parents[1] / "studio_medico.sqlite"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,              # metti True se vuoi vedere le query
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base ORM per tutti i modelli."""
    pass


@contextmanager
def db_session() -> Iterator[Session]:
    """
    Context manager per gestire correttamente la sessione:
    - commit se tutto ok
    - rollback su eccezioni
    - close sempre
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
