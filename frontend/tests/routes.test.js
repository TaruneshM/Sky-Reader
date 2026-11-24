import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { JSDOM } from "jsdom";
import { act, createElement } from "react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { createServer } from "vite";

const TOKEN = "a".repeat(43);
const USER = { id: 7, email: "reader@example.test", name: "Reader" };
const ACCOUNT_HISTORY = "skyreader_sessions:v2:account:7";
const GUEST_HISTORY = "skyreader_sessions:v2:guest";
const ATMOSPHERE_KEY = "skyreader_atmosphere_mode";

let dom, vite, App, createRoot;

before(async () => {
  dom = new JSDOM("<div id='root'></div>", { url: "http://skyreader.test", pretendToBeVisual: true });
  dom.window.HTMLCanvasElement.prototype.getContext = () => null;
  dom.window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.localStorage = dom.window.localStorage;
  globalThis.requestAnimationFrame = dom.window.requestAnimationFrame.bind(dom.window);
  globalThis.cancelAnimationFrame = dom.window.cancelAnimationFrame.bind(dom.window);
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  ({ createRoot } = await import("react-dom/client"));
  vite = await createServer({
    appType: "custom", optimizeDeps: { noDiscovery: true, include: [] },
    server: { middlewareMode: true, ws: false, watch: null },
  });
  ({ default: App } = await vite.ssrLoadModule("/src/App.jsx"));
});

after(async () => {
  await vite?.close();
  dom?.window.close();
  delete globalThis.window;
  delete globalThis.document;
  delete globalThis.localStorage;
  delete globalThis.requestAnimationFrame;
  delete globalThis.cancelAnimationFrame;
  delete globalThis.IS_REACT_ACT_ENVIRONMENT;
});

function thread(id, title = `Weather inquiry ${id}`) {
  return {
    id, title, messages: [{ id, sender: "user", text: title }],
    server: { id: "b".repeat(32), revision: 4 },
  };
}

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), { status, headers });
}

function deferred() {
  let resolve;
  const result = new Promise((complete) => { resolve = complete; });
  return { result, resolve };
}

async function mount(t, pathname, { account = false, guest = false, sessions = [], request, atmosphereMode } = {}) {
  dom.window.localStorage.clear();
  dom.window.sessionStorage.clear();
  if (atmosphereMode !== undefined) dom.window.localStorage.setItem(ATMOSPHERE_KEY, atmosphereMode);
  if (account) dom.window.localStorage.setItem("skyreader_token", TOKEN);
  if (guest) dom.window.sessionStorage.setItem("skyreader_guest_active", "1");
  (guest ? dom.window.sessionStorage : dom.window.localStorage)
    .setItem(guest ? GUEST_HISTORY : ACCOUNT_HISTORY, JSON.stringify(sessions));

  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(typeof request, "function", `Unexpected offline request to ${url}`);
    return request(new URL(url), options);
  });

  const container = document.querySelector("#root");
  const root = createRoot(container);
  t.after(() => act(async () => root.unmount()));
  let location, navigate;
  function RouteProbe() {
    location = useLocation();
    navigate = useNavigate();
    return null;
  }

  await act(async () => {
    root.render(createElement(MemoryRouter, { initialEntries: [pathname] },
      createElement(RouteProbe), createElement(App),
    ));
  });
  return {
    container, location: () => location,
    go: (destination, options) => act(async () => { navigate(destination, options); }),
    click: (selector) => act(async () => {
      const element = container.querySelector(selector);
      assert.ok(element, selector);
      element.click();
    }),
  };
}

function setInput(selector, text) {
  const input = document.querySelector(selector);
  Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, "value").set.call(input, text);
  input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
}

async function submitAuth(ui) {
  await act(async () => {
    setInput("input[type=email]", USER.email);
    setInput("input[type=password]", "fixture-pass");
  });
  await ui.click("button[type=submit]");
}

