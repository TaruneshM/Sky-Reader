import assert from "node:assert/strict";
import { test } from "node:test";
import { createAuthSession } from "../src/utils/authSession.js";
import { createConversations } from "../src/utils/conversations.js";

const KEY = "skyreader_token";
const TOKEN = "A".repeat(43);
const USER = { id: 7, name: "Weather Reader", email: "reader@example.com" };

function memoryStorage(entries = {}) {
  const data = new Map(Object.entries(entries));
  return {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
  };
}

function controlledRequest() {
  const calls = [];
  const request = (...args) => new Promise((resolve, reject) => calls.push({ args, resolve, reject }));
  return { calls, request };
}

function chatHarness() {
  const storage = memoryStorage();
  const deferred = controlledRequest();
  let index = 0;
  const chats = createConversations({
    storage: () => storage, send: deferred.request, id: () => String(++index),
  });
  chats.setOwner(1);
  return { chats, storage, calls: deferred.calls };
}

function texts(chats) {
  return chats.getSnapshot().messages.map((message) => message.text);
}

test("switching chats while pending keeps replies and loading with the owning thread", async () => {
  const { chats, calls } = chatHarness();
  const firstId = chats.getSnapshot().active;
  const first = chats.send("Tokyo");
  chats.newChat();
  const secondId = chats.getSnapshot().active;
  const second = chats.send("Paris");
  assert.equal(chats.activate(firstId), true);
  assert.equal(chats.getSnapshot().loading, true);
  calls[1].resolve({ response: "Paris reply" });
  await second;
  assert.deepEqual(texts(chats), ["Tokyo"]);
  assert.equal(chats.getSnapshot().loading, true);
  calls[0].resolve({ response: "Tokyo reply" });
  await first;
  assert.deepEqual(texts(chats), ["Tokyo", "Tokyo reply"]);
  assert.equal(chats.activate(secondId), true);
  assert.deepEqual(texts(chats), ["Paris", "Paris reply"]);
});

test("New Chat starts empty and cannot reuse a pending thread's context", async () => {
  const { chats, calls } = chatHarness();
  const pending = chats.send("First thread");
  chats.newChat();
  assert.deepEqual(texts(chats), []);
  assert.equal(chats.getSnapshot().loading, false);
  calls[0].resolve({ response: "Late forecast" });
  await pending;
  assert.deepEqual(texts(chats), []);
  const next = chats.send("New thread");
  assert.deepEqual(calls[1].args[0].conversation_history, []);
  calls[1].resolve({ response: "New forecast" });
  await next;
});

test("activate rejects unknown session IDs and leaves the draft active", () => {
  const { chats } = chatHarness();
  const before = chats.getSnapshot();
  assert.equal(chats.activate("unknown"), false);
  assert.equal(chats.getSnapshot(), before);
});

test("same-thread sends are synchronous single-flight and follow-up includes the completed exchange", async () => {
  const { chats, calls } = chatHarness();
  const first = chats.send("First question");
  await chats.send("Accidental duplicate");
  assert.equal(calls.length, 1);
  calls[0].resolve({ response: "First answer" });
  await first;
  const second = chats.send("Follow-up");
  assert.deepEqual(calls[1].args[0].conversation_history, [
    { role: "user", content: "First question" },
    { role: "assistant", content: "First answer" },
  ]);
  calls[1].resolve({ response: "Second answer" });
  await second;
});

test("clear aborts work and ignores an answer that arrives despite cancellation", async () => {
  const { chats, calls, storage } = chatHarness();
  const pending = chats.send("Will be deleted");
  chats.clear();
  assert.equal(calls[0].args[1].aborted, true);
  assert.equal(storage.getItem("skyreader_sessions:v2:account:1"), null);
  calls[0].resolve({ response: "Must not reappear" });
  await pending;
  assert.deepEqual(chats.getSnapshot().sessions, []);
  assert.equal(storage.getItem("skyreader_sessions:v2:account:1"), null);
});

test("logout and account switch invalidate pending replies and keep histories isolated", async () => {
  const { chats, storage, calls } = chatHarness();
  const pending = chats.send("Account A question");
  chats.setOwner(null, false);
  assert.equal(calls[0].args[1].aborted, true);
  assert.deepEqual(chats.getSnapshot().sessions, []);
  chats.setOwner(2);
  const next = chats.send("Account B question");
  calls[0].resolve({ response: "Account A late reply" });
  await pending;
  assert.deepEqual(texts(chats), ["Account B question"]);
  assert.equal(chats.getSnapshot().loading, true);
  calls[1].resolve({ response: "Account B reply" });
  await next;
  chats.setOwner(null);
  const guest = chats.send("Guest question");
  calls[2].resolve({ response: "Guest reply" });
  await guest;
  const refreshed = createConversations({ send: () => {}, storage: () => storage, id: () => "refreshed" });
  for (const [id, title] of [[1, "Account A question"], [2, "Account B question"], [null, "Guest question"]]) {
    refreshed.setOwner(id);
    assert.deepEqual(refreshed.getSnapshot().sessions.map((thread) => thread.title), [title]);
  }
  refreshed.clear();
  refreshed.setOwner(1);
  assert.deepEqual(refreshed.getSnapshot().sessions[0].messages.map((message) => message.text), ["Account A question"]);
});

