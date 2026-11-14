from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from patchwise.core.config import load_config


class Base(DeclarativeBase):
    pass


def resolve_db_path(db_path: str | None = None) -> str:
    if db_path is not None:
        resolved = Path(db_path).expanduser().resolve()
    else:
        resolved = Path(load_config().db_path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return str(resolved)


def get_engine(db_path: str | None = None):
    return create_engine(f"sqlite:///{resolve_db_path(db_path)}", future=True)


def get_session_factory(db_path: str | None = None):
    engine = get_engine(db_path)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(db_path: str | None = None) -> None:
    from patchwise.core.models import ActivityLog, Finding, FindingEvidence, Project, RemediationRecord, ScanRecord

    Base.metadata.create_all(bind=get_engine(db_path))
