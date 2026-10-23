"""Database engine + session. SQLite file by default (zero setup)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DATABASE_URL

# SQLite requires check_same_thread=False so the same engine can be used across
# different threads (FastAPI runs requests in a thread pool).
_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Single shared engine for the whole app.
engine = create_engine(DATABASE_URL, connect_args=_args)

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