function assertFreshChat(ui) {
  assert.equal(ui.location().pathname, "/chat");
  assert.equal(ui.location().search, "");
  assert.equal(ui.location().hash, "");
  assert.ok(ui.container.querySelector(".welcome-hero-container"));
  assert.equal(ui.container.querySelector(".chat-thread-list"), null);
  assert.equal(ui.container.querySelector(".chat-header-title").textContent, "New chat");
  assert.equal(ui.container.querySelector(".sidebar-recent-item-btn[aria-current]"), null);
  assert.equal(ui.container.querySelector(".sidebar-recent-item-btn.active"), null);
}

test("signed-out saved chat URL is discarded and sign-in opens a fresh chat", async (t) => {
  const ui = await mount(t, "/chat/abc123?source=bookmark#question", {
    sessions: [thread("abc123")],
    request: (url, options) => {
      assert.equal(url.pathname, "/api/auth/login");
      assert.deepEqual(JSON.parse(options.body), { email: USER.email, password: "fixture-pass" });
      return json({ token: TOKEN, user: USER });
    },
  });
  assert.equal(ui.location().pathname, "/login");
  assert.equal(ui.location().state, null);
  assert.equal(ui.container.querySelector(".sky-sidebar"), null);
  await submitAuth(ui);
  assertFreshChat(ui);
  assert.ok(ui.container.querySelector('.sidebar-recent-item-btn[href="/chat/abc123"]'));
});

test("signed-out preferences URL returns after sign-in with search and hash", async (t) => {
  const from = "/preferences?source=bookmark#settings";
  const ui = await mount(t, from, {
    request: (url) => {
      assert.equal(url.pathname, "/api/auth/login");
      return json({ token: TOKEN, user: USER });
    },
  });
  assert.equal(ui.location().pathname, "/login");
  assert.equal(ui.location().state.from, from);
  await submitAuth(ui);
  const { pathname, search, hash } = ui.location();
  assert.equal(pathname + search + hash, from);
  assert.ok(ui.container.querySelector(".preferences-tab-wrapper"));
});

test("signup ignores a stale chat return path", async (t) => {
  const ui = await mount(t, { pathname: "/signup", state: { from: "/chat/abc123" } }, {
    sessions: [thread("abc123")],
    request: (url) => {
      assert.equal(url.pathname, "/api/auth/register");
      return json({ token: TOKEN, user: USER });
    },
  });
  await submitAuth(ui);
  assertFreshChat(ui);
});

test("auth rejects non-internal and unlisted return paths", async (t) => {
  const ui = await mount(t, "/chat", {
    account: true,
    request: (url) => {
      assert.equal(url.pathname, "/api/auth/me");
      return json(USER);
    },
  });
  for (const from of ["//example.test", "/\\example.test", "/unknown", "/CHAT?old=1"]) {
    await ui.go("/login", { state: { from } });
    assertFreshChat(ui);
  }
});

test("protected URL stays put during session checking and unavailable sessions can retry", async (t) => {
  const first = deferred();
  let checks = 0;
  const ui = await mount(t, "/preferences", {
    account: true,
    request: (url) => {
      assert.equal(url.pathname, "/api/auth/me");
      return checks++ === 0 ? first.result : json(USER);
    },
  });
  assert.equal(ui.location().pathname, "/preferences");
  assert.match(ui.container.textContent, /Checking your session/);
  assert.doesNotMatch(ui.container.textContent, /Recent Inquiries|Continue as guest/);
  await act(async () => { first.resolve(json({}, 503)); });
  assert.equal(ui.location().pathname, "/login");
  assert.equal(ui.location().state.from, "/preferences");
  const retry = [...ui.container.querySelectorAll("button")].find((button) => /Retry session/.test(button.textContent));
  assert.ok(retry);
  await act(async () => retry.click());
  assert.equal(ui.location().pathname, "/preferences");
  assert.ok(ui.container.querySelector(".preferences-tab-wrapper"));
});

