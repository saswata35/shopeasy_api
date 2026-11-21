from contextlib import contextmanager
from typing import Optional
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from shopeasy_api.config import Config

UniqueViolation = pg_errors.UniqueViolation
ForeignKeyViolation = pg_errors.ForeignKeyViolation

_pool: Optional[SimpleConnectionPool] = None


def get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(
            minconn=Config.DB_MIN_CONN,
            maxconn=Config.DB_MAX_CONN,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
        )
    return _pool


def get_connection():
    return get_pool().getconn()


def release_connection(conn) -> None:
    if conn is not None and _pool is not None:
        _pool.putconn(conn)


@contextmanager
def get_cursor(autocommit: bool = False):
    conn = get_connection()
    conn.autocommit = autocommit
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        cur.close()
        release_connection(conn)


@contextmanager
def transaction():
    conn = get_connection()
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_connection(conn)