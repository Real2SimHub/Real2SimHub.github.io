/* Real2SimHub: theme toggle, research filters, copy buttons, the moving logos, the blog row and the
   WeChat codes. No dependencies. */
(function () {
  "use strict";
  var root = document.documentElement;
  var KEY = "r2sh-theme";
  var media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function store(t) {
    try { localStorage.setItem(KEY, t); } catch (e) { /* private mode: the choice lasts for this page */ }
  }
  function effective() {
    var t = root.getAttribute("data-theme");
    if (t === "light" || t === "dark") return t;
    return media && media.matches ? "dark" : "light";
  }

  /* <picture> sources marked data-dark follow the toggle, not only the system setting. */
  function syncPictures() {
    var t = root.getAttribute("data-theme");
    var q = t === "dark" ? "all" : t === "light" ? "not all" : "(prefers-color-scheme: dark)";
    var list = document.querySelectorAll("source[data-dark]");
    for (var i = 0; i < list.length; i++) {
      var extra = list[i].getAttribute("data-media");   // e.g. phones only
      var m = !extra ? q : q === "all" ? extra : q === "not all" ? q : extra + " and " + q;
      if (list[i].media !== m) list[i].media = m;
    }
  }

  function syncButton() {
    var b = document.querySelector(".theme-toggle");
    if (!b) return;
    var dark = effective() === "dark";
    b.setAttribute("aria-pressed", dark ? "true" : "false");
    b.setAttribute("aria-label", dark ? "Dark theme on. Switch to light theme" : "Light theme on. Switch to dark theme");
    b.title = dark ? "Switch to light theme" : "Switch to dark theme";
  }

  var initial = stored();
  if (initial === "light" || initial === "dark") root.setAttribute("data-theme", initial);
  syncPictures();
  syncButton();

  var toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = effective() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      store(next);
      syncPictures();
      syncButton();
    });
  }
  if (media) {
    var onChange = function () { syncButton(); };
    if (media.addEventListener) media.addEventListener("change", onChange);
    else if (media.addListener) media.addListener(onChange);
  }

  /* Research list filters. */
  var bar = document.querySelector("[data-filters]");
  if (bar) {
    var buttons = bar.querySelectorAll("button[data-filter]");
    var rows = document.querySelectorAll("[data-type]");
    var count = document.querySelector("[data-count]");
    var apply = function (f) {
      var shown = 0;
      for (var i = 0; i < rows.length; i++) {
        var on = f === "all" || rows[i].getAttribute("data-type") === f;
        rows[i].hidden = !on;
        if (on) shown++;
      }
      for (var j = 0; j < buttons.length; j++) {
        buttons[j].setAttribute("aria-pressed", buttons[j].getAttribute("data-filter") === f ? "true" : "false");
      }
      if (count) count.textContent = "Showing " + shown + " of " + rows.length;
    };
    for (var k = 0; k < buttons.length; k++) {
      buttons[k].addEventListener("click", function (ev) {
        apply(ev.currentTarget.getAttribute("data-filter"));
      });
    }
    /* Left and right arrows move between filters, as in a toolbar. */
    bar.addEventListener("keydown", function (ev) {
      if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
      var list = Array.prototype.slice.call(buttons);
      var i = list.indexOf(document.activeElement);
      if (i < 0) return;
      ev.preventDefault();
      var n = (i + (ev.key === "ArrowRight" ? 1 : -1) + list.length) % list.length;
      list[n].focus();
    });
    apply("all");
  }

  /* Copy buttons for commands and BibTeX. */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy") ? resolve() : reject(new Error("copy failed")); }
      catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }
  var copies = document.querySelectorAll("button.copy[data-copy], button.mail-copy[data-copy]");
  for (var c = 0; c < copies.length; c++) {
    copies[c].addEventListener("click", function (ev) {
      var btn = ev.currentTarget;
      var target = document.getElementById(btn.getAttribute("data-copy"));
      if (!target) return;
      var label = btn.querySelector("span");
      var text = target.getAttribute("data-text") || target.textContent;
      copyText(text).then(function () {
        btn.classList.add("done");
        setTimeout(function () { btn.classList.remove("done"); }, 1800);
        if (label) label.textContent = "Copied";
      }, function () {
        if (label) label.textContent = "Select and copy";
      });
      setTimeout(function () { if (label) label.textContent = "Copy"; }, 1800);
    });
  }
  /* The moving logos: a button pauses and resumes them. */
  var marquee = document.querySelector("[data-marquee]");
  if (marquee) {
    var mt = marquee.querySelector(".marquee-toggle");
    if (mt) {
      mt.addEventListener("click", function () {
        var paused = marquee.classList.toggle("paused");
        mt.setAttribute("aria-pressed", paused ? "true" : "false");
        mt.setAttribute("aria-label", paused ? "Play the moving logos" : "Pause the moving logos");
      });
    }
  }

  /* WeChat codes open in a dialog; without it (or without JavaScript) the link opens the image. */
  var dialog = document.querySelector(".qr-dialog");
  if (dialog && typeof dialog.showModal === "function") {
    var qrs = document.querySelectorAll("a[data-qr]");
    for (var w = 0; w < qrs.length; w++) {
      qrs[w].addEventListener("click", function (ev) {
        ev.preventDefault();
        var a = ev.currentTarget;
        var title = a.getAttribute("data-qr-title") || "";
        dialog.querySelector(".qr-title").textContent = title;
        var slot = dialog.querySelector(".qr-img");
        var img = slot.querySelector("img") || slot.appendChild(document.createElement("img"));
        img.src = a.getAttribute("href");
        img.alt = "WeChat QR code: " + title;
        dialog.showModal();
      });
    }
    dialog.addEventListener("click", function (ev) {
      if (ev.target === dialog) dialog.close();
    });
  }
})();