test("direct login URL redirects a signed-in account to a fresh chat and logout returns to login", async (t) => {
  const ui = await mount(t, "/login", {
    account: true, sessions: [thread("saved")],
    request: (url) => {
      assert.ok(["/api/auth/me", "/api/auth/logout"].includes(url.pathname));
      return json(USER);
    },
  });
  assert.equal(ui.location().pathname, "/chat");
  assert.ok(ui.container.querySelector(".welcome-hero-container"));
  assert.equal(ui.container.querySelector(".chat-header-title").textContent, "New chat");
  assert.equal(ui.container.querySelectorAll(".sidebar-recent-item-btn").length, 1);
  await ui.go("/");
  assert.equal(ui.location().pathname, "/chat");
  await ui.click(".sidebar-logout-btn");
  assert.equal(ui.location().pathname, "/login");
});

test("signed-in direct chat URL still opens, and logout then sign-in starts fresh", async (t) => {
  const ui = await mount(t, "/chat/abc123", {
    account: true, sessions: [thread("abc123")],
    request: (url) => {
      if (url.pathname === "/api/auth/me") return json(USER);
      if (url.pathname === "/api/auth/logout") return new Response(null, { status: 204 });
      assert.equal(url.pathname, "/api/auth/login");
      return json({ token: TOKEN, user: USER });
    },
  });
  assert.equal(ui.location().pathname, "/chat/abc123");
  assert.match(ui.container.querySelector(".chat-thread-list").textContent, /Weather inquiry abc123/);
  assert.ok(ui.container.querySelector('.sidebar-recent-item-btn[href="/chat/abc123"][aria-current="page"]'));

  await ui.click(".sidebar-logout-btn");
  assert.equal(ui.location().pathname, "/login");
  assert.equal(ui.location().state, null);
  await submitAuth(ui);
  assertFreshChat(ui);
  assert.ok(ui.container.querySelector('.sidebar-recent-item-btn[href="/chat/abc123"]'));
});

test("sign-in and sign-up links follow browser history and guests can return to sign in", async (t) => {
  const ui = await mount(t, "/preferences");
  assert.equal(ui.location().state.from, "/preferences");
  await ui.click('a[href="/signup"]');
  assert.equal(ui.location().pathname, "/signup");
  assert.ok(ui.container.querySelector("#login-name"));
  await ui.go(-1);
  assert.equal(ui.location().pathname, "/login");
  await ui.go(1);
  assert.equal(ui.location().pathname, "/signup");
  const guest = [...ui.container.querySelectorAll("button")].find((button) => /Continue as guest/.test(button.textContent));
  assert.ok(guest);
  await act(async () => guest.click());
  assertFreshChat(ui);
  await ui.click(".sidebar-logout-btn");
  assert.equal(ui.location().pathname, "/login");
});

test("saved chat URL selects the only current recent link, even outside the first ten", async (t) => {
  const longTitle = "A long chat title that should be displayed in full when hovering over the header";
  const sessions = Array.from({ length: 12 }, (_, index) => thread(`chat-${index}`));
  sessions.push(thread("older", longTitle));

  const ui = await mount(t, "/chat/older", { guest: true, sessions });
  const recent = [...ui.container.querySelectorAll(".sidebar-recent-item-btn")];
  assert.equal(recent.length, 11);
  assert.equal(recent.some((link) => link.pathname === "/chat/chat-10"), false);
  const currentLinks = [...ui.container.querySelectorAll('nav [aria-current="page"]')];
  assert.deepEqual(currentLinks.map((link) => link.pathname), ["/chat/older"]);
  assert.ok(currentLinks[0].classList.contains("active"));
  const title = ui.container.querySelector(".chat-header-title");
  assert.equal(title.textContent, longTitle);
  assert.equal(title.title, longTitle);
  assert.doesNotMatch(ui.container.textContent, /Sky Reader 4/);
  await ui.click(".new-chat-btn");
  assert.equal(ui.location().pathname, "/chat");
  assert.ok(ui.container.querySelector(".welcome-hero-container"));
  await ui.go(-1);
  assert.match(ui.container.querySelector(".chat-thread-list").textContent, /A long chat title/);
  await ui.go("/chat/wrong-owner");
  assert.equal(ui.location().pathname, "/chat");
});

