"""SQLite storage for server-verified planner state. No chat transcript or bearer token is stored here."""

from contextlib import closing, contextmanager
from dataclasses import dataclass
import hashlib
import secrets
import time

from pydantic import ValidationError

if __package__ == "backend":
    from .database import get_db_connection, get_user_by_session_token
    from .agent.conversation_state import ConversationScope, ConversationWeatherContext
else:
    from database import get_db_connection, get_user_by_session_token
    from agent.conversation_state import ConversationScope, ConversationWeatherContext


GUEST_LIFETIME = 7 * 24 * 60 * 60
THREAD_LIFETIME = 30 * 24 * 60 * 60
SCHEMA_VERSION = 1


class InvalidOwner(Exception):
    pass


class ThreadNotFound(Exception):
    pass


class ThreadConflict(Exception):
    def __init__(self, revision: int):
        self.revision = revision


class IncompatibleState(Exception):
    pass


@dataclass(frozen=True, repr=False)
class Credentials:
    bearer: str | None = None
    guest: str | None = None


@contextmanager
def _write():
    with closing(get_db_connection()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        yield conn


def _digest(credential: str) -> str:
    return hashlib.sha256(credential.encode()).hexdigest()


def _owner(conn, credentials: Credentials, now: int):
    if credentials.bearer is not None:
        user = get_user_by_session_token(credentials.bearer, connection=conn)
        if user:
            return ("account", user["id"])
    elif credentials.guest:
        guest = conn.execute(
            "SELECT id FROM guest_sessions WHERE credential_hash = ? AND expires_at > ?",
            (_digest(credentials.guest), now),
        ).fetchone()
        if guest:
            return ("guest", guest["id"])
    raise InvalidOwner


def _owner_column(owner):
    return "account_id" if owner[0] == "account" else "guest_id"


def _scope(owner, thread_id):
    return ConversationScope(owner_kind=owner[0], owner_id=str(owner[1]), thread_id=thread_id)


def _cleanup(conn, now):
    conn.execute("DELETE FROM guest_sessions WHERE expires_at <= ?", (now,))
    conn.execute("DELETE FROM conversation_threads WHERE expires_at <= ?", (now,))


def create_guest() -> str:
    credential = secrets.token_urlsafe(32)
    with _write() as conn:
        now = int(time.time())
        _cleanup(conn, now)
        conn.execute("INSERT INTO guest_sessions VALUES (?, ?, ?)",
                     (secrets.token_urlsafe(24), _digest(credential), now + GUEST_LIFETIME))
    return credential


def revoke_guest(credentials: Credentials):
    with _write() as conn:
        if credentials.guest:
            conn.execute("DELETE FROM guest_sessions WHERE credential_hash = ?", (_digest(credentials.guest),))


def create_thread(credentials: Credentials) -> str:
    thread_id = secrets.token_urlsafe(24)
    with _write() as conn:
        now = int(time.time())
        owner = _owner(conn, credentials, now)
        _cleanup(conn, now)
        state = ConversationWeatherContext(scope=_scope(owner, thread_id))
        conn.execute(
            f"""INSERT INTO conversation_threads
                (id, {_owner_column(owner)}, schema_version, revision, state_json, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, 0, ?, ?, ?, ?)""",
            (thread_id, owner[1], SCHEMA_VERSION, state.model_dump_json(), now, now, now + THREAD_LIFETIME),
        )
    return thread_id


def _thread(conn, owner, thread_id, now):
    row = conn.execute(
        f"""SELECT schema_version, revision, state_json FROM conversation_threads
            WHERE id = ? AND {_owner_column(owner)} = ? AND expires_at > ?""",
        (thread_id, owner[1], now),
    ).fetchone()
    if not row:
        raise ThreadNotFound
    return row


def load_thread(credentials: Credentials, thread_id: str, revision: int) -> ConversationWeatherContext:
    with closing(get_db_connection()) as conn, conn:
        conn.execute("BEGIN")
        now = int(time.time())
        owner = _owner(conn, credentials, now)
        row = _thread(conn, owner, thread_id, now)
    if row["revision"] != revision:
        raise ThreadConflict(row["revision"])
    if row["schema_version"] != SCHEMA_VERSION:
        raise IncompatibleState
    try:
        state = ConversationWeatherContext.model_validate_json(row["state_json"])
    except ValidationError as error:
        raise IncompatibleState from error
    if state.scope != _scope(owner, thread_id):
        raise ThreadNotFound
    return state


def save_thread(credentials: Credentials, thread_id: str, revision: int, state: ConversationWeatherContext) -> int:
    with _write() as conn:
        now = int(time.time())
        owner = _owner(conn, credentials, now)
        row = _thread(conn, owner, thread_id, now)
        if state.scope != _scope(owner, thread_id):
            raise ThreadNotFound
        if row["revision"] != revision:
            raise ThreadConflict(row["revision"])
        if row["schema_version"] != state.schema_version:
            raise IncompatibleState
        conn.execute(
            """UPDATE conversation_threads SET state_json = ?, revision = revision + 1,
                updated_at = ?, expires_at = ? WHERE id = ?""",
            (state.model_dump_json(), now, now + THREAD_LIFETIME, thread_id),
        )
    return revision + 1


def clear_threads(credentials: Credentials, thread_id: str | None = None):
    with _write() as conn:
        now = int(time.time())
        owner = _owner(conn, credentials, now)
        column = _owner_column(owner)
        if thread_id is None:
            conn.execute(f"DELETE FROM conversation_threads WHERE {column} = ?", (owner[1],))
        else:
            conn.execute(f"DELETE FROM conversation_threads WHERE {column} = ? AND id = ?", (owner[1], thread_id))
