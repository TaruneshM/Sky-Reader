import { local, readStorage, session, writeStorage } from "./browserStorage.js";

const TOKEN_KEY = "skyreader_token";
const GUEST_ACTIVE_KEY = "skyreader_guest_active";
const AUTH_TIMEOUT_MS = 15_000;
const isToken = (value) => typeof value === "string" && /^[A-Za-z0-9_-]{43}$/.test(value);
const isProfile = (value) => Number.isSafeInteger(value?.id) && value.id > 0 &&
  typeof value.email === "string" && typeof value.name === "string";

export function createAuthSession({ api, request = fetch, persistent = local, tab = session }) {
  let snapshot = { phase: "checking", user: null, notice: "" };
  let token = null;
  let pending = null;
  let generation = 0;
  const listeners = new Set();

  function publish(phase, user = null, notice = "") {
    snapshot = { phase, user, notice };
    listeners.forEach((listener) => listener());
  }

  function invalidate() {
    generation += 1;
    pending?.abort();
    pending = null;
  }

  function clearCredentials() {
    token = null;
    for (const storage of [persistent, tab]) writeStorage(storage, TOKEN_KEY, null);
  }

  function startRequest() {
    invalidate();
    pending = new AbortController();
    return { generation, signal: AbortSignal.any([pending.signal, AbortSignal.timeout(AUTH_TIMEOUT_MS)]) };
  }

  async function validate() {
    const operation = startRequest();
    const stored = readStorage(tab, TOKEN_KEY) ?? readStorage(persistent, TOKEN_KEY);
    writeStorage(persistent, "skyreader_user", null);
    token = null;
    if (!isToken(stored)) {
      pending = null;
      clearCredentials();
      publish(readStorage(tab, GUEST_ACTIVE_KEY) === "1" ? "guest" : "signin");
      return;
    }
    publish("checking");
    try {
      const response = await request(`${api}/api/auth/me`, {
        headers: { Authorization: `Bearer ${stored}` }, signal: operation.signal, cache: "no-store",
      });
      if (operation.generation !== generation) return;
      if (response.status === 401 || response.status === 403) {
        clearCredentials();
        publish("signin", null, "Your session has ended. Please sign in again.");
        return;
      }
      if (!response.ok) throw new Error();
      const user = await response.json();
      if (operation.generation !== generation) return;
      if (!isProfile(user)) {
        clearCredentials();
        publish("signin", null, "Your saved session could not be restored. Please sign in again.");
        return;
      }
      writeStorage(tab, GUEST_ACTIVE_KEY, null);
      token = stored;
      publish("account", user);
    } catch {
      if (operation.generation === generation) {
        publish("unavailable", null, "Couldn’t verify your session. Retry when the server is available.");
      }
    } finally {
      if (operation.generation === generation) pending = null;
    }
  }

  async function signIn(mode, credentials, remember) {
    if (snapshot.phase === "submitting") return;
    const operation = startRequest();
    publish("submitting");
    try {
      const response = await request(`${api}/api/auth/${mode === "signin" ? "login" : "register"}`, {
        method: "POST", signal: operation.signal,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(credentials),
      });
      const data = await response.json().catch(() => null);
      if (operation.generation !== generation) return;
      if (!response.ok) {
        throw new Error(typeof data?.detail === "string" ? data.detail : "Check your information and try again.");
      }
      if (!isToken(data?.token) || !isProfile(data?.user)) throw new Error("Invalid response from the sign-in server.");
      clearCredentials();
      writeStorage(tab, GUEST_ACTIVE_KEY, null);
      token = data.token;
      writeStorage(remember ? persistent : tab, TOKEN_KEY, token);
      publish("account", data.user);
    } catch (error) {
      if (operation.generation === generation) {
        publish("signin", null, error.message || "Couldn’t reach the sign-in server.");
      }
    } finally {
      if (operation.generation === generation) pending = null;
    }
  }

  async function logout() {
    const previous = token ?? readStorage(tab, TOKEN_KEY) ?? readStorage(persistent, TOKEN_KEY);
    invalidate();
    const logoutGeneration = generation;
    clearCredentials();
    writeStorage(tab, GUEST_ACTIVE_KEY, null);
    publish("signin");
    if (!isToken(previous)) return;
    try {
      const response = await request(`${api}/api/auth/logout`, {
        method: "POST", headers: { Authorization: `Bearer ${previous}` },
        signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
      });
      if (!response.ok) throw new Error();
    } catch {
      if (generation === logoutGeneration) {
        publish("signin", null, "Signed out here. The server session could not be revoked.");
      }
    }
  }

  return {
    getSnapshot: () => snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    validate, signIn, logout, cancel: invalidate,
    authorization: (userId) => token && snapshot.user?.id === userId ? `Bearer ${token}` : null,
    showGuestRevocationFailure() {
      if (snapshot.phase === "signin") publish("signin", null, "The guest session could not be revoked on the server.");
    },
    continueAsGuest() {
      invalidate();
      clearCredentials();
      writeStorage(tab, GUEST_ACTIVE_KEY, "1");
      publish("guest");
    },
  };
}
