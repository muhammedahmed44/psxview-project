from sqlalchemy import create_engine, inspect, text

import db


def test_existing_users_table_gets_totp_columns(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(254) NOT NULL,
                name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(100) NOT NULL
            )
        """))

    monkeypatch.setattr(db, "engine", engine)
    db._upgrade_users_for_totp()
    db._upgrade_users_for_totp()  # idempotent on repeated deploy/startup

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert {
        "totp_secret",
        "totp_enabled",
        "totp_last_counter",
        "recovery_codes_hashes",
    }.issubset(columns)
