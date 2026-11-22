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
  send, threads, storage = local, id = () => globalThis.crypto.randomUUID(),
}) {
  let owner = null;
  let active = null;
  let sessions = [];
  let clearing = null;
  let notice = "";
  const provisioning = new Set();
  const requests = new Map();
  const errors = new Map();
  const listeners = new Set();
  let snapshot;

  function publish() {
    snapshot = {
      sessions, active, messages: sessions.find((thread) => thread.id === active)?.messages ?? [],
      loading: requests.has(active) || Boolean(clearing), error: errors.get(active) ?? "", notice,
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
    writeStorage(storage, `${storageKey(owner)}:active`, sessions.some((thread) => thread.id === active) ? active : null);
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

  function setThreadIdentity(threadId, identity) {
    sessions = sessions.map((thread) => thread.id === threadId ? { ...thread, server: identity } : thread);
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
      clearing = null;
      notice = "";
      sessions = owner ? loadSessions(storage, owner) : [];
      const savedActive = owner ? readStorage(storage, `${storageKey(owner)}:active`) : null;
      active = owner ? (sessions.some((thread) => thread.id === savedActive) ? savedActive : id()) : null;
      publish();
    },
    cancel() {
      cancelRequests();
      publish();
    },
    newChat() {
      if (!owner) return;
      active = id();
      save();
      publish();
    },
    select(threadId) {
      if (!sessions.some((thread) => thread.id === threadId)) return;
      active = threadId;
      save();
      publish();
    },
    clear({ server = true } = {}) {
      if (!owner || clearing) return;
      cancelRequests();
      sessions = [];
      active = id();
      notice = "";
      save();
      if (threads && server) {
        const clearingOwner = owner;
        const cleanup = Promise.allSettled([...provisioning]).then(() => {
          if (clearing === cleanup && owner === clearingOwner) return threads.clear();
        });
        clearing = cleanup;
        void cleanup.catch(() => {
          if (clearing === cleanup) notice = "Local history was cleared, but server conversation context could not be cleared. Try Clear History again.";
        }).finally(() => {
          if (clearing === cleanup) {
            clearing = null;
            publish();
          }
        });
      }
      publish();
    },
    async send(text) {
      const message = text.trim();
      const threadId = active;
      if (!message || !owner || !threadId || clearing || requests.has(threadId)) return;
      const request = { owner, id: id(), controller: new AbortController() };
      const isCurrent = () => owner === request.owner && requests.get(threadId) === request;
      const history = snapshot.messages.slice(-6).map(({ sender, text }) => ({ role: sender, content: text }));
      requests.set(threadId, request);
      errors.delete(threadId);
      append(threadId, { id: request.id, sender: "user", text: message, timestamp: timestamp() });
      publish();
      let identity = sessions.find((thread) => thread.id === threadId)?.server;
      try {
        const payload = { message, conversation_history: history };
        let data;
        if (threads) {
          if (!identity) {
            const creation = threads.create();
            provisioning.add(creation);
            try {
              identity = await creation;
            } finally {
              provisioning.delete(creation);
            }
            if (!isCurrent()) return;
            setThreadIdentity(threadId, identity);
          }
          const response = await threads.send(payload, request.controller.signal, identity);
          data = response.data;
          if (isCurrent() && Number.isSafeInteger(response.revision)) {
            setThreadIdentity(threadId, { ...identity, revision: response.revision });
          }
        } else {
          data = await send(payload, request.controller.signal);
        }
        if (isCurrent()) append(threadId, assistantMessage(data, `reply_${request.id}`));
      } catch (error) {
        if (isCurrent()) {
          if (identity && error.status === 404) setThreadIdentity(threadId, undefined);
          else if (identity && error.status === 409 && Number.isSafeInteger(error.revision)) {
            setThreadIdentity(threadId, { ...identity, revision: error.revision });
          }
          errors.set(threadId, error.message || "Failed to communicate with Sky Reader backend.");
        }
      } finally {
        if (isCurrent()) {
          requests.delete(threadId);
          publish();
        }
      }
    },
  };
}