test("unknown routes show 404 and Saved Places and Notifications present empty states", async (t) => {
  const ui = await mount(t, "/no-such-page", { guest: true });
  assert.match(ui.container.textContent, /Page not found/);
  assert.equal(ui.container.querySelector('a[href="/chat"]').textContent, "Back to chat");
  await ui.go("/saved");
  assert.match(ui.container.querySelector("main").textContent, /Saved PlacesComing soon/);
  await ui.click('a[href="/notifications"]');
  assert.match(ui.container.querySelector("main").textContent, /NotificationsComing soon/);
  assert.equal(ui.container.querySelector(".nav-item-badge"), null);
});

test("dashboard consultation starts a clean thread and pending replies follow its URL", async (t) => {
  const serverId = "c".repeat(32);
  const reply = deferred();
  const sends = [];
  const ui = await mount(t, "/chat/older", {
    guest: true, sessions: [thread("older")],
    request: (url, options) => {
      switch (url.pathname) {
        case "/weather":
          return json({ location: { name: "Dehradun" }, current: {
            temperature: 20, weather_code: 0, condition: "Clear", humidity: 50, wind_speed: 2,
          } });
        case "/api/guest/session":
          return json({ credential: TOKEN }, 201);
        case "/api/chat/threads":
          return json({ thread_id: serverId, thread_revision: 0 }, 201);
        case "/api/agent/chat":
          sends.push(JSON.parse(options.body));
          return reply.result;
        default:
          assert.fail(`Unexpected mock request ${url.pathname}`);
      }
    },
  });
  await ui.click('a[href="/dashboard"]');
  assertAtmosphereOff(ui);
  await ui.click(".consult-agent-hero-btn");
  const consultation = ui.location().pathname;
  assert.match(consultation, /^\/chat\/[^/]+$/);
  assert.notEqual(consultation, "/chat/older");
  assert.equal(sends.length, 1);
  assert.equal(sends[0].thread_id, serverId);
  assert.equal(sends[0].thread_revision, 0);
  assert.deepEqual(sends[0].conversation_history, []);
  assert.match(sends[0].message, /Dehradun/);
  assert.ok(ui.container.querySelector(".thinking-row"));
  await ui.click('a[href="/chat/older"]');
  assert.equal(ui.container.querySelector(".thinking-row"), null);
  await act(async () => { reply.resolve(json({ response: "Fixture consultation" }, 200, {
    "X-Thread-Revision": "1",
  })); });
  assert.doesNotMatch(ui.container.querySelector(".chat-thread-list").textContent, /Fixture consultation/);
  await ui.go(consultation);
  assert.match(ui.container.querySelector(".chat-thread-list").textContent, /Fixture consultation/);
});

test("the first WelcomeHero prompt replaces the empty chat URL", async (t) => {
  const sends = [];
  const ui = await mount(t, "/saved", {
    guest: true, sessions: [thread("older")],
    request: (url, options) => {
      if (url.pathname === "/api/guest/session") return json({ credential: TOKEN }, 201);
      if (url.pathname === "/api/chat/threads") {
        return json({ thread_id: "d".repeat(32), thread_revision: 0 }, 201);
      }
      assert.equal(url.pathname, "/api/agent/chat");
      sends.push(JSON.parse(options.body));
      return json({ response: "Fixture reply" }, 200, { "X-Thread-Revision": "1" });
    },
  });
  await ui.click('a[href="/chat"]');
  await ui.click(".video1-starter-card");
  assert.match(ui.location().pathname, /^\/chat\/[^/]+$/);
  assert.equal(sends.length, 1);
  assert.deepEqual(sends[0].conversation_history, []);
  await ui.go(-1);
  assert.equal(ui.location().pathname, "/saved");
});

