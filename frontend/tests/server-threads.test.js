import assert from "node:assert/strict";
import { test } from "node:test";
import { setImmediate as tick } from "node:timers/promises";
import { createChatThreads } from "../src/utils/chatThreads.js";
import { createConversations } from "../src/utils/conversations.js";
import { createAuthSession } from "../src/utils/authSession.js";

const THREAD = "a".repeat(32);
const CREDENTIAL = "b".repeat(43);

function storage() {
  const values = new Map();
  return () => ({
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  });
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

const json = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), { status, headers });

test("refresh restores the selected server thread and its revision within the account", async () => {
  const browser = storage();
  let next = 0;
  const threadSends = [];
  const transport = {
    async create() { return { id: THREAD, revision: 0 }; },
    async send(_payload, _signal, identity) {
      threadSends.push(identity);
      return { data: { response: "Fixture reply" }, revision: identity.revision + 1 };
    },
  };
  const make = () => createConversations({ storage: browser, threads: transport, id: () => String(++next) });
  const original = make();
  original.setOwner(7);
  await original.send("Weather in Tokyo?");
  const selected = original.getSnapshot().active;
  const refreshed = make();
  refreshed.setOwner(7);
  assert.equal(refreshed.getSnapshot().active, selected);
  await refreshed.send("What about tomorrow?");
  assert.deepEqual(threadSends, [{ id: THREAD, revision: 0 }, { id: THREAD, revision: 1 }]);
  refreshed.setOwner(8);
  assert.deepEqual(refreshed.getSnapshot().sessions, []);
});

test("clear waits for pending provisioning but never lets the abandoned turn reach chat", async () => {
  const creation = deferred();
  const calls = [];
  const chats = createConversations({ storage: storage(), threads: {
    create: () => creation.promise,
    send: () => { calls.push("send"); },
    clear: () => { calls.push("clear"); },
  }});
  chats.setOwner(7);
  const pending = chats.send("Old thread");
  chats.clear();
  assert.equal(chats.getSnapshot().loading, true);
  creation.resolve({ id: THREAD, revision: 0 });
  await pending;
  await tick();
  assert.deepEqual(calls, ["clear"]);
  assert.deepEqual(chats.getSnapshot().sessions, []);
  assert.equal(chats.getSnapshot().loading, false);
});

test("a deferred clear cannot run under the next account", async () => {
  const creation = deferred();
  let clearCount = 0;
  const chats = createConversations({ storage: storage(), threads: {
    create: () => creation.promise,
    clear: () => { clearCount += 1; },
  }});
  chats.setOwner(7);
  const pending = chats.send("Old thread");
  chats.clear();
  chats.setOwner(8);
  creation.resolve({ id: THREAD, revision: 0 });
  await pending;
  await tick();
  assert.equal(clearCount, 0);
  assert.deepEqual(chats.getSnapshot().sessions, []);
});

test("conflict updates the revision without automatically resending the turn", async () => {
  const revisions = [];
  const chats = createConversations({ storage: storage(), threads: {
    async create() { return { id: THREAD, revision: 0 }; },
    async send(_payload, _signal, { revision }) {
      revisions.push(revision);
      if (revision === 0) throw Object.assign(new Error("The conversation changed."), { status: 409, revision: 4 });
      return { data: { response: "Updated reply" }, revision: 5 };
    },
  }});
  chats.setOwner(7);
  await chats.send("Stale turn");
  assert.deepEqual(revisions, [0]);
  assert.match(chats.getSnapshot().error, /changed/);
  await chats.send("New turn");
  assert.deepEqual(revisions, [0, 4]);
});

test("guest uses a server credential and a separate header from account authentication", async () => {
  const tab = storage();
  const calls = [];
  async function request(url, options) {
    calls.push([url, options]);
    if (url.endsWith("/api/guest/session") && options.method === "POST") return json({ credential: CREDENTIAL }, 201);
    if (url.endsWith("/api/guest/session") && options.method === "DELETE") return new Response(null, { status: 204 });
    if (url.endsWith("/api/chat/threads")) return json({ thread_id: THREAD, thread_revision: 0 }, 201);
    return json({ response: "Fixture" }, 200, { "X-Thread-Revision": "1" });
  }

  const transport = createChatThreads({ api: "http://test", guest: true, authorization: () => "Bearer wrong", request, tab });
  const [thread] = await Promise.all([transport.create(), transport.create()]);
  const restored = createChatThreads({ api: "http://test", guest: true, request, tab });
  const result = await restored.send({ message: "Weather?" }, undefined, thread);
  assert.equal(result.revision, 1);
  assert.equal(calls.filter(([url]) => url.endsWith("/api/guest/session")).length, 1);
  const [, chat] = calls.at(-1);
  assert.equal(chat.headers["X-Guest-Session"], CREDENTIAL);
  assert.equal(chat.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(chat.body), { message: "Weather?", thread_id: THREAD, thread_revision: 0 });
  await restored.revokeGuest();
  assert.equal(tab().getItem("skyreader_guest_credential"), null);
});

test("guest mode restores in its tab and account credentials are scoped to the current user", async () => {
  const tab = storage();
  const persistent = storage();
  const request = async () => json({ token: CREDENTIAL, user: { id: 7, email: "reader@example.com", name: "Reader" } });
  const make = () => createAuthSession({ api: "http://test", tab, persistent, request });
  make().continueAsGuest();
  const refreshed = make();
  await refreshed.validate();
  assert.equal(refreshed.getSnapshot().phase, "guest");
  await refreshed.signIn("signin", {}, false);
  assert.equal(refreshed.authorization(7), `Bearer ${CREDENTIAL}`);
  assert.equal(refreshed.authorization(8), null);
});

test("a provider error stays outside the transcript and keeps the thread revision", async () => {
  const sent = [];
  const threads = createChatThreads({
    api: "", guest: false, authorization: () => "Bearer fixture",
    async request(path, options) {
      if (path === "/api/chat/threads") return json({ thread_id: THREAD, thread_revision: 0 }, 201);
      sent.push(JSON.parse(options.body));
      if (sent.length === 1) {
        return json({ detail: "AI usage limit reached.", error: { category: "groq_quota_exhausted" } }, 429);
      }
      return json({ response: "Weather answer" }, 200, { "X-Thread-Revision": "1" });
    },
  });
  const chats = createConversations({ storage: storage(), threads });
  chats.setOwner(7);
  await chats.send("Hello");
  assert.equal(chats.getSnapshot().error, "AI usage limit reached.");
  assert.deepEqual(chats.getSnapshot().messages.map(({ sender }) => sender), ["user"]);
  await chats.send("How is the weather?");
  assert.deepEqual(sent.map(({ thread_revision }) => thread_revision), [0, 0]);
  assert.ok(sent[1].conversation_history.every(({ content }) => content !== "AI usage limit reached."));
});
