import sqlite3
import os
import hashlib
import secrets
import json
import logging
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger("skyreader.database")
DB_PATH = os.path.join(os.path.dirname(__file__), "skyreader.db")
DEMO_EMAIL = "explorer@skyreader.ai"
DUMMY_PASSWORD_HASH = "0" * 32 + "$" + "0" * 64


class RegistrationRejected(ValueError):
    pass


def get_neon_url() -> Optional[str]:
    """Retrieves Neon / PostgreSQL database connection URL from environment."""
    url = (
        os.getenv("NEON_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
    )
    if url and url.strip():
        url = url.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return url
    return None


def is_neon_enabled() -> bool:
    """Returns True if a Neon / PostgreSQL connection string is configured and driver is available."""
    return bool(get_neon_url() and PSYCOPG2_AVAILABLE)


def get_db_type() -> str:
    """Returns 'neon-postgres' or 'sqlite' depending on configuration."""
    return "neon-postgres" if is_neon_enabled() else "sqlite"


def demo_enabled() -> bool:
    return os.getenv("SKYREADER_ENABLE_DEMO", "").strip() == "1"


class PostgresCursorWrapper:
    """Cursor wrapper for PostgreSQL that adapts SQLite syntax to PostgreSQL."""
    def __init__(self, raw_cursor):
        self._cur = raw_cursor
        self.lastrowid = None

    def execute(self, sql: str, params=()):
        clean = sql.strip()
        # Handle SQLite transaction and pragma statements
        if clean.upper() in ("BEGIN IMMEDIATE", "BEGIN"):
            return self
        if clean.upper().startswith("PRAGMA"):
            return self

        # Replace '?' parameter placeholders with '%s' for psycopg2
        pg_sql = sql.replace("?", "%s")
        self._cur.execute(pg_sql, params)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows] if rows else []

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()


class PostgresConnectionWrapper:
    """Connection wrapper for PostgreSQL to maintain interface parity with sqlite3.Connection."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=RealDictCursor))

    def execute(self, sql: str, params=()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._conn.rollback()
        else:
            self._conn.commit()


def get_db_connection():
    """Returns an active database connection (Neon PostgreSQL if configured, else SQLite)."""
    neon_url = get_neon_url()
    if neon_url and PSYCOPG2_AVAILABLE:
        try:
            raw = psycopg2.connect(neon_url)
            return PostgresConnectionWrapper(raw)
        except Exception as err:
            logger.warning("Failed to connect to Neon PostgreSQL (%s). Falling back to SQLite.", err)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000
    ).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain password against the stored salt$hash format."""
    try:
        salt, original_hash = stored_hash.split("$", 1)
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000
        ).hex()
        return secrets.compare_digest(computed_hash, original_hash)
    except Exception:
        return False


