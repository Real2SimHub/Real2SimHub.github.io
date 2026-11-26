#!/usr/bin/env python3
"""Synthesise the narration (video/narration.json) locally with Kokoro-82M, one WAV per line.

    python video/narrate.py          # -> video/build/voice/<id>.wav (24 kHz, mono)

Needs a Python with `kokoro` and `soundfile` (pip install kokoro soundfile); the model and the voice are
downloaded once from Hugging Face at the pinned revision (Apache-2.0). No text leaves the machine.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "voice"


def main() -> None:
    try:
        import numpy as np
        import soundfile as sf
        from kokoro import KModel, KPipeline
    except ImportError as e:
        sys.exit(f"error: {e}\n  fix: run with a Python that has kokoro and soundfile (pip install kokoro soundfile)")
    from huggingface_hub import hf_hub_download

    spec = json.loads((HERE / "narration.json").read_text())
    repo, rev = spec["model"], spec["revision"]
    # The model, its config and the voice, at the pinned revision.
    files = {name: hf_hub_download(repo, name, revision=rev)
             for name in ("config.json", "kokoro-v1_0.pth", f"voices/{spec['voice']}.pt")}
    model = KModel(repo_id=repo, config=files["config.json"], model=files["kokoro-v1_0.pth"])
    pipe = KPipeline(lang_code=spec["voice"][0], repo_id=repo, model=model)
    voice = files[f"voices/{spec['voice']}.pt"]
    OUT.mkdir(parents=True, exist_ok=True)
    for line in spec["lines"]:
        parts = [np.asarray(audio) for _, _, audio in pipe(line["text"], voice=voice, speed=spec["speed"])]
        wav = np.concatenate(parts)
        sf.write(OUT / f"{line['id']}.wav", wav, 24000)
        print(f"{line['id']}: {len(wav) / 24000:.2f} s  {line['text']}")


if __name__ == "__main__":
    main()
