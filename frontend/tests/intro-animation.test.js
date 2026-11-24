import assert from "node:assert/strict";
import { after, before, beforeEach, test } from "node:test";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";
import { act, createElement } from "react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { createServer } from "vite";

const FRONTEND_ROOT = fileURLToPath(new URL("../", import.meta.url));

const TOKEN = "a".repeat(43);
const USER = { id: 7, email: "reader@example.test", name: "Reader" };

let dom, vite, App, createRoot, introState;

before(async () => {
  dom = new JSDOM("<div id='root'></div>", { url: "http://skyreader.test", pretendToBeVisual: true });
  dom.window.HTMLCanvasElement.prototype.getContext = () => ({
    measureText: () => ({ width: 100 }),
    getImageData: () => ({ data: new Uint8ClampedArray(400) }),
    clearRect: () => {},
    beginPath: () => {},
    arc: () => {},
    fill: () => {},
    fillText: () => {},
    setTransform: () => {},
    createLinearGradient: () => ({ addColorStop() {} }),
  });
  dom.window.matchMedia = (query) => ({
    matches: false,
    media: query,
    addEventListener() {},
    removeEventListener() {},
  });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.localStorage = dom.window.localStorage;
  globalThis.sessionStorage = dom.window.sessionStorage;
  globalThis.requestAnimationFrame = (cb) => dom.window.setTimeout(cb, 16);
  globalThis.cancelAnimationFrame = (id) => dom.window.clearTimeout(id);
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  ({ createRoot } = await import("react-dom/client"));
  vite = await createServer({
    root: FRONTEND_ROOT,
    appType: "custom",
    optimizeDeps: { noDiscovery: true, include: [] },
    server: { middlewareMode: true, ws: false, watch: null },
  });
  ({ default: App } = await vite.ssrLoadModule("/src/App.jsx"));
  await vite.ssrLoadModule("/src/components/SkyReaderIntro.jsx");
  introState = await vite.ssrLoadModule("/src/utils/introState.js");
});

beforeEach(() => {
  dom.window.localStorage.clear();
  dom.window.sessionStorage.clear();
  introState.resetIntroStateForTesting();
  dom.window.matchMedia = (query) => ({
    matches: false,
    media: query,
    addEventListener() {},
    removeEventListener() {},
  });
});

after(async () => {
  await vite?.close();
  dom?.window.close();
  delete globalThis.window;
  delete globalThis.document;
  delete globalThis.localStorage;
  delete globalThis.sessionStorage;
  delete globalThis.requestAnimationFrame;
  delete globalThis.cancelAnimationFrame;
  delete globalThis.ResizeObserver;
  delete globalThis.IS_REACT_ACT_ENVIRONMENT;
});

