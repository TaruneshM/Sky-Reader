import { readStorage, session, writeStorage } from "./browserStorage.js";

const GUEST_KEY = "skyreader_guest_credential";
const credentialPattern = /^[A-Za-z0-9_-]{43}$/;
const threadPattern = /^[A-Za-z0-9_-]{32}$/;
const lifecycleTimeout = () => AbortSignal.timeout(15_000);

export function createChatThreads({ api, authorization, guest, request = fetch, tab = session }) {
  let guestCredential = guest ? readStorage(tab, GUEST_KEY) : null;
  let pendingGuest;
  let closed = false;

  async function headers() {
    if (!guest) {
      const bearer = authorization();
      if (!bearer) throw new Error("Sign in again to access your conversations.");
      return { Authorization: bearer };
    }
    if (closed) throw new Error("This guest session has ended.");
    let credential = guestCredential;
    if (!credentialPattern.test(credential ?? "")) {
      pendingGuest ??= (async () => {
        const response = await request(`${api}/api/guest/session`, { method: "POST", cache: "no-store", signal: lifecycleTimeout() });
        if (!response.ok) throw new Error("Could not establish a guest session.");
        const data = await response.json();
        if (!credentialPattern.test(data.credential ?? "")) throw new Error("Invalid guest session response.");
        if (!closed) {
          guestCredential = data.credential;
          writeStorage(tab, GUEST_KEY, data.credential);
        }
        return data.credential;
      })().finally(() => { pendingGuest = undefined; });
      credential = await pendingGuest;
    }
    if (closed) throw new Error("This guest session has ended.");
    return { "X-Guest-Session": credential };
  }

  async function checked(response, fallback) {
    if (response.ok) return response;
    const data = await response.json().catch(() => null);
    const error = new Error(typeof data?.detail === "string" ? data.detail : fallback);
    error.status = response.status;
    const revision = response.headers.get("X-Thread-Revision");
    if (revision !== null && /^\d+$/.test(revision) && Number.isSafeInteger(Number(revision))) {
      error.revision = Number(revision);
    }
    throw error;
  }

  return {
    async create() {
      const response = await checked(await request(`${api}/api/chat/threads`, {
        method: "POST", headers: await headers(), cache: "no-store", signal: lifecycleTimeout(),
      }), "Could not create a conversation thread.");
      const data = await response.json();
      if (!threadPattern.test(data.thread_id ?? "") || data.thread_revision !== 0) {
        throw new Error("Invalid conversation thread response.");
      }
      return { id: data.thread_id, revision: data.thread_revision };
    },
    async send(payload, signal, thread) {
      const response = await checked(await request(`${api}/api/agent/chat`, {
        method: "POST", signal,
        headers: { ...await headers(), "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, thread_id: thread.id, thread_revision: thread.revision }),
      }), "Sky Reader could not process this request.");
      const rawRevision = response.headers.get("X-Thread-Revision");
      const revision = rawRevision !== null && /^\d+$/.test(rawRevision) ? Number(rawRevision) : undefined;
      return { data: await response.json(), revision };
    },
    async clear() {
      // No server-side guest state can exist if this tab has never requested a guest credential.
      if (guest && !pendingGuest && !guestCredential) return;
      await checked(await request(`${api}/api/chat/threads`, {
        method: "DELETE", headers: await headers(), signal: lifecycleTimeout(),
      }), "Could not clear saved conversation context.");
    },
    async revokeGuest() {
      if (!guest) return;
      closed = true;
      const stored = guestCredential;
      guestCredential = null;
      writeStorage(tab, GUEST_KEY, null);
      const credential = stored || await pendingGuest;
      if (!credentialPattern.test(credential ?? "")) return;
      await checked(await request(`${api}/api/guest/session`, {
        method: "DELETE", headers: { "X-Guest-Session": credential }, signal: lifecycleTimeout(),
      }), "The guest session could not be revoked.");
    },
  };
}
