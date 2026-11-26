// Render video scenes (HTML pages driven by window.seek) to frames with headless Chrome.
//   node video/render.mjs scene SCENE...          -> video/build/scenes/SCENE.mp4 (lossless-ish H.264)
//   node video/render.mjs stills SCENE t1,t2,...  -> video/build/stills/SCENE_t.png
// Called by video/make_video.py; needs ffmpeg and google-chrome.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launch } from "../scripts/cdp.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const BUILD = join(HERE, "build");
const FPS = 30;
const STAMP = Date.now().toString(36).slice(-5);   // unique still names (viewers cache by path)
const [mode, ...rest] = process.argv.slice(2);
if (!["scene", "stills"].includes(mode) || !rest.length) {
  console.error("error: usage: node video/render.mjs scene SCENE... | stills SCENE t1,t2,...");
  process.exit(2);
}

const errors = [];
async function open(browser, name) {
  const url = pathToFileURL(join(HERE, "scenes", `${name}.html`)).href;
  await browser.goto(url);
  await browser.evaluate("window.READY");
  const dur = await browser.evaluate("window.DURATION");
  if (!(dur > 0)) throw new Error(`${name}.html does not set window.DURATION: ${errors.join(' | ')}`);
  return dur;
}

async function shot(browser, format = "png") {
  const r = await browser.send("Page.captureScreenshot", { format, quality: format === "jpeg" ? 95 : undefined, optimizeForSpeed: true });
  return Buffer.from(r.data, "base64");
}

const browser = await launch({ width: 1920, height: 1080 });
browser.on("Runtime.exceptionThrown", (p) => errors.push(p.exceptionDetails?.exception?.description || p.exceptionDetails?.text));
try {
  if (mode === "stills") {
    const [name, times] = rest;
    mkdirSync(join(BUILD, "stills"), { recursive: true });
    await open(browser, name);
    for (const t of times.split(",").map(Number)) {
      await browser.evaluate(`window.seek(${t})`);
      const f = join(BUILD, "stills", `${name}_${t.toFixed(2)}_${STAMP}.png`);
      writeFileSync(f, await shot(browser));
      console.log(f);
    }
  } else {
    mkdirSync(join(BUILD, "scenes"), { recursive: true });
    for (const name of rest) {
      const dur = await open(browser, name);
      const n = Math.round(dur * FPS);
      const out = join(BUILD, "scenes", `${name}.mp4`);
      const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "8", "-pix_fmt", "yuv420p", "-r", String(FPS), out],
        { stdio: ["pipe", "inherit", "inherit"] });
      const done = new Promise((r, j) => ff.on("exit", (c) => (c === 0 ? r() : j(new Error(`ffmpeg exited ${c} for ${name}`)))));
      const t0 = Date.now();
      for (let i = 0; i < n; i++) {
        await browser.evaluate(`window.seek(${(i / FPS).toFixed(5)})`);
        const buf = await shot(browser);
        if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
        if (errors.length) throw new Error(`${name}: ${errors.join(" | ")}`);
      }
      ff.stdin.end();
      await done;
      console.log(`${name}: ${n} frames, ${dur}s, ${((Date.now() - t0) / 1000).toFixed(0)}s to render -> ${out}`);
    }
  }
  if (errors.length) throw new Error(errors.join(" | "));
} finally {
  await browser.close();
}
