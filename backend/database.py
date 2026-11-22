import sqlite3
import os
import hashlib
import secrets
import json
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "skyreader.db")
DEMO_EMAIL = "explorer@skyreader.ai"
DUMMY_PASSWORD_HASH = "0" * 32 + "$" + "0" * 64


class RegistrationRejected(ValueError):
  pass


def demo_enabled() -> bool:
  return os.getenv("SKYREADER_ENABLE_DEMO", "").strip() == "1"


def get_db_connection() -> sqlite3.Connection:
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
  """Initializes database tables if they do not exist."""
  conn = get_db_connection()
  cursor = conn.cursor()

  cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        hashed_password TEXT NOT NULL,
        created_at TEXT NOT NULL,
        saved_cities TEXT DEFAULT '[]'
    )
    """)

  cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

  cursor.execute("""
    CREATE TABLE IF NOT EXISTS guest_sessions (
      id TEXT PRIMARY KEY,
      credential_hash TEXT UNIQUE NOT NULL,
      expires_at INTEGER NOT NULL
    )
  """)
  cursor.execute("""
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
      CHECK ((account_id IS NULL) <> (guest_id IS NULL))
    )
  """)
  cursor.execute("CREATE INDEX IF NOT EXISTS conversation_threads_account ON conversation_threads(account_id)")
  cursor.execute("CREATE INDEX IF NOT EXISTS conversation_threads_guest ON conversation_threads(guest_id)")

  if demo_enabled():
    cursor.execute(
        """
        INSERT INTO users (email, name, hashed_password, created_at, saved_cities)
        SELECT ?, ?, ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE LOWER(email) = ?)
        """,
        (DEMO_EMAIL, "Atmospheric Explorer", hash_password("weather123"),
         datetime.now(timezone.utc).isoformat(), json.dumps(["Tokyo", "Dehradun", "Paris"]), DEMO_EMAIL),
    )

  conn.commit()
  conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, email, name, hashed_password, created_at, saved_cities FROM"
      " users WHERE LOWER(email) = LOWER(?)",
      (email.strip(),),
  )
  row = cursor.fetchone()
  conn.close()
  if not row:
    return None
  return {
      "id": row["id"],
      "email": row["email"],
      "name": row["name"],
      "hashed_password": row["hashed_password"],
      "created_at": row["created_at"],
      "saved_cities": json.loads(row["saved_cities"] or "[]"),
  }


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, email, name, created_at, saved_cities FROM users WHERE id ="
      " ?",
      (user_id,),
  )
  row = cursor.fetchone()
  conn.close()
  if not row:
    return None
  return {
      "id": row["id"],
      "email": row["email"],
      "name": row["name"],
      "created_at": row["created_at"],
      "saved_cities": json.loads(row["saved_cities"] or "[]"),
  }


def _insert_user(conn, email: str, password: str, name: str) -> Dict[str, Any]:
  clean_email = email.strip().lower()
  if clean_email == DEMO_EMAIL:
    raise RegistrationRejected("Registration could not be completed.")

  display_name = name.strip() or clean_email.split("@")[0]
  now_str = datetime.now(timezone.utc).isoformat()
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
  return {
      "id": cursor.lastrowid, "email": clean_email, "name": display_name,
      "created_at": now_str, "saved_cities": [],
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
    expires = datetime.fromisoformat(row["expires_at"])
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
      return None
  except (TypeError, ValueError, OverflowError):
    return None

  return {
      "id": row["id"],
      "email": row["email"],
      "name": row["name"],
      "created_at": row["created_at"],
      "saved_cities": json.loads(row["saved_cities"] or "[]"),
  }


def delete_session(token: str) -> bool:
  with closing(get_db_connection()) as conn, conn:
    cursor = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    return cursor.rowcount > 0
