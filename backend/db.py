"""Database engine + session. SQLite file by default (zero setup)."""
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DATABASE_URL

# SQLite requires check_same_thread=False so the same engine can be used across
# different threads (FastAPI runs requests in a thread pool).
_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Single shared engine for the whole app. Pre-ping replaces stale cloud
# connections automatically after a database restart or idle period.
engine = create_engine(DATABASE_URL, connect_args=_args, pool_pre_ping=True)
log = logging.getLogger("psxviewai.db")

# Factory that creates new DB sessions bound to the engine.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Models subclass this and define tables using __tablename__ and Column fields.
    """
    pass


def get_db():
    """
    FastAPI dependency: one DB session per request, always closed.

    Yields a session to the route, then closes it in a finally block
    so connections are not leaked on success or failure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables defined by models that inherit from Base.

    Importing `models` registers the model classes with Base.metadata.
    """
    import models  # noqa: F401  (import registers the tables on Base)
    Base.metadata.create_all(bind=engine)
    _upgrade_users_for_totp()


def _upgrade_users_for_totp() -> None:
    """Add TOTP columns to an existing SQLite/PostgreSQL deployment.

    ``create_all`` creates new tables but deliberately does not alter existing
    ones. The project does not use Alembic yet, so this small idempotent upgrade
    keeps current Render users intact while enabling authenticator enrollment.
    """
    existing = {column["name"] for column in inspect(engine).get_columns("users")}
    definitions = {
        "totp_secret": "VARCHAR(512)",
        "totp_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
        "totp_last_counter": "BIGINT",
        "recovery_codes_hashes": "TEXT",
    }
    missing = [(name, ddl) for name, ddl in definitions.items() if name not in existing]
    if not missing:
        return

    table = engine.dialect.identifier_preparer.quote("users")
    with engine.begin() as connection:
        for name, ddl in missing:
            column = engine.dialect.identifier_preparer.quote(name)
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            log.info("Added users.%s for authenticator-based 2FA", name)
