from config import normalize_database_url


def test_normalizes_render_postgresql_url_for_psycopg():
    assert (
        normalize_database_url("postgresql://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )


def test_normalizes_legacy_postgres_url_for_psycopg():
    assert (
        normalize_database_url("postgres://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )


def test_preserves_sqlite_and_explicit_driver_urls():
    assert normalize_database_url("sqlite:///./app.db") == "sqlite:///./app.db"
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
