import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { Buffer } from "node:buffer";
import process from "node:process";

const OUT_DIR = resolve("/home/victus/.gemini/antigravity/brain/2737cad0-e367-41d0-a8c1-1150a2500d65/screenshots");
mkdirSync(OUT_DIR, { recursive: true });

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.id && this.pending.has(data.id)) {
        const { resolve, reject } = this.pending.get(data.id);
        this.pending.delete(data.id);
        if (data.error) reject(new Error(data.error.message));
        else resolve(data.result);
      }
    };
  }

  async ready() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    return new Promise((res, rej) => {
      this.ws.onopen = res;
      this.ws.onerror = rej;
    });
  }

  async send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.ws.close();
  }
}

async function captureMoment(width, height, isMobile, waitAfterLoadMs, filename) {
  console.log(`Capturing ${filename} (${width}x${height}, wait: ${waitAfterLoadMs}ms)...`);
  const tmpDir = `/tmp/chrome-test-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const chrome = spawn("/usr/bin/google-chrome", [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    `--remote-debugging-port=9222`,
    `--user-data-dir=${tmpDir}`,
    `--window-size=${width},${height}`,
    "about:blank",
  ]);

  try {
    let versionData = null;
    for (let i = 0; i < 30; i++) {
      await sleep(200);
      try {
        const res = await fetch("http://127.0.0.1:9222/json/version");
        if (res.ok) {
          versionData = await res.json();
          break;
        }
      } catch {
        // Retry
      }
    }

    if (!versionData) throw new Error("Could not connect to Chrome debugging port");

    const client = new CDPClient(versionData.webSocketDebuggerUrl);
    await client.ready();

    const { targetId } = await client.send("Target.createTarget", { url: "about:blank" });
    const targetWsUrl = `ws://127.0.0.1:9222/devtools/page/${targetId}`;
    const pageClient = new CDPClient(targetWsUrl);
    await pageClient.ready();

    await pageClient.send("Page.enable");
    await pageClient.send("Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 2,
      mobile: isMobile,
    });

    await pageClient.send("Page.navigate", { url: "http://127.0.0.1:5173/login" });
    // Wait for exact in-animation timing
    await sleep(waitAfterLoadMs);

    const snap = await pageClient.send("Page.captureScreenshot", { format: "png" });
    writeFileSync(resolve(OUT_DIR, filename), Buffer.from(snap.data, "base64"));
    console.log(`Saved ${filename}`);

    pageClient.close();
    client.close();
  } finally {
    chrome.kill("SIGKILL");
  }
}

async function main() {
  // Desktop moments
  await captureMoment(1440, 900, false, 3300, "desktop-03b-stage3-3.3s-wordmark.png");
  console.log("Desktop 3.3s captured!");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
