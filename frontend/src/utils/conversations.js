import { local, readStorage, writeStorage } from "./browserStorage.js";

const ownerKey = (userId) => userId == null ? "guest" : `account:${userId}`;
const storageKey = (owner) => `skyreader_sessions:v2:${owner}`;
const timestamp = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function loadSessions(storage, owner) {
  try {
    const sessions = JSON.parse(readStorage(storage, storageKey(owner)));
    if (Array.isArray(sessions)) {
      return sessions.filter((thread) => typeof thread?.id === "string" &&
        Array.isArray(thread.messages) && thread.messages.every((message) =>
          typeof message?.text === "string" && ["user", "assistant"].includes(message.sender)));
    }
  } catch {
    // A corrupt snapshot has no usable conversation history.
  }
  return [];
}

function assistantMessage(data, id) {
  return {
    id, sender: "assistant", text: data.response || "No meteorological response received.",
    timestamp: timestamp(), toolCalls: data.tool_calls || [], iterations: data.iterations || 1,
    claims: data.claims || [], validationReport: data.validation_report || null,
    explanation: data.explanation || null, riskAssessment: data.risk_assessment || null,
  };
}

export function createConversations({
  send, storage = local, id = () => globalThis.crypto.randomUUID(),
}) {
  let owner = null;
  let active = null;
  let sessions = [];
  const requests = new Map();
  const errors = new Map();
  const listeners = new Set();
  let snapshot;

  function publish() {
    snapshot = {
      sessions, active, messages: sessions.find((thread) => thread.id === active)?.messages ?? [],
      loading: requests.has(active), error: errors.get(active) ?? "",
    };
    listeners.forEach((listener) => listener());
  }

  function cancelRequests() {
    for (const request of requests.values()) request.controller.abort();
    requests.clear();
    errors.clear();
  }

  function save() {
    writeStorage(storage, storageKey(owner), sessions.length ? JSON.stringify(sessions) : null);
  }

  function append(threadId, message) {
    const existing = sessions.find((thread) => thread.id === threadId);
    const first = message.text.length > 36 ? `${message.text.slice(0, 36)}...` : message.text;
    const thread = existing
      ? { ...existing, messages: [...existing.messages, message], updatedAt: Date.now() }
      : { id: threadId, title: first, messages: [message], updatedAt: Date.now() };
    sessions = [thread, ...sessions.filter((item) => item.id !== threadId)];
    save();
  }

  publish();

  return {
    getSnapshot: () => snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setOwner(userId, allowed = true) {
      const next = allowed ? ownerKey(userId) : null;
      if (next === owner) return;
      cancelRequests();
      owner = next;
      active = owner ? id() : null;
      sessions = owner ? loadSessions(storage, owner) : [];
      publish();
    },
    cancel() {
      cancelRequests();
      publish();
    },
    newChat() {
      if (!owner) return;
      active = id();
      publish();
    },
    select(threadId) {
      if (!sessions.some((thread) => thread.id === threadId)) return;
      active = threadId;
      publish();
    },
    clear() {
      if (!owner) return;
      cancelRequests();
      sessions = [];
      active = id();
      save();
      publish();
    },
    async send(text) {
      const message = text.trim();
      const threadId = active;
      if (!message || !owner || !threadId || requests.has(threadId)) return;
      const request = { owner, id: id(), controller: new AbortController() };
      const isCurrent = () => owner === request.owner && requests.get(threadId) === request;
      const history = snapshot.messages.slice(-6).map(({ sender, text }) => ({ role: sender, content: text }));
      requests.set(threadId, request);
      errors.delete(threadId);
      append(threadId, { id: request.id, sender: "user", text: message, timestamp: timestamp() });
      publish();
      try {
        const data = await send({ message, conversation_history: history }, request.controller.signal);
        if (isCurrent()) append(threadId, assistantMessage(data, `reply_${request.id}`));
      } catch (error) {
        if (isCurrent()) errors.set(threadId, error.message || "Failed to communicate with Sky Reader backend.");
      } finally {
        if (isCurrent()) {
          requests.delete(threadId);
          publish();
        }
      }
    },
  };
}