def init_db():
    """Initializes database tables for Neon PostgreSQL or SQLite."""
    conn = get_db_connection()
    is_pg = isinstance(conn, PostgresConnectionWrapper)

    try:
        cur = conn.cursor()
        if is_pg:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL,
                saved_cities TEXT DEFAULT '[]'
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS guest_sessions (
                id TEXT PRIMARY KEY,
                credential_hash TEXT UNIQUE NOT NULL,
                expires_at BIGINT NOT NULL
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_threads (
                id TEXT PRIMARY KEY,
                account_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                guest_id TEXT REFERENCES guest_sessions(id) ON DELETE CASCADE,
                schema_version INTEGER NOT NULL,
                revision INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                expires_at BIGINT NOT NULL,
                CHECK ((account_id IS NULL AND guest_id IS NOT NULL) OR (account_id IS NOT NULL AND guest_id IS NULL))
            );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_threads_account ON conversation_threads(account_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_threads_guest ON conversation_threads(guest_id);")

            if demo_enabled():
                cur.execute(
                    """
                    INSERT INTO users (email, name, hashed_password, created_at, saved_cities)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO NOTHING;
                    """,
                    (DEMO_EMAIL, "Atmospheric Explorer", hash_password("weather123"),
                     datetime.now(timezone.utc).isoformat(), json.dumps(["Tokyo", "Dehradun", "Paris"]))
                )
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL,
                saved_cities TEXT DEFAULT '[]'
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS guest_sessions (
                id TEXT PRIMARY KEY,
                credential_hash TEXT UNIQUE NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_threads (
                id TEXT PRIMARY KEY,
                account_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                guest_id TEXT REFERENCES guest_sessions(id) ON DELETE CASCADE,
                schema_version INTEGER NOT NULL,
                revision INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                CHECK ((account_id IS NULL AND guest_id IS NOT NULL) OR (account_id IS NOT NULL AND guest_id IS NULL))
            )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS conversation_threads_account ON conversation_threads(account_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS conversation_threads_guest ON conversation_threads(guest_id)")

            if demo_enabled():
                cur.execute(
                    """
                    INSERT INTO users (email, name, hashed_password, created_at, saved_cities)
                    SELECT ?, ?, ?, ?, ?
                    WHERE NOT EXISTS (SELECT 1 FROM users WHERE LOWER(email) = ?)
                    """,
                    (DEMO_EMAIL, "Atmospheric Explorer", hash_password("weather123"),
                     datetime.now(timezone.utc).isoformat(), json.dumps(["Tokyo", "Dehradun", "Paris"]), DEMO_EMAIL),
                )

        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, name, hashed_password, created_at, saved_cities FROM"
            " users WHERE LOWER(email) = LOWER(?)",
            (email.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "hashed_password": row["hashed_password"],
            "created_at": str(row["created_at"]),
            "saved_cities": json.loads(row["saved_cities"] or "[]"),
        }
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, name, created_at, saved_cities FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "created_at": str(row["created_at"]),
            "saved_cities": json.loads(row["saved_cities"] or "[]"),
        }
    finally:
        conn.close()


def _insert_user(conn, email: str, password: str, name: str) -> Dict[str, Any]:
    clean_email = email.strip().lower()
    if clean_email == DEMO_EMAIL:
        raise RegistrationRejected("Registration could not be completed.")

    display_name = name.strip() or clean_email.split("@")[0]
    now_str = datetime.now(timezone.utc).isoformat()
    is_pg = isinstance(conn, PostgresConnectionWrapper)

    if is_pg:
        cursor = conn.execute(
            """
            INSERT INTO users (email, name, hashed_password, created_at, saved_cities)
            VALUES (?, ?, ?, ?, '[]')
            ON CONFLICT (email) DO NOTHING
            RETURNING id
            """,
            (clean_email, display_name, hash_password(password), now_str),
        )
        row = cursor.fetchone()
        if not row:
            raise RegistrationRejected("Registration could not be completed.")
        user_id = row["id"]
    else:
        cursor = conn.execute(
            """
            INSERT INTO users (email, name, hashed_password, created_at, saved_cities)
            SELECT ?, ?, ?, ?, '[]'
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE LOWER(email) = ?)
            """,
            (clean_email, display_name, hash_password(password), now_str, clean_email),
        )
        if cursor.rowcount == 0:
            raise RegistrationRejected("Registration could not be completed.")
        user_id = cursor.lastrowid

    return {
        "id": user_id,
        "email": clean_email,
        "name": display_name,
        "created_at": now_str,
        "saved_cities": [],
    }


def create_user(email: str, password: str, name: str) -> Dict[str, Any]:
    with closing(get_db_connection()) as conn, conn:
        return _insert_user(conn, email, password, name)


def register_with_session(email: str, password: str, name: str):
    with closing(get_db_connection()) as conn, conn:
        user = _insert_user(conn, email, password, name)
        return user, _insert_session(conn, user["id"], 14)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    password_matches = verify_password(password, user["hashed_password"] if user else DUMMY_PASSWORD_HASH)
    if not user or not password_matches or (user["email"].lower() == DEMO_EMAIL and not demo_enabled()):
        return None
    user.pop("hashed_password")
    return user


def _insert_session(conn, user_id: int, duration_days: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=duration_days)
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now.isoformat(), expires.isoformat()),
    )
    return token


def create_session(user_id: int, duration_days: int = 14) -> str:
    with closing(get_db_connection()) as conn, conn:
        return _insert_session(conn, user_id, duration_days)


def get_user_by_session_token(token: str, *, connection=None) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    if connection is None:
        with closing(get_db_connection()) as conn:
            return get_user_by_session_token(token, connection=conn)

    row = connection.execute(
        """
        SELECT u.id, u.email, u.name, u.created_at, u.saved_cities, s.expires_at
        FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    if not row or (row["email"].lower() == DEMO_EMAIL and not demo_enabled()):
        return None

    try:
        expires = datetime.fromisoformat(str(row["expires_at"]))
        if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
            return None
    except (TypeError, ValueError, OverflowError):
        return None

    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "created_at": str(row["created_at"]),
        "saved_cities": json.loads(row["saved_cities"] or "[]"),
    }


def delete_session(token: str) -> bool:
    with closing(get_db_connection()) as conn, conn:
        cursor = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return cursor.rowcount > 0