async function mountApp(t, initialPath, { account = false, request } = {}) {
  dom.window.localStorage.clear();
  dom.window.sessionStorage.clear();
  if (account) {
    dom.window.localStorage.setItem("skyreader_token", TOKEN);
  }

  t.mock.method(globalThis, "fetch", async (url, options) => {
    if (typeof request === "function") {
      return request(new URL(url), options);
    }
    if (url.toString().includes("/api/auth/me")) {
      if (account) {
        return new Response(JSON.stringify(USER), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response("", { status: 401 });
    }
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  });

  const container = document.querySelector("#root");
  container.innerHTML = "";
  const root = createRoot(container);
  t.after(() => act(async () => root.unmount()));

  let location, navigate;
  function RouteProbe() {
    location = useLocation();
    navigate = useNavigate();
    return null;
  }

  await act(async () => {
    root.render(createElement(MemoryRouter, { initialEntries: [initialPath] },
      createElement(RouteProbe), createElement(App),
    ));
  });

  // Allow RAF and lazy imports to resolve
  await act(async () => {
    await new Promise((r) => setTimeout(r, 120));
  });

  return {
    container,
    location: () => location,
    go: (dest) => act(async () => {
      navigate(dest);
      await new Promise((r) => setTimeout(r, 60));
    }),
  };
}

test("intro does not render when signed in, and is not loaded", async (t) => {
  introState.resetIntroStateForTesting();
  const ui = await mountApp(t, "/login", { account: true });
  // Signed-in users are routed to /chat by AuthLayout
  assert.equal(ui.location().pathname, "/chat");
  assert.equal(ui.container.querySelector(".sky-reader-intro-container"), null);
  // Module-level intro should not have played
  assert.equal(introState.hasIntroPlayed(), false);
});

test("intro does not render while phase is checking", async (t) => {
  introState.resetIntroStateForTesting();
  dom.window.localStorage.setItem("skyreader_token", TOKEN);
  let resolveMe;
  const pendingMe = new Promise((resolve) => { resolveMe = resolve; });

  const container = document.querySelector("#root");
  container.innerHTML = "";
  const root = createRoot(container);
  t.after(() => act(async () => root.unmount()));

  t.mock.method(globalThis, "fetch", async (url) => {
    if (url.toString().includes("/api/auth/me")) {
      await pendingMe;
      return new Response(JSON.stringify(USER), { status: 200 });
    }
    return new Response("{}", { status: 200 });
  });

  await act(async () => {
    root.render(createElement(MemoryRouter, { initialEntries: ["/login"] }, createElement(App)));
  });

  // During checking, App displays the status frame
  assert.match(container.textContent, /Checking your session/);
  assert.equal(container.querySelector(".sky-reader-intro-container"), null);

  // Clean up pending promise
  resolveMe();
  await act(async () => {
    await new Promise((r) => setTimeout(r, 20));
  });
});

test("intro renders once on /login when signed out, and does not replay on /signup or after failed sign-in", async (t) => {
  introState.resetIntroStateForTesting();
  const ui = await mountApp(t, "/login", { account: false });

  // Intro should be mounted on initial signed-out /login visit
  const intro = ui.container.querySelector(".sky-reader-intro-container");
  assert.ok(intro, "Intro container should be rendered on initial signed-out /login visit");
  assert.equal(intro.getAttribute("role"), "presentation");

  // Form should stay mounted with aria-hidden
  const emailInput = ui.container.querySelector("#login-email");
  assert.ok(emailInput, "Email input must stay mounted during intro");
  const formCard = emailInput.closest("div[aria-hidden='true']");
  assert.ok(formCard, "Form card must have aria-hidden during intro");

  // Skip the intro
  const skipBtn = ui.container.querySelector(".intro-skip-button");
  assert.ok(skipBtn, "Skip button should exist");
  await act(async () => {
    skipBtn.click();
    await new Promise((r) => setTimeout(r, 60));
  });

  // Intro is gone and card is revealed
  assert.equal(ui.container.querySelector(".sky-reader-intro-container"), null);
  assert.equal(introState.hasIntroPlayed(), true);

  // Navigate to /signup
  await ui.go("/signup");
  assert.equal(ui.location().pathname, "/signup");
  // Intro should NOT replay
  assert.equal(ui.container.querySelector(".sky-reader-intro-container"), null);

  // Failed sign-in attempt
  await act(async () => {
    const submitBtn = ui.container.querySelector("button[type=submit]");
    submitBtn.click();
    await new Promise((r) => setTimeout(r, 40));
  });
  // Intro must still NOT replay
  assert.equal(ui.container.querySelector(".sky-reader-intro-container"), null);
});

test("skip via Escape reveals the form and moves focus to email", async (t) => {
  introState.resetIntroStateForTesting();
  const ui = await mountApp(t, "/login", { account: false });
  assert.ok(ui.container.querySelector(".sky-reader-intro-container"));

  // Dispatch Escape key
  await act(async () => {
    dom.window.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await new Promise((r) => setTimeout(r, 60));
  });

  // Intro should be removed
  assert.equal(ui.container.querySelector(".sky-reader-intro-container"), null);
  // Email field should be focused
  assert.equal(dom.window.document.activeElement.id, "login-email");
});

test("skip via overlay click reveals the form and moves focus to email", async (t) => {
  introState.resetIntroStateForTesting();
  const ui = await mountApp(t, "/login", { account: false });
  const intro = ui.container.querySelector(".sky-reader-intro-container");
  assert.ok(intro);

  await act(async () => {
    intro.click();
    await new Promise((r) => setTimeout(r, 60));
  });

  assert.equal(ui.container.querySelector(".sky-reader-intro-container"), null);
  assert.equal(dom.window.document.activeElement.id, "login-email");
});

test("prefers-reduced-motion skips the intro entirely", async (t) => {
  introState.resetIntroStateForTesting();
  dom.window.matchMedia = (query) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener() {},
    removeEventListener() {},
  });

  const ui = await mountApp(t, "/login", { account: false });
  assert.equal(ui.container.querySelector(".sky-reader-intro-container"), null);
  assert.equal(introState.hasIntroPlayed(), true);
});
