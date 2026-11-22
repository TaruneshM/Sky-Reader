import asyncio
import importlib
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from threading import Barrier
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import routing

from backend import main

database = importlib.import_module(main.create_session.__module__)
PASSWORD = "fixture-only-password"


@pytest.fixture
def temporary_database(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "accounts.sqlite"))
    monkeypatch.delenv("SKYREADER_ENABLE_DEMO", raising=False)
    database.init_db()


@pytest.fixture
def client(monkeypatch, temporary_database):
    # Run synchronous route handlers inline for in-process ASGI calls.
    # Concurrent database writes are exercised separately with real threads.
    async def run_inline(handler, *args, **kwargs):
        return handler(*args, **kwargs)

    monkeypatch.setattr(routing, "run_in_threadpool", run_inline)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


async def register(client, email="reader@example.com"):
    return await client.post("/api/auth/register", json={"email": email, "password": PASSWORD})


def test_register_login_refresh_logout_and_revocation(client):
    async def workflow():
        async with client:
            registration = await register(client)
            assert registration.status_code == 200
            assert registration.headers["cache-control"] == "no-store"
            account = registration.json()
            token = account["token"]
            refreshed = await client.get("/api/auth/me", headers=bearer(token))
            assert refreshed.json() == account["user"]
            assert refreshed.headers["cache-control"] == "no-store"
            assert (await client.post("/api/auth/logout", headers=bearer(token))).status_code == 200
            assert (await client.get("/api/auth/me", headers=bearer(token))).status_code == 401
            assert (await client.post("/api/auth/logout", headers=bearer(token))).status_code == 200

            bad_login = await client.post("/api/auth/login", json={
                "email": "reader@example.com", "password": "wrong-password",
            })
            missing_login = await client.post("/api/auth/login", json={
                "email": "unknown@example.com", "password": "wrong-password",
            })
            assert bad_login.status_code == missing_login.status_code == 401
            assert bad_login.json() == missing_login.json()
            login = await client.post("/api/auth/login", json={"email": "reader@example.com", "password": PASSWORD})
            assert login.json()["token"] != token
            assert (await client.get("/api/auth/me", headers=bearer(login.json()["token"]))).status_code == 200

    asyncio.run(workflow())


@pytest.mark.parametrize("expiry", [
    "invalid",
    "2099-01-01T00:00:00",
    (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
])
def test_sessions_reject_malformed_naive_and_expired_dates(client, expiry):
    async def workflow():
        async with client:
            token = (await register(client)).json()["token"]
            with closing(database.get_db_connection()) as conn, conn:
                conn.execute("UPDATE sessions SET expires_at = ? WHERE token = ?", (expiry, token))
            assert (await client.get("/api/auth/me", headers=bearer(token))).status_code == 401
            assert (await client.get("/api/auth/me", headers=bearer(token + " trailing"))).status_code == 401
            assert (await client.get("/api/auth/me")).status_code == 401

    asyncio.run(workflow())


def test_duplicate_registration_is_atomic_and_uses_generic_feedback(client):
    async def workflow():
        async with client:
            first = await register(client, "Same@example.com")
            second = await register(client, "SAME@example.com")
            assert sorted((first.status_code, second.status_code)) == [200, 400]
            rejected = first if first.status_code == 400 else second
            assert rejected.json() == {"detail": "Registration could not be completed."}

    asyncio.run(workflow())
    with closing(database.get_db_connection()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


def test_concurrent_registration_creates_only_one_account_and_session(temporary_database):
    start = Barrier(2)

    def attempt(email):
        start.wait(timeout=5)
        try:
            return database.register_with_session(email, PASSWORD, "")
        except database.RegistrationRejected:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["Same@example.com", "SAME@example.com"]))

    assert sum(result is not None for result in results) == 1
    with closing(database.get_db_connection()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


def test_registration_rolls_back_when_session_creation_fails(client, monkeypatch):
    def fail_session(*_args):
        raise RuntimeError("private internal detail")

    monkeypatch.setattr(database, "_insert_session", fail_session)

    async def workflow():
        async with client:
            response = await register(client)
            assert response.status_code == 500
            assert response.json() == {"detail": "Registration could not be completed."}

    asyncio.run(workflow())
    assert database.get_user_by_email("reader@example.com") is None


def test_registration_validation_does_not_echo_password(client):
    async def workflow():
        async with client:
            response = await client.post("/api/auth/register", json={
                "email": "reader@example.com", "password": "weak",
            })
            assert response.status_code == 422
            assert response.json()["detail"] == "Check your information and try again."

    asyncio.run(workflow())


def test_demo_requires_explicit_opt_in_and_preserves_existing_row(client, monkeypatch):
    assert database.get_user_by_email(database.DEMO_EMAIL) is None
    monkeypatch.setenv("SKYREADER_ENABLE_DEMO", "1")
    database.init_db()
    assert database.authenticate_user(database.DEMO_EMAIL, "weather123")
    user = database.get_user_by_email(database.DEMO_EMAIL)
    token = database.create_session(user["id"])
    assert database.get_user_by_session_token(token)
    monkeypatch.delenv("SKYREADER_ENABLE_DEMO")
    assert database.authenticate_user(database.DEMO_EMAIL, "weather123") is None
    assert database.get_user_by_session_token(token) is None
    assert database.get_user_by_email(database.DEMO_EMAIL)["id"] == user["id"]
    asyncio.run(client.aclose())


def test_public_chat_aliases_share_rate_limit_before_agent_execution(client, monkeypatch):
    limiter = main.ChatRateLimit(per_client=1, total=2)
    monkeypatch.setattr(main, "chat_rate_limit", limiter)
    agent = AsyncMock(return_value={"response": "Fixture reply"})
    monkeypatch.setattr(main, "run_agent", agent)

    async def ask(transport, path):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as caller:
            return await caller.post(path, json={"message": "Weather in Tokyo"})

    async def workflow():
        async with client:
            allowed = await client.post("/api/agent/chat", json={"message": "Weather in Tokyo"})
            assert allowed.status_code == 200
            blocked = await client.post("/agent/chat", json={"message": "Weather in Tokyo"})
            assert blocked.status_code == 429
            assert blocked.headers["retry-after"] == "60"
        assert (await ask(httpx.ASGITransport(app=main.app, client=("198.51.100.1", 0)), "/api/agent/chat")).status_code == 200
        assert (await ask(httpx.ASGITransport(app=main.app, client=("198.51.100.2", 0)), "/api/agent/chat")).status_code == 429
        assert agent.await_count == 2

    asyncio.run(workflow())


def test_chat_limit_releases_capacity_after_window(monkeypatch):
    from types import SimpleNamespace

    now = 0
    monkeypatch.setattr(main, "time", SimpleNamespace(monotonic=lambda: now))
    limiter = main.ChatRateLimit(per_client=1, total=1)
    limiter.check("first")
    now = 59
    with pytest.raises(main.HTTPException) as raised:
        limiter.check("second")
    assert raised.value.status_code == 429
    now = 60
    limiter.check("second")
    assert "first" not in limiter.counts
