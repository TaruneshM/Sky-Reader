import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("assistant and user messages and thinking indicator render image avatars with srcset", async () => {
  const vite = await createServer({
    appType: "custom",
    optimizeDeps: { noDiscovery: true, include: [] },
    server: { middlewareMode: true, ws: false, watch: null },
  });
  try {
    const { default: ChatMessage } = await vite.ssrLoadModule("/src/components/ChatMessage.jsx");
    const { default: ThinkingIndicator } = await vite.ssrLoadModule("/src/components/ThinkingIndicator.jsx");

    // 1. Assistant message renders bot avatar image with srcset
    const assistantHtml = renderToStaticMarkup(createElement(ChatMessage, {
      message: { id: "msg-1", sender: "assistant", text: "Current conditions are 22°C." },
    }));
    assert.match(assistantHtml, /class="message-avatar assistant-avatar"/);
    assert.match(assistantHtml, /<img\b[^>]*src="[^"]*bot-avatar\.png"[^>]*>/);
    assert.match(assistantHtml, /srcset="[^"]*bot-avatar\.png 1x,\s*[^"]*bot-avatar@2x\.png 2x"/i);

    // 2. User message renders user avatar image with srcset
    const userHtml = renderToStaticMarkup(createElement(ChatMessage, {
      message: { id: "msg-2", sender: "user", text: "What's the weather in Seattle?" },
    }));
    assert.match(userHtml, /class="message-avatar user-avatar"/);
    assert.match(userHtml, /<img\b[^>]*src="[^"]*user-avatar\.png"[^>]*>/);
    assert.match(userHtml, /srcset="[^"]*user-avatar\.png 1x,\s*[^"]*user-avatar@2x\.png 2x"/i);

    // 3. Thinking indicator renders the same bot avatar
    const thinkingHtml = renderToStaticMarkup(createElement(ThinkingIndicator));
    assert.match(thinkingHtml, /class="message-avatar assistant-avatar"/);
    assert.match(thinkingHtml, /<img\b[^>]*src="[^"]*bot-avatar\.png"[^>]*>/);
    assert.match(thinkingHtml, /srcset="[^"]*bot-avatar\.png 1x,\s*[^"]*bot-avatar@2x\.png 2x"/i);

    // 4. Verify required accessibility, sizing and loading attributes
    for (const html of [assistantHtml, userHtml, thinkingHtml]) {
      assert.match(html, /alt=""/);
      assert.match(html, /aria-hidden="true"/);
      assert.match(html, /loading="eager"/);
      assert.match(html, /draggable="false"/);
      assert.match(html, /width="40"/);
      assert.match(html, /height="40"/);
    }
  } finally {
    await vite.close();
  }
});
