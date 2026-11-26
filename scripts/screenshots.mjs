// Full-page screenshots of every page at 1440 px and 390 px, light and dark, plus checks:
// JavaScript errors, failed requests, horizontal overflow, images without alt text.
//   node scripts/screenshots.mjs OUT_DIR [--proxy http://127.0.0.1:7897]
// Serves the site with `python3 -m http.server` on a free port. Exits 1 if a check fails.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { launch } from "./cdp.mjs";

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = process.argv[2];
if (!out) { console.error("error: no output directory\n  fix: node scripts/screenshots.mjs OUT_DIR"); process.exit(2); }
const pi = process.argv.indexOf("--proxy");
const proxy = pi > 0 ? process.argv[pi + 1] : null;
mkdirSync(out, { recursive: true });

const port = await new Promise((r) => { const s = createServer(); s.listen(0, () => { const p = s.address().port; s.close(() => r(p)); }); });
const server = spawn("python3", ["-m", "http.server", String(port), "--bind", "127.0.0.1"], { cwd: SITE, stdio: "ignore" });
await new Promise((r) => setTimeout(r, 800));

const pages = [["home", "/"], ["real2simlab", "/real2simlab/"], ["awesome", "/awesome-real2sim/"],
  ["blog", "/blog/"], ["blog-4dcodebench", "/blog/4dcodebench/"], ["blog-video2world", "/blog/video2world/"],
  ["blog-physics-iq", "/blog/physics-iq/"], ["blog-iris", "/blog/iris/"], ["blog-physcodegym", "/blog/physcodegym/"],
  ["blog-physimcode", "/blog/physimcode/"], ["blog-agentic-real2sim", "/blog/agentic-real2sim/"],
  ["blog-3dcodeverse", "/blog/3dcodeverse/"], ["404", "/404.html"]];
const args = proxy ? [`--proxy-server=${proxy}`, "--proxy-bypass-list=127.0.0.1;localhost"] : [];
const problems = [];
const browser = await launch({ width: 1440, height: 900, args });
const errors = [];
browser.on("Runtime.exceptionThrown", (p) => errors.push(p.exceptionDetails?.exception?.description || p.exceptionDetails?.text));
browser.on("Runtime.consoleAPICalled", (p) => { if (p.type === "error") errors.push(p.args.map((a) => a.value ?? a.description).join(" ")); });
await browser.send("Log.enable");
browser.on("Log.entryAdded", (p) => { if (p.entry.level === "error") errors.push(`${p.entry.text} ${p.entry.url || ""}`); });
await browser.send("Network.enable");
const failed = [];
browser.on("Network.loadingFailed", (p) => { if (!p.canceled) failed.push(p.errorText + " " + (p.requestId || "")); });
browser.on("Network.responseReceived", (p) => { if (p.response.status >= 400 && !p.response.url.endsWith("/404.html")) failed.push(`${p.response.status} ${p.response.url}`); });

for (const [name, path] of pages) {
  for (const width of [1440, 390]) {
    for (const theme of ["light", "dark"]) {
      errors.length = 0; failed.length = 0;
      await browser.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: theme }] });
      await browser.send("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: width < 500 });
      await browser.goto(`http://127.0.0.1:${port}${path}`);
      const info = await browser.evaluate(`(async () => {
        await document.fonts.ready;
        document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager');
        await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
        await new Promise(r => setTimeout(r, 300));
        const W = document.documentElement.clientWidth;
        const wide = [...document.querySelectorAll('body *')].filter(e => {
          const r = e.getBoundingClientRect(); if (!r.width) return false;
          let p = e.parentElement; while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return false; p = p.parentElement; }
          return r.right > W + 1 || r.left < -1;
        }).map(e => e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : '')).slice(0, 8);
        return {
          height: Math.ceil(document.documentElement.scrollHeight),
          overflow: document.documentElement.scrollWidth > W, wide,
          noAlt: [...document.images].filter(i => !i.hasAttribute('alt')).map(i => i.src),
          broken: [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.currentSrc || i.src),
          fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight).filter((v, i, a) => a.indexOf(v) === i).join(', '),
        };
      })()`);
      await browser.send("Emulation.setDeviceMetricsOverride", { width, height: Math.min(info.height, 16000), deviceScaleFactor: 1, mobile: width < 500 });
      await new Promise((r) => setTimeout(r, 400));
      const shot = await browser.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      const file = join(out, `${name}-${width}-${theme}.png`);
      writeFileSync(file, Buffer.from(shot.data, "base64"));
      const bad = [];
      if (info.overflow || info.wide.length) bad.push(`horizontal overflow: ${info.wide.join(", ")}`);
      if (info.noAlt.length) bad.push(`images without alt: ${info.noAlt.join(", ")}`);
      if (info.broken.length) bad.push(`broken images: ${info.broken.join(", ")}`);
      if (errors.length) bad.push(`console errors: ${errors.join(" | ")}`);
      if (failed.length) bad.push(`failed requests: ${failed.join(" | ")}`);
      console.log(`${bad.length ? "FAIL" : "ok  "} ${file} (${info.height}px)${bad.length ? "\n     " + bad.join("\n     ") : ""}`);
      if (bad.length) problems.push(file);
      if (name === "home" && width === 1440 && theme === "light") console.log(`     fonts: ${info.fonts || "none loaded"}`);
    }
  }
}
await browser.close();
server.kill();
writeFileSync(join(out, "checks.txt"), problems.length ? problems.join("\n") + "\n" : "all ok\n");
process.exit(problems.length ? 1 : 0);
