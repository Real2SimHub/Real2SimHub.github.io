// A minimal Chrome DevTools Protocol client (Node 22+, no dependencies).
// launch() starts headless Chrome and returns a page session: send(method, params), on(event, fn), close().
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export async function launch({ width = 1920, height = 1080, scale = 1, args = [] } = {}) {
  const chrome = process.env.CHROME || "google-chrome";
  const profile = mkdtempSync(join(tmpdir(), "r2sh-chrome-"));
  const proc = spawn(chrome, [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
    "--no-first-run", "--no-default-browser-check", "--allow-file-access-from-files",
    "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
    "--font-render-hinting=none", `--user-data-dir=${profile}`, "--remote-debugging-port=0",
    `--window-size=${width},${height}`, ...args, "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  const wsUrl = await new Promise((resolve, reject) => {
    let buf = "";
    const timer = setTimeout(() => reject(new Error("Chrome did not start within 30 s")), 30000);
    proc.stderr.on("data", (d) => {
      buf += d.toString();
      const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) { clearTimeout(timer); resolve(m[1]); }
    });
    proc.on("exit", (c) => { clearTimeout(timer); reject(new Error(`Chrome exited (${c}): ${buf.slice(-400)}`)); });
  });
  const port = new URL(wsUrl).port;
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = list.find((t) => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });

  let id = 0;
  const pending = new Map();
  const handlers = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject, method } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(`${method}: ${msg.error.message}`));
      else resolve(msg.result);
    } else if (msg.method && handlers.has(msg.method)) {
      for (const fn of handlers.get(msg.method)) fn(msg.params);
    }
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id;
    pending.set(n, { resolve, reject, method });
    ws.send(JSON.stringify({ id: n, method, params }));
  });
  const on = (event, fn) => {
    if (!handlers.has(event)) handlers.set(event, []);
    handlers.get(event).push(fn);
  };
  const once = (event) => new Promise((r) => {
    const fn = (p) => { handlers.set(event, handlers.get(event).filter((f) => f !== fn)); r(p); };
    on(event, fn);
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: scale, mobile: false });

  async function goto(url, { timeout = 30000 } = {}) {
    const loaded = once("Page.loadEventFired");
    await send("Page.navigate", { url });
    await Promise.race([loaded, new Promise((_, j) => setTimeout(() => j(new Error(`timeout loading ${url}`)), timeout))]);
  }
  async function evaluate(expression) {
    const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(`page error: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
    return r.result.value;
  }
  async function close() {
    try { ws.close(); } catch { /* already closed */ }
    proc.kill("SIGKILL");
    await new Promise((r) => setTimeout(r, 200));
    rmSync(profile, { recursive: true, force: true });
  }
  return { send, on, once, goto, evaluate, close };
}
