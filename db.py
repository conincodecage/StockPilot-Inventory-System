"""Oracle connection helpers for Flask."""
from __future__ import annotations

import os
import oracledb
from flask import g


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when the Oracle connection environment is missing."""


def get_db():
    """Get one Oracle connection per Flask request."""
    if "oracle_db" not in g:
        user = os.getenv("ORACLE_USER")
        password = os.getenv("ORACLE_PASSWORD")
        dsn = os.getenv("ORACLE_DSN")
        if not all((user, password, dsn)):
            raise DatabaseNotConfiguredError(
                "Oracle settings are missing. Copy .env.example to .env and set ORACLE_USER, ORACLE_PASSWORD and ORACLE_DSN."
            )
        g.oracle_db = oracledb.connect(user=user, password=password, dsn=dsn)
    return g.oracle_db


def close_db(exception=None):
    db = g.pop("oracle_db", None)
    if db is not None:
        try:
            if exception is not None:
                db.rollback()
        finally:
            db.close()


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or {})
        names = [col[0].lower() for col in cursor.description] if cursor.description else []
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or {})
        row = cursor.fetchone()
        if row is None:
            return None
        names = [col[0].lower() for col in cursor.description]
        return dict(zip(names, row))
