import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("login renders guest access and disables unavailable authentication features", async () => {
  const vite = await createServer({
    appType: "custom",
    server: { middlewareMode: true, ws: false, watch: null },
  });
  try {
    const { default: LoginPage } = await vite.ssrLoadModule("/src/components/LoginPage.jsx");
    const html = renderToStaticMarkup(createElement(LoginPage, {
      onContinueAsGuest: () => {}, onAuthenticate: () => {},
    }));
    assert.match(html, /Continue as guest/);
    const buttons = html.match(/<button\b[\s\S]*?<\/button>/g);
    for (const label of ["Password reset unavailable", "Google sign-in unavailable"]) {
      const button = buttons.find((value) => value.includes(label));
      assert.ok(button, label);
      assert.match(button, /^<button\b[^>]*\bdisabled=""/);
    }
    const { default: App } = await vite.ssrLoadModule("/src/App.jsx");
    const app = renderToStaticMarkup(createElement(App));
    assert.match(app, /Checking your session/);
    assert.doesNotMatch(app, /Recent Inquiries|Continue as guest/);
  } finally {
    await vite.close();
  }
});
