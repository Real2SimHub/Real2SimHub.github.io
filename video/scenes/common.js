// Shared clock and helpers for the video scenes. Every scene is a pure function of time:
// window.seek(t) puts the page in its state at t seconds and resolves when the frame is ready.
// Nothing uses CSS transitions, CSS animations or requestAnimationFrame.
"use strict";
const FPS = 30;
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const ramp = (t, a, b) => clamp01((t - a) / (b - a));
const ease = {
  out: (x) => 1 - Math.pow(1 - x, 3),
  inOut: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  back: (x) => { const c = 1.4; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
};
const lerp = (a, b, k) => a + (b - a) * k;
/** Visibility envelope: rises over d after tin, falls over d before tout. */
function env(t, tin, tout, d = 0.45) {
  const a = tin === undefined ? 1 : ease.out(ramp(t, tin, tin + d));
  const b = tout === undefined ? 1 : 1 - ease.out(ramp(t, tout - d, tout));
  return a * b;
}

// Declarative timing: <el data-in="1.2" data-out="5" data-fx="up|down|fade|scale|left|right" data-d="0.45" data-dist="28">
function applyTimed(t) {
  document.querySelectorAll("[data-in],[data-out]").forEach((el) => {
    const tin = el.dataset.in !== undefined ? +el.dataset.in : undefined;
    const tout = el.dataset.out !== undefined ? +el.dataset.out : undefined;
    const d = +(el.dataset.d || 0.45);
    const k = env(t, tin, tout, d);
    const fx = el.dataset.fx || "up";
    const dist = +(el.dataset.dist || 28);
    const rise = tin === undefined ? 1 : ease.out(ramp(t, tin, tin + d));
    let tr = "";
    if (fx === "up") tr = `translateY(${(1 - rise) * dist}px)`;
    else if (fx === "down") tr = `translateY(${-(1 - rise) * dist}px)`;
    else if (fx === "left") tr = `translateX(${(1 - rise) * dist}px)`;
    else if (fx === "right") tr = `translateX(${-(1 - rise) * dist}px)`;
    else if (fx === "scale") tr = `scale(${lerp(0.9, 1, ease.back(rise))})`;
    el.style.opacity = k.toFixed(4);
    el.style.transform = (el.dataset.base || "") + " " + tr;
    el.style.visibility = k < 0.002 ? "hidden" : "visible";
  });
}

// The logo (inline SVG #logo): the ribbon is drawn from Real to Sim, the letters appear as it passes, the name follows.
function logoReveal(t, at) {
  const logo = document.getElementById("logo");
  if (!logo) return;
  const show = (id, tin, d) => {
    logo.querySelector(id).style.opacity = ease.out(ramp(t, tin, tin + d)).toFixed(4);
  };
  const k = ease.inOut(ramp(t, at, at + 1.2));
  logo.querySelector("#line").setAttribute("stroke-dashoffset", (1.01 * (1 - k)).toFixed(4));
  logo.querySelector("#ribbon").style.visibility = k > 0 ? "visible" : "hidden";
  show("#r", at + 0.3, 0.4);
  show("#s", at + 0.8, 0.4);
  show("#word", at + 0.9, 0.6);
}

// Clips: <img data-clip="name" data-at="2" data-from="0" data-rate="1" data-loop>
// Frames live in ../build/clips/<name>/NNNN.jpg; window.CLIPS (clips.js) gives each clip's frame count.
// A scene may set el.clipTime (seconds into the clip) in its scene(t) to take control.
function clipFrame(el, t) {
  const c = (window.CLIPS || {})[el.dataset.clip];
  if (!c) throw new Error(`clip ${el.dataset.clip} is missing; run video/make_video.py clips`);
  let ct;
  if (typeof el.clipTime === "number") ct = el.clipTime;
  else {
    const at = +(el.dataset.at || 0), from = +(el.dataset.from || 0), rate = +(el.dataset.rate || 1);
    ct = from + Math.max(0, t - at) * rate;
  }
  let f = Math.floor(ct * FPS + 1e-6);
  if (el.hasAttribute("data-loop")) f = ((f % c.n) + c.n) % c.n;
  f = Math.max(0, Math.min(c.n - 1, f));
  return `../build/clips/${el.dataset.clip}/${String(f + 1).padStart(4, "0")}.${c.ext || "jpg"}`;
}

async function updateClips(t) {
  const waits = [];
  document.querySelectorAll("img[data-clip]").forEach((el) => {
    const src = clipFrame(el, t);
    if (el.getAttribute("src") !== src) {
      el.setAttribute("src", src);
      waits.push(el.decode().catch(() => { throw new Error(`cannot load ${src}`); }));
    }
  });
  await Promise.all(waits);
}

/** Type out text: the first n characters of full, with a caret while typing. */
function typed(full, t, t0, cps) {
  const n = Math.max(0, Math.min(full.length, Math.floor((t - t0) * cps)));
  return full.slice(0, n);
}

window.seek = async function (t) {
  applyTimed(t);
  if (typeof window.scene === "function") window.scene(t);
  await updateClips(t);
};

// Ready once fonts and all static images are decoded.
window.READY = (async () => {
  await new Promise((r) => (document.readyState === "complete" ? r() : window.addEventListener("load", r)));
  await document.fonts.ready;
  await Promise.all([...document.images].filter((i) => !i.dataset.clip).map((i) => i.decode().catch(() => {
    throw new Error(`cannot load ${i.src}`);
  })));
  if (typeof window.setup === "function") await window.setup();
  await window.seek(0);
  return true;
})();
