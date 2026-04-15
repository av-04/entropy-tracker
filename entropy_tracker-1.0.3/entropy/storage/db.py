"""
Database connection and session management.

Provides:
- Async and sync engines for PostgreSQL + TimescaleDB
- Session factories
- Schema initialization (creates tables, sets up hypertable)
- Helper functions for common queries
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from entropy.storage.models import AlertRecord, Base, ModuleEntropy, Repo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

# Priority: DATABASE_URL env var → docker default → SQLite local
_DEFAULT_PG_URL = "postgresql://postgres:entropy@localhost:5432/entropy"
DATABASE_URL = os.environ.get("DATABASE_URL", _DEFAULT_PG_URL)

# SQLite fallback for local use without Docker
SQLITE_URL = "sqlite:///entropy.db"

_db_url_resolved: str | None = None  # cached after first probe


def get_database_url() -> str:
    """
    Return the best available DB URL.
    Probes PostgreSQL first; silently falls back to SQLite on any connection error.
    Result is cached so the probe only happens once per process.
    """
    global _db_url_resolved
    if _db_url_resolved is not None:
        return _db_url_resolved

    target = DATABASE_URL
    if not target.startswith("postgresql"):
        _db_url_resolved = SQLITE_URL
        return _db_url_resolved

    # Probe PostgreSQL with a quick connection attempt
    try:
        from sqlalchemy import create_engine, text as sql_text
        probe = create_engine(target, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        with probe.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
        probe.dispose()
        _db_url_resolved = target
        logger.info("Database: connected to PostgreSQL at %s", target.split("@")[-1])
    except Exception as e:
        logger.warning(
            "PostgreSQL unavailable (%s). Falling back to SQLite (entropy.db).", str(e)[:80]
        )
        _db_url_resolved = SQLITE_URL

    return _db_url_resolved


# ---------------------------------------------------------------------------
# Engine & Session
# ---------------------------------------------------------------------------

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_database_url()
        logger.info("Connecting to database: %s", url.split("@")[-1] if "@" in url else url)

        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        _engine = create_engine(
            url,
            pool_pre_ping=True,
            echo=False,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager that yields a database session and handles commit/rollback."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Schema initialization
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables and set up TimescaleDB hypertable if using PostgreSQL."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created")

    # Try to create hypertable (only works with TimescaleDB extension)
    url = get_database_url()
    if url.startswith("postgresql"):
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                conn.execute(
                    text(
                        "SELECT create_hypertable('module_entropy', 'time', "
                        "if_not_exists => TRUE, migrate_data => TRUE);"
                    )
                )
                conn.commit()
                logger.info("TimescaleDB hypertable configured for module_entropy")
        except Exception as e:
            logger.warning("TimescaleDB not available — using regular PostgreSQL table: %s", str(e))


def reset_engine() -> None:
    """Reset engine and session factory (for testing)."""
    global _engine, _session_factory
    if _engine:
        _engine.dispose()
    _engine = None
    _session_factory = None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def save_repo(session: Session, name: str, path: str, language: str = "python") -> Repo:
    """Create or update a tracked repository."""
    existing = session.query(Repo).filter_by(path=path).first()
    if existing:
        existing.name = name
        existing.language = language
        return existing
    repo = Repo(name=name, path=path, language=language)
    session.add(repo)
    session.flush()
    return repo


def save_module_scores(
    session: Session,
    repo_id: UUID,
    scores: dict,
    timestamp: datetime | None = None,
) -> list[ModuleEntropy]:
    """Write scored modules to the module_entropy table."""
    ts = timestamp or datetime.now(timezone.utc)
    records = []

    for path, score in scores.items():
        record = ModuleEntropy(
            time=ts,
            repo_id=repo_id,
            module_path=path,
            entropy_score=score.entropy_score,
            knowledge_score=score.knowledge_score,
            dep_score=score.dep_score,
            churn_score=score.churn_score,
            age_score=score.age_score,
            blast_radius=score.blast_radius,
            bus_factor=score.bus_factor,
            trend_per_month=score.trend_per_month,
            authors_active=score.authors_active,
            authors_total=score.authors_total,
            months_since_refactor=score.months_since_refactor,
            churn_commits=score.churn_commits,
            refactor_commits=score.refactor_commits,
        )
        session.add(record)
        records.append(record)

    return records


def save_alerts(session: Session, repo_id: UUID, alerts: list) -> list[AlertRecord]:
    """Write fired alerts to the alerts table."""
    records = []
    for alert in alerts:
        record = AlertRecord(
            repo_id=repo_id,
            module_path=alert.module_path,
            severity=alert.severity,
            message=alert.message,
            fired_at=alert.fired_at,
        )
        session.add(record)
        records.append(record)
    return records


def get_latest_scores(session: Session, repo_id: UUID) -> list[ModuleEntropy]:
    """Get the most recent entropy scores for each module in a repo."""
    # Subquery to find the max time per module
    from sqlalchemy import func

    subq = (
        session.query(
            ModuleEntropy.module_path,
            func.max(ModuleEntropy.time).label("max_time"),
        )
        .filter(ModuleEntropy.repo_id == repo_id)
        .group_by(ModuleEntropy.module_path)
        .subquery()
    )

    return (
        session.query(ModuleEntropy)
        .join(
            subq,
            (ModuleEntropy.module_path == subq.c.module_path)
            & (ModuleEntropy.time == subq.c.max_time),
        )
        .filter(ModuleEntropy.repo_id == repo_id)
        .order_by(ModuleEntropy.entropy_score.desc())
        .all()
    )


def get_module_history(
    session: Session,
    repo_id: UUID,
    module_path: str,
    limit: int = 365,
) -> list[ModuleEntropy]:
    """Get historical entropy scores for a single module."""
    return (
        session.query(ModuleEntropy)
        .filter(
            ModuleEntropy.repo_id == repo_id,
            ModuleEntropy.module_path == module_path,
        )
        .order_by(ModuleEntropy.time.desc())
        .limit(limit)
        .all()
    )