function authHarness(stored = TOKEN, tabStored) {
  const persistent = memoryStorage(stored == null ? {} : { [KEY]: stored, skyreader_user: '{"id":999}' });
  const tab = memoryStorage(tabStored ? { [KEY]: tabStored } : {});
  const deferred = controlledRequest();
  const auth = createAuthSession({
    api: "http://test", persistent: () => persistent, tab: () => tab, request: deferred.request,
  });
  return { auth, persistent, tab, calls: deferred.calls };
}

const ok = (data) => new Response(JSON.stringify(data), { status: 200 });

test("refresh hides private content until /me confirms the stored token and profile", async () => {
  const { auth, persistent, calls } = authHarness();
  const check = auth.validate();
  assert.equal(auth.getSnapshot().phase, "checking");
  assert.equal(auth.getSnapshot().user, null);
  assert.equal(persistent.getItem("skyreader_user"), null);
  assert.equal(calls[0].args[0], "http://test/api/auth/me");
  assert.equal(calls[0].args[1].headers.Authorization, `Bearer ${TOKEN}`);
  calls[0].resolve(ok(USER));
  await check;
  assert.deepEqual(auth.getSnapshot(), { phase: "account", user: USER, notice: "" });
});

test("expired or revoked sessions and malformed tokens leave the app signed out", async () => {
  const { auth, calls, persistent } = authHarness();
  const check = auth.validate();
  calls[0].resolve(new Response(null, { status: 401 }));
  await check;
  assert.equal(auth.getSnapshot().phase, "signin");
  assert.equal(auth.getSnapshot().user, null);
  assert.equal(persistent.getItem(KEY), null);
  const malformed = authHarness("Bearer invalid");
  await malformed.auth.validate();
  assert.equal(malformed.calls.length, 0);
  assert.equal(malformed.persistent.getItem(KEY), null);
});

test("an unavailable server keeps the account locked and permits session validation retry", async () => {
  const { auth, calls, persistent } = authHarness();
  const initial = auth.validate();
  calls[0].reject(new Error("Offline"));
  await initial;
  assert.equal(auth.getSnapshot().phase, "unavailable");
  assert.equal(auth.getSnapshot().user, null);
  assert.equal(persistent.getItem(KEY), TOKEN);
  const retry = auth.validate();
  calls[1].resolve(ok(USER));
  await retry;
  assert.equal(auth.getSnapshot().user.id, USER.id);
});

test("logout clears the session immediately and an earlier /me result cannot restore it", async () => {
  const { auth, calls, persistent } = authHarness();
  const check = auth.validate();
  const logout = auth.logout();
  assert.equal(auth.getSnapshot().phase, "signin");
  assert.equal(persistent.getItem(KEY), null);
  assert.equal(calls[0].args[1].signal.aborted, true);
  assert.equal(calls[1].args[0], "http://test/api/auth/logout");
  assert.equal(calls[1].args[1].headers.Authorization, `Bearer ${TOKEN}`);
  calls[0].resolve(ok(USER));
  calls[1].resolve(ok({ message: "Logged out" }));
  await Promise.all([check, logout]);
  assert.equal(auth.getSnapshot().user, null);
});

test("logout revocation failures are visible and never restore the token", async () => {
  const { auth, calls, persistent } = authHarness();
  const logout = auth.logout();
  calls[0].reject(new Error("Offline"));
  await logout;
  assert.match(auth.getSnapshot().notice, /could not be revoked/);
  assert.equal(persistent.getItem(KEY), null);
  await auth.validate();
  assert.equal(calls.length, 1);
});

test("email authentication supports tab-only sessions and stale login cannot replace guest mode", async () => {
  const { auth, calls, persistent, tab } = authHarness(null);
  const pending = auth.signIn("signin", { email: USER.email, password: "fixture-password" }, false);
  auth.continueAsGuest();
  assert.equal(calls[0].args[1].signal.aborted, true);
  calls[0].resolve(ok({ user: USER, token: TOKEN }));
  await pending;
  assert.equal(auth.getSnapshot().phase, "guest");
  assert.equal(tab.getItem(KEY), null);
  const next = auth.signIn("signin", { email: USER.email, password: "fixture-password" }, false);
  calls[1].resolve(ok({ user: USER, token: TOKEN }));
  await next;
  assert.equal(auth.getSnapshot().phase, "account");
  assert.equal(tab.getItem(KEY), TOKEN);
  assert.equal(persistent.getItem(KEY), null);
});

test("a malformed profile response cannot activate account history", async () => {
  const { auth, calls, persistent } = authHarness();
  const check = auth.validate();
  calls[0].resolve(ok({ id: USER.id }));
  await check;
  assert.equal(auth.getSnapshot().phase, "signin");
  assert.equal(auth.getSnapshot().user, null);
  assert.equal(persistent.getItem(KEY), null);
});
