#!/usr/bin/env python3
"""Build the Real2SimHub video: 1920x1080, 30 fps, AAC stereo 48 kHz, with +faststart, in two encodings.

The page offers AV1 first (real2simhub-av1.mp4, about half the size) and H.264 as the fallback
(real2simhub.mp4) for browsers without AV1. Both are encoded from one lossless master and were checked
with VMAF against it: each scores at least as high as the earlier H.264 (preset slow, CRF 21), overall
and in every part of the video, so the smaller files cost no picture quality.

    python video/narrate.py                # first, with a Python that has kokoro: the narration lines
    python3 video/make_video.py            # clips, render, assemble (with the sound), poster
    python3 video/make_video.py fetch      # download the Wikimedia Commons recordings and the music
    python3 video/make_video.py clips      # extract the clip frames into video/build/clips
    python3 video/make_video.py render [SCENE ...]   # render scenes (all by default)
    python3 video/make_video.py assemble   # join scenes with cross-fades, mix the sound, write the poster
    python3 video/make_video.py stills SCENE t1,t2   # preview frames of one scene

The sound: the narration (narration.json, synthesised locally by narrate.py with Kokoro-82M, Apache-2.0),
each line placed at its time in its scene, over the music of music.json ("Supernova" by Scott Buckley, CC BY 4.0,
credited in the README), edited to the video on its beat grid and ducked under the voice (see mix()), with lighter
drums and bass and smaller swings in the middle of the video (music.json `calm`). The mix without that change is normalised to
-15 LUFS, so the opening and the ending keep their level.

Each scene is an HTML page in video/scenes/ that sets window.DURATION and window.seek(t); the
renderer (render.mjs) steps its clock frame by frame in headless Chrome and captures every frame.
The recording and the simulation in s03_how come from a local run of the Codex agent made with
Real2SimLab (set R2S_RUNS to that run): PhysCodeGym's clip of a Physics-IQ take (CC-BY-4.0). 4DCodeBench declares no license: never take a frame of it.
The wall of real recordings (s01_open) is listed in real_clips.json with each one's credit and license:
Wikimedia Commons files (CC0 or CC BY only) are downloaded into R2S_COMMONS; Physics-IQ and DROID come
from the Lab's data cache (R2S_DATA). Each gets two frame sets: the recording (r_NAME) and the same
frames shrunk to 32x18 (b_NAME), which the scene draws as building blocks.
Needs ffmpeg/ffprobe, node 22+, google-chrome and the Noto Sans fonts.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
BUILD = HERE / "build"
OUT = SITE / "assets" / "video" / "real2simhub.mp4"            # H.264, the fallback
OUT_AV1 = SITE / "assets" / "video" / "real2simhub-av1.mp4"    # AV1, offered first
MASTER = BUILD / "master.mkv"                                  # lossless video + PCM sound
POSTER = SITE / "assets" / "video" / "real2simhub-poster.jpg"
RUNS = Path(os.environ.get("R2S_RUNS", "<unset: R2S_RUNS>"))
DATA = Path(os.environ.get("R2S_DATA", "<unset: R2S_DATA>"))
COMMONS = Path(os.environ.get("R2S_COMMONS", "<unset: R2S_COMMONS>"))
WALL = json.loads((HERE / "real_clips.json").read_text())["clips"]
NARRATION = json.loads((HERE / "narration.json").read_text())
MUSIC = json.loads((HERE / "music.json").read_text())
VOICE = BUILD / "voice"
AUDIO = BUILD / "audio.wav"
SR = 48000
LOUDNESS = -15.0        # LUFS, integrated, of the final mix
MUSIC_GAP = 0.0         # dB: the music's loudness relative to the voice, between lines
DUCK_HIGH = -11.0       # dB: the music above 200 Hz while a line is spoken (where the voice is)
DUCK_LOW = -5.0         # dB: its bass and kick while a line is spoken, so the beat carries on
HOLD = 0.7              # s: a pause in the narration shorter than this keeps the music down
WALL_SECONDS = 8  # frames taken from each recording; the scene needs at least WALL_MIN seconds
WALL_MIN = 7
FPS = 30
XFADE = 0.5

# Scenes in order, with the transition into the next one.
SCENES = [
    ("s01_open", "fade"),
    ("s02_contrib", "fade"),
    ("s03_how", "fade"),
    ("s05_platform", "fade"),
    ("s06_fair", "fade"),
    ("s07_command", "fade"),
    ("s08_awesome", "fade"),
    ("s09_close", None),
]


PCG = "physics_iq_0001_ball_and_block_fall"
# name: (source, width, height). Every clip is resampled to 30 fps.
CLIPS = {
    "pcg_real": (RUNS / f"tasks/physcodegym/{PCG}/rerun/visible/cam/rgb.mp4", 1920, 1080),
    "pcg_sim": (RUNS / f"runs/physcodegym__{PCG}__rerun/codex/trial-0/seed-0/rerun/output/render.mp4", 1920, 1080),
}


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(f"error: command failed ({r.returncode}): {' '.join(map(str, cmd[:6]))} ...")
    return r


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"error: cannot read {path}\n  fix: python3 video/make_video.py render")
    return float(r.stdout)


def fetch() -> None:
    import urllib.request

    if not COMMONS.is_dir():
        sys.exit(f"error: R2S_COMMONS is not a directory: {COMMONS}\n  fix: export R2S_COMMONS=/some/cache/dir")
    music = {"name": MUSIC["file"], "url": MUSIC["url"], "license": MUSIC["license"], "file": MUSIC["file"]}
    for c in [*WALL, music]:
        if "url" not in c:
            continue
        dest = COMMONS / c.get("file", f"{c['name']}.webm")
        if dest.exists() and dest.stat().st_size > 0:
            continue
        req = urllib.request.Request(c["url"], headers={"User-Agent": "real2simhub-video/1.0"})
        tmp = dest.with_suffix(".part")
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.replace(dest)
        print(f"fetched {dest.name} ({c['license']})")
    music_file()


def music_file() -> Path:
    import hashlib

    path = COMMONS / MUSIC["file"]
    if not path.exists():
        sys.exit(f"error: the music is missing: {path}\n  fix: python3 video/make_video.py fetch")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != MUSIC["sha256"]:
        sys.exit(f"error: {path} is not the file of music.json (sha256 {digest[:12]})\n  fix: delete it and fetch again")
    return path


def decode(path: Path, channels: int, seconds: float | None = None, start: float = 0.0) -> "np.ndarray":
    import numpy as np

    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(path)]
    if seconds is not None:
        cmd += ["-t", f"{seconds:.3f}"]
    raw = run([*cmd, "-f", "f32le", "-ac", str(channels), "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, channels).astype(np.float64)


def write_wav(x: "np.ndarray", path: Path) -> None:
    """32-bit float, so peaks above full scale reach the limiter in assemble() instead of being clipped."""
    import numpy as np

    run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", str(x.shape[1]), "-i", "-",
         "-c:a", "pcm_f32le", str(path)],
        input=np.ascontiguousarray(x, dtype=np.float32).tobytes())


def lufs(x: "np.ndarray") -> float:
    """Integrated loudness (EBU R128) of a signal, measured by ffmpeg."""
    import re
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "x.wav"
        write_wav(x, path)
        r = run(["ffmpeg", "-v", "info", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    if not m:
        sys.exit("error: cannot measure the loudness (ffmpeg ebur128)")
    return float(m[-1])


def music_track(total: float) -> "np.ndarray":
    """The music edited to the video (music.json `edit`): each piece from its `from` in the track, starting at its
    `at` in the video, at its `gain` (dB), joined on the beat with a cross-fade just before the beat (its `fade`, 12 ms
    by default; longer where the music changes character), faded out over the last `end_fade` seconds of the video."""
    import numpy as np

    track = decode(music_file(), 2)
    n = round(total * SR)
    out = np.zeros((n, 2))
    edit = MUSIC["edit"]
    fades = [round(piece.get("fade", 0.012) * SR) for piece in edit]
    lead = round(0.004 * SR)                   # the cross-fade ends this long before the bar line
    for i, piece in enumerate(edit):
        at, src = round(piece["at"] * SR), round(piece["from"] * SR)
        stop = round(edit[i + 1]["at"] * SR) if i + 1 < len(edit) else n
        fade = fades[i]
        a0, s0 = max(at - fade - lead, 0), src - (at - max(at - fade - lead, 0))
        if s0 < 0 or src >= len(track):
            sys.exit(f"error: music.json edit {i} starts outside the track")
        seg = track[s0:s0 + (stop - a0)]
        w = np.ones(len(seg))
        if i > 0:                                # fade in over the cross-fade, under the end of the last piece
            k = min(fade, len(w))
            w[:k] = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
        if i + 1 < len(edit):                    # fade out where the next piece fades in
            out_fade = fades[i + 1]
            w[-(out_fade + lead):-lead] = np.cos(np.linspace(0, np.pi / 2, out_fade)) ** 2
            w[-lead:] = 0.0
        out[a0:a0 + len(seg)] += seg * (w * 10 ** (piece.get("gain", 0.0) / 20))[:, None]
    k = round(MUSIC.get("end_fade", 0.0) * SR)
    if k:
        out[-k:] *= (np.cos(np.linspace(0, np.pi / 2, k)) ** 2)[:, None]
    return out


def split_bands(x: "np.ndarray", hz: float = 200.0) -> tuple["np.ndarray", "np.ndarray"]:
    """A linear-phase split at `hz` (a raised-cosine crossover an octave wide): low + high == x."""
    import numpy as np

    spec = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    lo, hi = hz / np.sqrt(2), hz * np.sqrt(2)
    h = np.clip((np.log2(hi) - np.log2(np.maximum(f, 1e-9))) / (np.log2(hi) - np.log2(lo)), 0, 1)
    h = np.sin(h * np.pi / 2) ** 2
    low = np.fft.irfft(spec * h[:, None], n=len(x), axis=0)
    return low, x - low


def percussive(x: "np.ndarray", n_fft: int = 2048, hop: int = 512, width: int = 17) -> "np.ndarray":
    """The percussive part of `x` (drums and other hits), by median-filtering harmonic-percussive separation: a soft
    mask from the spectrum median-filtered across time (the tonal part) and across frequency (the hits). x minus it is
    the tonal part, so lowering only this keeps the melody."""
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view

    win = np.hanning(n_fft + 1)[:-1].astype(np.float32)
    pad = np.pad(x, ((n_fft, n_fft), (0, 0)))
    frames = sliding_window_view(pad, n_fft, axis=0)[::hop]          # (T, channels, n_fft)
    spec = np.fft.rfft(frames * win, axis=-1)                         # (T, channels, F)
    mag = np.abs(spec).mean(axis=1).T.astype(np.float32)              # (F, T), one mask for both channels
    half = width // 2

    def median(a: "np.ndarray", axis: int) -> "np.ndarray":
        out = np.empty_like(a)
        if axis == 1:                                                 # across time, in chunks of rows
            padded = np.pad(a, ((0, 0), (half, half)), mode="edge")
            for r in range(0, a.shape[0], 64):
                out[r:r + 64] = np.median(sliding_window_view(padded[r:r + 64], width, axis=1), axis=-1)
        else:                                                         # across frequency, in chunks of columns
            padded = np.pad(a, ((half, half), (0, 0)), mode="edge")
            for c in range(0, a.shape[1], 512):
                out[:, c:c + 512] = np.median(sliding_window_view(padded[:, c:c + 512], width, axis=0), axis=-1)
        return out

    tonal, hits = median(mag, 1) ** 2, median(mag, 0) ** 2
    mask = (hits / (tonal + hits + 1e-12)).T                          # (T, F)
    frames = np.fft.irfft(spec * mask[:, None, :], n=n_fft, axis=-1) * win
    out = np.zeros_like(pad)
    norm = np.zeros(len(pad))
    for i in range(frames.shape[0]):
        out[i * hop:i * hop + n_fft] += frames[i].T
        norm[i * hop:i * hop + n_fft] += win ** 2
    return (out / np.maximum(norm, 1e-6)[:, None])[n_fft:n_fft + len(x)]


def mix(starts: dict[str, float], total: float) -> None:
    """The narration at its times over the edited music -> build/audio.wav (stereo, 48 kHz).

    The music is there from the first frame. Between lines it is as loud as the voice (MUSIC_GAP); while a line is
    spoken it goes down, its mids and highs (DUCK_HIGH, where the voice is) more than its bass and kick (DUCK_LOW), so
    the beat carries on under the words. A pause shorter than HOLD keeps it down, so it never pumps between phrases.
    Over the calm span (music.json `calm`) the drums and the bass (below 200 Hz, `bass_db`) are lower, so the music under
    the words is light rather than boomy, and it comes back less between lines. Loudness
    is measured outside the calm span only, so whatever changes inside it, the opening and the ending keep their level."""
    import numpy as np

    n = round(total * SR)
    voice = np.zeros((n, 2))             # the same in both channels, so both are measured alike
    said: dict[str, tuple[int, int]] = {}  # line id -> its first and last spoken sample
    for line in NARRATION["lines"]:
        path = VOICE / f"{line['id']}.wav"
        if not path.exists():
            sys.exit(f"error: narration line {line['id']} is missing: {path}\n  fix: python video/narrate.py")
        if line["scene"] not in starts:
            sys.exit(f"error: narration line {line['id']} names an unknown scene {line['scene']!r}")
        x = decode(path, 1)[:, 0]
        lead = int(np.argmax(np.abs(x) > 0.01))          # the silence before the first word
        at = round((starts[line["scene"]] + line["at"]) * SR) - lead
        if at < 0 or at + len(x) > n:
            sys.exit(f"error: narration line {line['id']} does not fit in the video\n  fix: change its 'at' in narration.json")
        voice[at:at + len(x)] += x[:, None]
        spoken = np.flatnonzero(np.abs(x) > 0.01)
        said[line["id"]] = (at + spoken[0], at + spoken[-1])
    calm = MUSIC.get("calm")
    if calm and not {calm["from"], calm["to"]} <= set(said):
        sys.exit(f"error: music.json calm names a narration line that does not exist: {calm['from']}, {calm['to']}")
    # The calm span: 1 from the first word of calm["from"] to the last of calm["to"], ramped over calm["fade"] outside.
    weight = np.zeros(n)
    if calm:
        a, b, f = said[calm["from"]][0], said[calm["to"]][1], round(calm["fade"] * SR)
        t = np.arange(n)
        weight = np.sin(np.clip(np.minimum((t - (a - f)) / f, ((b + f) - t) / f), 0, 1) * np.pi / 2) ** 2
    outside = weight == 0
    voice *= 10 ** ((LOUDNESS - lufs(voice)) / 20)
    music = music_track(total)
    playing = np.abs(music).max(axis=1) > 0
    music *= 10 ** ((LOUDNESS + MUSIC_GAP - lufs(music[playing & outside])) / 20)
    # Where a line is spoken: 10 ms blocks, from 0.2 s before its first word to 0.15 s after its last, with pauses
    # shorter than HOLD filled in.
    hop = SR // 100
    blocks = np.sqrt(np.mean(voice[: n // hop * hop, 0].reshape(-1, hop) ** 2, axis=1))
    speaking = blocks > 0.02 * blocks.max()
    idx = np.flatnonzero(speaking)
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= round(HOLD * 100):
            speaking[a:b] = True
    near = speaking.copy()
    for k in range(1, 21):
        near[:-k] |= speaking[k:]                         # 0.2 s before
    for k in range(1, 16):
        near[k:] |= speaking[:-k]                         # 0.15 s after
    if calm:
        drums = 1 - 10 ** (calm["drums_db"] / 20)
        calmed = music - percussive(music) * (drums * weight)[:, None]
    else:
        calmed = music
    blocks_weight = np.interp(np.arange(len(near)) * hop + hop / 2, np.arange(n), weight)
    between = blocks_weight * (calm["between_lines_db"] if calm else 0.0)
    bass = blocks_weight * (calm.get("bass_db", 0.0) if calm else 0.0)   # always, so the music stays light, not boomy
    start = np.clip(np.arange(n) / (0.02 * SR), 0, 1)     # 20 ms, only against a click

    def ducked(m: "np.ndarray", rest: "np.ndarray", low_extra: "np.ndarray") -> "np.ndarray":
        out = voice.copy()
        for band, duck, extra in zip(split_bands(m), (DUCK_LOW, DUCK_HIGH), (low_extra, 0.0)):
            target = np.where(near, duck, rest) + extra
            gain = np.empty_like(target)
            g = 0.0
            for i, t in enumerate(target):
                g += (t - g) * (0.3 if t < g else 0.06)  # down in ~30 ms, back up in ~0.2 s
                gain[i] = g
            # per sample, between the blocks' centres, so the gain never steps
            gain = 10 ** (np.interp(np.arange(n), np.arange(len(gain)) * hop + hop / 2, gain) / 20)
            out += band * gain[:, None]
        return out * start[:, None]

    zero = np.zeros(len(near))
    scale = 10 ** ((LOUDNESS - lufs(ducked(music, zero, zero)[outside])) / 20)
    out = ducked(calmed, between, bass) * scale
    write_wav(out, AUDIO)
    if os.environ.get("R2S_STEMS"):                       # to check the balance: the two parts, as mixed
        write_wav(voice * start[:, None] * scale, BUILD / "stem-voice.wav")
        write_wav(out - voice * start[:, None] * scale, BUILD / "stem-music.wav")
    print(f"{AUDIO.relative_to(SITE)}: {total:.2f} s, peak {20 * np.log10(np.abs(out).max()):.1f} dBFS")


def wall_sources(c: dict) -> tuple[list[str], str]:
    """ffmpeg inputs and the filter that joins them, for one recording of the wall."""
    if "url" in c:
        src = COMMONS / f"{c['name']}.webm"
        if not src.exists():
            sys.exit(f"error: {src} is missing\n  fix: python3 video/make_video.py fetch")
        return ["-ss", str(c.get("start", 0)), "-i", str(src)], "[0:v]"
    paths = [DATA / d for d in c["data"]]
    for p in paths:
        if not p.exists():
            sys.exit(f"error: {p} is missing\n  fix: set R2S_DATA to the Lab's data cache (see the docstring)")
    args = [a for p in paths for a in ("-i", str(p))]
    if len(paths) == 1:
        return args, "[0:v]"
    joined = "".join(f"[{i}:v]" for i in range(len(paths)))
    return args, f"{joined}concat=n={len(paths)}:v=1:a=0,"


def wall_clips(counts: dict) -> None:
    for c in WALL:
        args, head = wall_sources(c)
        steps = [f"crop={c['crop']}"] if "crop" in c else []
        steps.append("minterpolate=fps=30:mi_mode=mci" if c.get("interpolate") else f"fps={FPS}")
        steps.append("scale=384:216:force_original_aspect_ratio=increase:flags=lanczos,crop=384:216,setsar=1")
        real, blocks = BUILD / "clips" / f"r_{c['name']}", BUILD / "clips" / f"b_{c['name']}"
        for d in (real, blocks):
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
        run(["ffmpeg", "-v", "error", *args, "-filter_complex", f"{head}{','.join(steps)}[v]", "-map", "[v]",
             "-t", str(WALL_SECONDS), "-q:v", "3", str(real / "%04d.jpg")])
        run(["ffmpeg", "-v", "error", "-i", str(real / "%04d.jpg"), "-vf", "scale=32:18:flags=area",
             str(blocks / "%04d.png")])
        n = len(list(real.glob("*.jpg")))
        if n < WALL_MIN * FPS:
            sys.exit(f"error: {c['name']} gave {n} frames, fewer than {WALL_MIN} s\n  fix: lower its start in real_clips.json")
        counts[f"r_{c['name']}"] = {"n": n, "w": 384, "h": 216}
        counts[f"b_{c['name']}"] = {"n": n, "w": 32, "h": 18, "ext": "png"}
        print(f"wall {c['name']}: {n} frames")


def clips() -> None:
    counts = {}
    for name, (src, w, h) in CLIPS.items():
        if not src.exists():
            sys.exit(f"error: clip {name} not found at {src}\n  fix: set R2S_RUNS (see the docstring)")
        d = BUILD / "clips" / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        sharpen = ",unsharp=5:5:0.6" if w >= 1280 else ""
        run(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps={FPS},scale={w}:{h}:flags=lanczos{sharpen}",
             "-q:v", "2", str(d / "%04d.jpg")])
        counts[name] = {"n": len(list(d.glob("*.jpg"))), "w": w, "h": h}
        print(f"clip {name}: {counts[name]['n']} frames from {src.name}")
    wall_clips(counts)
    (BUILD / "clips" / "clips.js").write_text("window.CLIPS = " + json.dumps(counts, indent=1) + ";\n")


def render(names: list[str]) -> None:
    names = names or [s for s, _ in SCENES]
    unknown = [n for n in names if n not in dict(SCENES)]
    if unknown:
        sys.exit(f"error: unknown scene {unknown}; scenes: {', '.join(s for s, _ in SCENES)}")
    if not (BUILD / "clips" / "clips.js").exists():
        sys.exit("error: clip frames are missing\n  fix: python3 video/make_video.py clips")
    run(["node", str(HERE / "render.mjs"), "scene", *names])


def assemble() -> None:
    encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    if "libsvtav1" not in encoders:
        sys.exit("error: this ffmpeg has no libsvtav1 (AV1) encoder\n"
                 "  fix: install an ffmpeg built with SVT-AV1 (Ubuntu 24.04's ffmpeg package has it)")
    files = [BUILD / "scenes" / f"{s}.mp4" for s, _ in SCENES]
    for f in files:
        if not f.exists():
            sys.exit(f"error: {f.name} is missing\n  fix: python3 video/make_video.py render {f.stem}")
    durs = [duration(f) for f in files]
    inputs: list[str] = []
    for f in files:
        inputs += ["-i", str(f)]
    parts, prev, acc = [], "[0:v]", durs[0]
    starts = {SCENES[0][0]: 0.0}
    for i in range(1, len(files)):
        kind = SCENES[i - 1][1] or "fade"
        off = acc - XFADE
        lab = f"[x{i}]"
        parts.append(f"{prev}[{i}:v]xfade=transition={kind}:duration={XFADE}:offset={off:.3f}{lab}")
        starts[SCENES[i][0]] = off
        prev, acc = lab, off + durs[i]
    mix(starts, acc)
    # Fade in from black at the start and out to black at the end.
    graph = ";".join(parts) + f";{prev}fade=t=in:st=0:d=0.3,fade=t=out:st={acc - 0.8:.3f}:d=0.8,format=yuv420p[v]"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    k = len(files)
    graph += f";[{k}:a]alimiter=limit=0.84:level=false,aformat=sample_rates={SR}:channel_layouts=stereo[a]"
    # One lossless master (x264 at QP 0 is lossless for yuv420p), then each delivery encoding from it.
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(AUDIO), "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-qp", "0", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "pcm_s16le", "-t", f"{acc:.3f}", str(MASTER)])
    sound = ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    for out, video in [
        (OUT, ["-c:v", "libx264", "-preset", "veryslow", "-crf", "21", "-profile:v", "high", "-pix_fmt", "yuv420p"]),
        (OUT_AV1, ["-c:v", "libsvtav1", "-preset", "4", "-crf", "34", "-g", "300", "-pix_fmt", "yuv420p",
                   "-svtav1-params", "tune=0"]),
    ]:
        tmp = out.with_suffix(".tmp.mp4")
        run(["ffmpeg", "-v", "error", "-y", "-i", str(MASTER), *video, *sound, str(tmp)])
        tmp.replace(out)
    # Poster: the title, with the logo, the invitation and the institutions shown.
    run(["ffmpeg", "-v", "error", "-y", "-ss", "12.8", "-i", str(OUT), "-frames:v", "1", "-q:v", "3", str(POSTER)])
    sizes = ", ".join(f"{o.name} {o.stat().st_size / 1e6:.1f} MB" for o in (OUT_AV1, OUT))
    print(f"{acc:.2f} s: {sizes}; poster {POSTER.relative_to(SITE)}")


def main() -> None:
    args = sys.argv[1:]
    step = args[0] if args else "all"
    if step == "fetch":
        fetch()
    elif step == "clips":
        clips()
    elif step == "render":
        render(args[1:])
    elif step == "assemble":
        assemble()
    elif step == "stills":
        if len(args) != 3:
            sys.exit("error: usage: python3 video/make_video.py stills SCENE t1,t2,...")
        run(["node", str(HERE / "render.mjs"), "stills", args[1], args[2]])
    elif step == "all":
        clips()
        render([])
        assemble()
    else:
        sys.exit(f"error: unknown step {step!r}; choose fetch, clips, render, assemble, stills or all")


if __name__ == "__main__":
    main()
