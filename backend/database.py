import sqlite3
import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "skyreader.db")


def get_db_connection() -> sqlite3.Connection:
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
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

  # Seed a default demo user if table is empty
  cursor.execute("SELECT COUNT(*) FROM users")
  if cursor.fetchone()[0] == 0:
    demo_email = "explorer@skyreader.ai"
    demo_pwd_hash = hash_password("weather123")
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO users (email, name, hashed_password, created_at, saved_cities)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            demo_email,
            "Atmospheric Explorer",
            demo_pwd_hash,
            now_str,
            json.dumps(["Tokyo", "Dehradun", "Paris"]),
        ),
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


def create_user(email: str, password: str, name: str) -> Dict[str, Any]:
  clean_email = email.strip().lower()
  if get_user_by_email(clean_email):
    raise ValueError("A user with this email address already exists.")

  display_name = name.strip() if name.strip() else clean_email.split("@")[0]
  pwd_hash = hash_password(password)
  now_str = datetime.now(timezone.utc).isoformat()

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO users (email, name, hashed_password, created_at, saved_cities)
        VALUES (?, ?, ?, ?, ?)
    """,
      (clean_email, display_name, pwd_hash, now_str, json.dumps([])),
  )
  user_id = cursor.lastrowid
  conn.commit()
  conn.close()

  return {
      "id": user_id,
      "email": clean_email,
      "name": display_name,
      "created_at": now_str,
      "saved_cities": [],
  }


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
  user = get_user_by_email(email)
  if not user:
    return None
  if not verify_password(password, user["hashed_password"]):
    return None

  return {
      "id": user["id"],
      "email": user["email"],
      "name": user["name"],
      "created_at": user["created_at"],
      "saved_cities": user["saved_cities"],
  }


def create_session(user_id: int, duration_days: int = 14) -> str:
  token = secrets.token_urlsafe(32)
  now = datetime.now(timezone.utc)
  expires = now + timedelta(days=duration_days)

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    """,
      (token, user_id, now.isoformat(), expires.isoformat()),
  )
  conn.commit()
  conn.close()

  return token


def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
  if not token:
    return None
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT u.id, u.email, u.name, u.created_at, u.saved_cities, s.expires_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
    """,
      (token.strip(),),
  )
  row = cursor.fetchone()
  conn.close()

  if not row:
    return None

  # Check expiration
  try:
    expires = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires:
      delete_session(token)
      return None
  except Exception:
    pass

  return {
      "id": row["id"],
      "email": row["email"],
      "name": row["name"],
      "created_at": row["created_at"],
      "saved_cities": json.loads(row["saved_cities"] or "[]"),
  }


def delete_session(token: str) -> bool:
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM sessions WHERE token = ?", (token.strip(),))
  conn.commit()
  conn.close()
  return True
