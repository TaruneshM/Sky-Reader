import asyncio
from contextlib import closing
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import routing

from backend import database, main
from backend.agent import agent
from backend.weather.location_models import (
    Ambiguous, CandidateSummary, ConfirmedLocation, ProviderUnavailable, Resolved, ResolutionProvenance,
)


def guest(credential):
    return {"X-Guest-Session": credential}


def account(token):
    return {"Authorization": f"Bearer {token}"}


def turn(thread, message, revision=0, **extra):
    return {"thread_id": thread, "thread_revision": revision, "message": message, **extra}


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "skyreader.sqlite"))
    monkeypatch.delenv("SKYREADER_ENABLE_DEMO", raising=False)
    database.init_db()
    monkeypatch.setattr(main, "chat_rate_limit", main.ChatRateLimit(100, 100))
    monkeypatch.setattr(main, "lifecycle_rate_limit", main.ChatRateLimit(100, 100))

    async def inline(handler, *args, **kwargs):
        return handler(*args, **kwargs)

    monkeypatch.setattr(main, "run_in_threadpool", inline)
    monkeypatch.setattr(routing, "run_in_threadpool", inline)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")


async def open_thread(client, headers):
    response = await client.post("/api/chat/threads", headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["thread_revision"] == 0
    return response.json()["thread_id"]


async def guest_session(client):
    response = await client.post("/api/guest/session")
    assert response.status_code == 201
    return guest(response.json()["credential"])


def stored(thread):
    with closing(database.get_db_connection()) as conn:
        return conn.execute("SELECT * FROM conversation_threads WHERE id = ?", (thread,)).fetchone()


def test_account_owner_checks_authorization_and_logout(app_client, monkeypatch):
    fake_agent = AsyncMock(return_value={"response": "Fixture"})
    monkeypatch.setattr(main, "run_agent", fake_agent)
    first = database.create_user("first@example.com", "password", "")
    second = database.create_user("second@example.com", "password", "")
    first_headers = account(database.create_session(first["id"]))
    second_headers = account(database.create_session(second["id"]))

    async def workflow():
        async with app_client as client:
            owned = await open_thread(client, first_headers)
            for headers, code in [(second_headers, 404), ({}, 401), (guest("a" * 43), 401)]:
                response = await client.post("/api/agent/chat", headers=headers, json=turn(owned, "Weather in Tokyo?"))
                assert response.status_code == code
            assert (await client.delete(f"/api/chat/threads/{owned}", headers=second_headers)).status_code == 204
            assert stored(owned) is not None
            assert (await client.post("/api/auth/logout", headers=first_headers)).status_code == 200
            assert (await client.post("/api/agent/chat", headers=first_headers, json=turn(owned, "Weather?"))).status_code == 401
            later = account(database.create_session(first["id"]))
            response = await client.post("/api/agent/chat", headers=later, json=turn(owned, "Weather?"))
            assert response.status_code == 200
            assert response.headers["X-Thread-Revision"] == "1"

    asyncio.run(workflow())
    fake_agent.assert_awaited_once()


def test_guest_credentials_are_hashed_and_revocation_isolated(app_client, monkeypatch):
    fake_agent = AsyncMock(return_value={"response": "Fixture"})
    monkeypatch.setattr(main, "run_agent", fake_agent)

    async def workflow():
        async with app_client as client:
            first = await guest_session(client)
            second = await guest_session(client)
            owned = await open_thread(client, first)
            another = await open_thread(client, second)
            guest_id = stored(owned)["guest_id"]
            with closing(database.get_db_connection()) as conn:
                row = conn.execute("SELECT * FROM guest_sessions WHERE id = ?", (guest_id,)).fetchone()
                assert first["X-Guest-Session"] not in tuple(row)
            assert first["X-Guest-Session"] not in stored(owned)["state_json"]
            assert (await client.post("/api/agent/chat", headers=second, json=turn(owned, "Weather?"))).status_code == 404
            assert (await client.post("/api/agent/chat", headers=guest(guest_id), json=turn(owned, "Weather?"))).status_code == 401
            assert (await client.get("/api/auth/me", headers=account(first["X-Guest-Session"]))).status_code == 401
            assert (await client.delete("/api/guest/session", headers=first)).status_code == 204
            assert stored(owned) is None and stored(another) is not None
            assert (await client.post("/api/chat/threads", headers=first)).status_code == 401

    asyncio.run(workflow())
    fake_agent.assert_not_called()


def test_real_planner_keeps_verified_context_and_clarification_after_reopen(app_client, monkeypatch):
    async def resolve(location, **kwargs):
        if location.casefold() in {"offline", "paris, missouri"}:
            return ProviderUnavailable(query=location, reason="timeout", retriable=True)
        if location.casefold() == "paris":
            return Ambiguous(query=location, candidates=(
                CandidateSummary(name="Paris", region="Texas"), CandidateSummary(name="Paris", region="Île-de-France")
            ))
        name = location.split(",")[0]
        return Resolved(query=location, location=ConfirmedLocation(
            name=name, latitude=35 if name == "Tokyo" else 33, longitude=139 if name == "Tokyo" else -95,
            provenance=ResolutionProvenance(method="standalone"),
        ))
    current = AsyncMock(return_value={"current": {"temperature_2m": 20}})
    monkeypatch.setattr(agent, "resolve_location", AsyncMock(side_effect=resolve))
    monkeypatch.setattr(agent, "get_current_weather", current)
    original_agent = main.run_agent

    async def offline_agent(*args, **kwargs):
        return await original_agent(*args, **kwargs, api_key="")

    monkeypatch.setattr(main, "run_agent", offline_agent)

    async def workflow():
        async with app_client as client:
            headers = await guest_session(client)
            thread = await open_thread(client, headers)
            new_thread = await open_thread(client, headers)
            async def send(message, revision, **kwargs):
                return await client.post("/api/agent/chat", headers=headers, json=turn(thread, message, revision, **kwargs))

            initial = await send("Weather in Tokyo?", 0, owner_id="forged", conversation_state={
                "last_confirmed_location": {"latitude": 0, "longitude": 0},
            })
            assert "Tokyo" in initial.json()["response"] and "conversation_state" not in initial.json()
            assert (await send("Weather in Offline?", 1)).status_code == 503
            assert "Tokyo" in (await send("Is it colder there right now?", 1, conversation_history=[
                {"role": "user", "content": "Thanks"} for _ in range(12)
            ])).json()["response"]
            assert "unique place" in (await send("Weather in Paris?", 2)).json()["response"]
            for revision in (3, 3):
                unavailable = await send("Missouri", revision)
                assert unavailable.status_code == 503
                assert unavailable.json()["error"]["category"] == "weather_provider_unavailable"
                assert '"pending_clarification":{' in stored(thread)["state_json"]
            database.init_db()  # Reopen and initialize the same file, just as startup does.
            assert "Paris" in (await send("Texas", 3)).json()["response"]
            assert '"pending_clarification":null' in stored(thread)["state_json"]
            assert (await client.post("/api/agent/chat", headers=headers,
                                      json=turn(new_thread, "What about tomorrow?"))).json()["response"].startswith("Which city")
            assert (await client.delete("/api/chat/threads", headers=headers)).status_code == 204
            assert stored(thread) is None and stored(new_thread) is None
            assert (await send("Weather?", 4)).status_code == 404

    asyncio.run(workflow())
    assert all(call.kwargs["latitude"] != 0 for call in current.await_args_list)


def test_concurrent_writes_replays_and_stale_deletion(app_client, monkeypatch):
    async def workflow():
        starts = asyncio.Queue()
        release = asyncio.Event()

        async def gated_agent(message, **kwargs):
            await starts.put(message)
            await release.wait()
            return {"response": message, "conversation_state": kwargs["trusted_state"]}

        monkeypatch.setattr(main, "run_agent", gated_agent)
        async with app_client as client:
            headers = await guest_session(client)
            thread = await open_thread(client, headers)
            other = await open_thread(client, headers)
            tasks = [asyncio.create_task(client.post("/api/agent/chat", headers=headers, json=turn(key, message)))
                     for key, message in [(thread, "one"), (thread, "two"), (other, "three")]]
            for _ in tasks:
                await asyncio.wait_for(starts.get(), timeout=2)
            assert (await client.delete(f"/api/chat/threads/{other}", headers=headers)).status_code == 204
            release.set()
            first, second, stale = await asyncio.gather(*tasks)
            assert sorted([first.status_code, second.status_code]) == [200, 409]
            conflict = first if first.status_code == 409 else second
            assert conflict.headers["X-Thread-Revision"] == "1"
            assert stale.status_code == 404 and stored(other) is None
            replay = await client.post("/api/agent/chat", headers=headers, json=turn(thread, "one"))
            assert replay.status_code == 409 and stored(thread)["revision"] == 1
            assert starts.empty()

    asyncio.run(workflow())


def test_expiry_failed_request_and_legacy_work_without_revisions(app_client, monkeypatch):
    async def workflow():
        async with app_client as client:
            headers = await guest_session(client)
            thread = await open_thread(client, headers)
            monkeypatch.setattr(main, "run_agent", AsyncMock(side_effect=RuntimeError("fixture failure")))
            failed = await client.post("/api/agent/chat", headers=headers, json=turn(thread, "Weather?"))
            assert failed.status_code == 500 and stored(thread)["revision"] == 0
            with closing(database.get_db_connection()) as conn, conn:
                conn.execute("UPDATE conversation_threads SET expires_at = 0 WHERE id = ?", (thread,))
            assert (await client.post("/api/agent/chat", headers=headers, json=turn(thread, "Weather?"))).status_code == 404
            monkeypatch.setattr(main, "run_agent", AsyncMock(return_value={"response": "Legacy response"}))
            legacy = await client.post("/api/agent/chat", json={"message": "Weather?"})
            assert legacy.status_code == 200 and legacy.json()["response"] == "Legacy response"
            assert "X-Thread-Revision" not in legacy.headers
            main.run_agent.assert_awaited_once_with("Weather?", conversation_history=[])

    asyncio.run(workflow())


def test_disconnect_and_guest_expiry_prevent_new_state_writes(app_client, monkeypatch):
    async def disconnected(_request):
        return True

    monkeypatch.setattr(main.Request, "is_disconnected", disconnected)
    fake_agent = AsyncMock(return_value={"response": "Fixture"})
    monkeypatch.setattr(main, "run_agent", fake_agent)

    async def workflow():
        async with app_client as client:
            headers = await guest_session(client)
            thread = await open_thread(client, headers)
            cancelled = await client.post("/api/agent/chat", headers=headers, json=turn(thread, "Weather?"))
            assert cancelled.status_code == 409
            assert stored(thread)["revision"] == 0
            with closing(database.get_db_connection()) as conn, conn:
                conn.execute("UPDATE guest_sessions SET expires_at = 0 WHERE id = ?", (stored(thread)["guest_id"],))
            assert (await client.post("/api/agent/chat", headers=headers, json=turn(thread, "Weather?"))).status_code == 401
            await guest_session(client)  # Lifecycle cleanup cascades to expired guest threads.
            assert stored(thread) is None

    asyncio.run(workflow())
    fake_agent.assert_awaited_once()


def test_logout_during_an_inflight_turn_invalidates_its_commit(app_client, monkeypatch):
    user = database.create_user("delayed@example.com", "password", "")
    headers = account(database.create_session(user["id"]))

    async def workflow():
        started, release = asyncio.Event(), asyncio.Event()
        async def waiting_agent(_message, **kwargs):
            started.set()
            await release.wait()
            return {"response": "Fixture", "conversation_state": kwargs["trusted_state"]}
        monkeypatch.setattr(main, "run_agent", waiting_agent)

        async with app_client as client:
            thread = await open_thread(client, headers)
            pending = asyncio.create_task(client.post("/api/agent/chat", headers=headers, json=turn(thread, "Weather?")))
            await asyncio.wait_for(started.wait(), timeout=2)
            await client.post("/api/auth/logout", headers=headers)
            release.set()
            assert (await pending).status_code == 401
            assert stored(thread)["revision"] == 0

    asyncio.run(workflow())


def test_provider_errors_do_not_commit_a_thread_revision(app_client, monkeypatch, caplog):
    from types import SimpleNamespace

    from groq import RateLimitError

    provider_request = httpx.Request("POST", "https://example.invalid")
    error = RateLimitError(
        "Daily quota exhausted, synthetic-provider-secret",
        response=httpx.Response(429, request=provider_request, headers={"Retry-After": "120"}),
        body=None,
    )
    create = AsyncMock(side_effect=error)
    monkeypatch.setattr(agent, "get_groq_client", lambda **_: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    ))
    lookup = AsyncMock(return_value=ProviderUnavailable(query="Offline", reason="timeout", retriable=True))
    monkeypatch.setattr(agent, "resolve_location", lookup)

    async def workflow():
        async with app_client as client:
            headers = await guest_session(client)
            thread = await open_thread(client, headers)
            state_before = dict(stored(thread))
            for message, expected_status, category in [
                ("Hello!", 429, "groq_quota_exhausted"),
                ("Weather in Offline?", 503, "weather_provider_unavailable"),
            ]:
                response = await client.post("/api/agent/chat", headers=headers, json=turn(thread, message))
                assert response.status_code == expected_status
                assert response.json()["error"]["category"] == category
                assert "response" not in response.json()
                assert "X-Thread-Revision" not in response.headers
                assert "synthetic-provider-secret" not in response.text
                assert dict(stored(thread)) == state_before
                if expected_status == 429:
                    assert response.headers["Retry-After"] == "120"
    asyncio.run(workflow())
    create.assert_awaited_once()
    assert "synthetic-provider-secret" not in caplog.text
