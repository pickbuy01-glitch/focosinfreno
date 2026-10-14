"""Synthesize the narration phrase by phrase with local Kokoro so every phrase and word has a known time.

Writes assets/voice/NN.wav per frame and audio_meta.json (voices + word timings).
Word times inside a phrase are distributed by character length (no ASR available offline).
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path.home() / ".cache/hyperframes/tts"
VOICE, SPEED, SR = "am_michael", 1.15, 24000
GAP = {",": 0.07, ":": 0.12, ".": 0.2, "?": 0.24}
LEAD, TAIL = 0.06, 0.18


def lines_from_script(md):
    out = []
    for block in re.split(r"^## Line \d+ .*?\(Frame (\d+)\)\s*$", md, flags=re.M)[1:]:
        out.append(block)
    frames = []
    for i in range(0, len(out), 2):
        frame = int(out[i])
        spoken = " ".join(l.strip() for l in out[i + 1].splitlines() if l.startswith("    "))
        frames.append((frame, spoken))
    return frames


def trim(audio, thr=0.01):
    idx = np.where(np.abs(audio) > thr)[0]
    if not len(idx):
        return audio
    a, b = max(idx[0] - int(0.02 * SR), 0), min(idx[-1] + int(0.04 * SR), len(audio))
    return audio[a:b]


def main():
    kokoro = Kokoro(str(CACHE / "models/kokoro-v1.0.onnx"), str(CACHE / "voices/voices-v1.0.bin"))
    frames = lines_from_script((ROOT / "SCRIPT.md").read_text())
    voices = []
    (ROOT / "assets/voice").mkdir(parents=True, exist_ok=True)
    for frame, text in frames:
        phrases = re.findall(r"[^,.?:]+[,.?:]?", text)
        chunks, words, t = [np.zeros(int(LEAD * SR), dtype=np.float32)], [], LEAD
        for ph in (p.strip() for p in phrases):
            if not ph:
                continue
            samples, _ = kokoro.create(ph, voice=VOICE, speed=SPEED, lang="en-us")
            samples = trim(samples.astype(np.float32))
            dur = len(samples) / SR
            toks = ph.split()
            weights = [len(re.sub(r"[^\w']", "", w)) + 1.5 for w in toks]
            total, acc = sum(weights), 0.0
            for w, wt in zip(toks, weights):
                start = t + dur * acc / total
                acc += wt
                words.append({"text": w, "start": round(start, 3), "end": round(t + dur * acc / total, 3)})
            chunks.append(samples)
            t += dur
            gap = GAP.get(ph[-1], 0.12)
            chunks.append(np.zeros(int(gap * SR), dtype=np.float32))
            t += gap
        chunks.append(np.zeros(int(TAIL * SR), dtype=np.float32))
        audio = np.concatenate(chunks)
        path = f"assets/voice/{frame:02d}.wav"
        sf.write(ROOT / path, audio, SR)
        voices.append({"frame": frame, "path": path, "duration_s": round(len(audio) / SR, 3), "words": words})
        print(f"frame {frame}: {len(audio) / SR:.2f}s, {len(words)} words", file=sys.stderr)
    meta_path = ROOT / "audio_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta["voices"] = voices
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"total {sum(v['duration_s'] for v in voices):.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