function assertAtmosphereOff(ui) {
  assert.equal(localStorage.getItem(ATMOSPHERE_KEY), "none");
  assert.equal(ui.container.querySelector(".atmosphere-active-label").textContent, "None");
  assert.equal(ui.container.querySelector(".weather-atmosphere-canvas-wrapper"), null);
  assert.equal(ui.container.querySelector("canvas"), null);
  assert.ok(ui.container.querySelector(".sky-cloud-layer"));
  assert.equal(ui.container.querySelector(".skyreader-root-environment").className, "skyreader-root-environment");
}

for (const [atmosphereMode, title] of [
  [undefined, "missing preference defaults to None"],
  ["auto", "stored Auto migrates to None"],
  ["invalid-scene", "invalid preference migrates to None"],
]) {
  test(`${title} without creating a canvas or scheduling an animation frame`, async (t) => {
    const context = t.mock.method(dom.window.HTMLCanvasElement.prototype, "getContext");
    const frame = t.mock.method(globalThis, "requestAnimationFrame");
    const ui = await mount(t, "/chat", { guest: true, atmosphereMode });
    assertAtmosphereOff(ui);
    assert.equal(context.mock.callCount(), 0);
    assert.equal(frame.mock.callCount(), 0);
  });
}

test("an incoming weather reply leaves the atmosphere off", async (t) => {
  const reply = "Heavy rain, thunderstorms, and wind gusts are possible.";
  const ui = await mount(t, "/chat", {
    guest: true,
    request: (url) => {
      if (url.pathname === "/api/guest/session") return json({ credential: TOKEN }, 201);
      if (url.pathname === "/api/chat/threads") {
        return json({ thread_id: "e".repeat(32), thread_revision: 0 }, 201);
      }
      assert.equal(url.pathname, "/api/agent/chat");
      return json({
        response: reply,
        claims: [{ variable: "precipitation_probability", claimed_value: 80 }],
      }, 200, { "X-Thread-Revision": "1" });
    },
  });
  await ui.click(".video1-starter-card");
  assert.ok(ui.container.querySelector(".chat-thread-list").textContent.includes(reply));
  assertAtmosphereOff(ui);
});

test("manual Rain still starts a canvas and switching to None stops its animation frame", async (t) => {
  t.mock.method(dom.window.HTMLCanvasElement.prototype, "getContext", () => ({
    clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, ellipse() {}, stroke() {},
  }));
  const pendingFrames = new Set();
  let frameId = 0;
  const frame = t.mock.method(globalThis, "requestAnimationFrame", () => {
    pendingFrames.add(++frameId);
    return frameId;
  });
  t.mock.method(globalThis, "cancelAnimationFrame", (id) => pendingFrames.delete(id));
  const ui = await mount(t, "/preferences", { guest: true, atmosphereMode: "rain" });
  const select = ui.container.querySelector("#atmosphere-scene");
  assert.equal(select.value, "rain");
  assert.equal(ui.container.querySelector(".atmosphere-active-label").textContent, "Rain Shower");
  assert.ok(ui.container.querySelector(".scene-rain canvas"));
  assert.equal(pendingFrames.size, 1);
  const framesBeforeSwitchingOff = frame.mock.callCount();

  await act(async () => {
    select.value = "none";
    select.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  });
  assertAtmosphereOff(ui);
  assert.equal(pendingFrames.size, 0);
  assert.equal(frame.mock.callCount(), framesBeforeSwitchingOff);

  await ui.click(".atmosphere-pill-btn");
  const rain = [...ui.container.querySelectorAll(".dropdown-scene-btn")]
    .find((button) => button.textContent.includes("Rain Shower"));
  assert.ok(rain);
  await act(async () => rain.click());
  assert.ok(ui.container.querySelector(".scene-rain canvas"));
  assert.ok(ui.container.querySelector(".atmosphere-active-rain"));
  assert.equal(select.value, "rain");
  assert.equal(localStorage.getItem(ATMOSPHERE_KEY), "rain");
  assert.equal(pendingFrames.size, 1);
  assert.equal(frame.mock.callCount(), framesBeforeSwitchingOff + 1);
});
