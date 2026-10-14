"""Assemble index.html from src/index.template.html + audio_meta.json (frame timing, captions, audio tracks)."""
import json
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
LOCKUP = 1.8  # seconds of brand lockup after the last line


def main():
    meta = json.loads((ROOT / "audio_meta.json").read_text())
    voices = sorted(meta["voices"], key=lambda v: v["frame"])
    frames, t = [], 0.0
    for v in voices:
        frames.append({"start": round(t, 3), "duration": v["duration_s"], "words": v["words"], "voice": v["path"]})
        t += v["duration_s"]
    lockup_start = round(t, 3)
    total = round(t + LOCKUP, 3)
    frames[-1]["duration"] = round(total - frames[-1]["start"], 3)

    def word_time(fi, text):
        fr = frames[fi]
        for w in fr["words"]:
            if w["text"].lower().strip(".,?:") == text:
                return round(fr["start"] + w["start"], 3)
        return fr["start"]

    sfx = [
        ("impact", 0.38, 0.55),
        ("tick", frames[1]["start"] + 0.25, 0.5),
        ("tick", frames[1]["start"] + 1.85, 0.4),
        ("tick", frames[1]["start"] + 5.0, 0.4),
        ("whoosh", frames[2]["start"] - 0.25, 0.45),
        ("tick", word_time(2, "head") - 0.05, 0.4),
        ("tick", word_time(2, "jaw") - 0.05, 0.4),
        ("tick", word_time(2, "chewing") - 0.05, 0.4),
        ("impact", frames[3]["start"] + 0.1, 0.35),
        ("pulse", frames[3]["start"] + 3.6, 0.5),
        ("whoosh", frames[4]["start"] - 0.1, 0.4),
        ("impact", word_time(4, "better"), 0.5),
        ("whoosh", frames[5]["start"] - 0.2, 0.35),
        ("resolve", lockup_start + 0.15, 0.5),
    ]
    audio = []
    for i, fr in enumerate(frames):
        audio.append(f'      <audio id="vo-{i + 1}" src="{fr["voice"]}" data-start="{fr["start"]}" data-duration="{sf.info(ROOT / fr["voice"]).duration:.3f}" data-track-index="10" data-volume="1"></audio>')
    audio.append(f'      <audio id="bgm" src="assets/audio/bed.wav" data-start="0" data-duration="{total}" data-track-index="11" data-volume="0.32"></audio>')
    for i, (name, at, vol) in enumerate(sfx):
        dur = min(sf.info(ROOT / f"assets/audio/{name}.wav").duration, total - at)
        audio.append(f'      <audio id="sfx-{i + 1}" src="assets/audio/{name}.wav" data-start="{max(at, 0):.3f}" data-duration="{dur:.3f}" data-track-index="{12 + i % 3}" data-volume="{vol}"></audio>')

    timing = {"frames": [{k: fr[k] for k in ("start", "duration", "words")} for fr in frames], "lockupStart": lockup_start, "total": total}
    html = (ROOT / "src/index.template.html").read_text()
    reps = {"__TOTAL__": str(total), "__TIMING__": json.dumps(timing), "__AUDIO__": "\n".join(audio)}
    for i, fr in enumerate(frames):
        reps[f"__F{i + 1}S__"] = str(fr["start"])
        reps[f"__F{i + 1}D__"] = str(fr["duration"])
    for k, v in reps.items():
        html = html.replace(k, v)
    (ROOT / "index.html").write_text(html)
    print(f"index.html · {len(frames)} frames · total {total}s · lockup at {lockup_start}s")


if __name__ == "__main__":
    main()
