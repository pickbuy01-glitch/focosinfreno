"""Original dark-minimal ambient bed + subtle SFX, synthesized with numpy (deterministic, seeded)."""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
SR = 44100
rng = np.random.default_rng(7)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    e[:a] = np.linspace(0, 1, a)
    e[n - r:] *= np.linspace(1, 0, r)
    return e


def bed(seconds):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    # A-minor-ish drone: A1, E2, A2, C3 with slow detuned beating and breathing LFO
    for f, amp, lfo in [(55.0, 0.30, 0.05), (82.41, 0.18, 0.07), (110.0, 0.12, 0.04), (130.81, 0.06, 0.09)]:
        out += amp * (0.6 + 0.4 * np.sin(2 * np.pi * lfo * t)) * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t))
    # Second section (from ~22s) adds a soft fifth above for controlled lift
    lift = np.clip((t - 21.5) / 3, 0, 1) * np.clip((40 - t) / 3, 0, 1)
    out += 0.05 * lift * np.sin(2 * np.pi * 164.81 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t))
    # Air: filtered noise
    noise = lowpass(rng.standard_normal(n), 900) * 0.06
    out += noise * (0.7 + 0.3 * np.sin(2 * np.pi * 0.03 * t))
    # Slow pulse (heartbeat-like, very low) under the posture/mechanics sections
    for beat in np.arange(5.2, 31.0, 1.6):
        i = int(beat * SR)
        m = min(int(0.5 * SR), n - i)
        tt = np.arange(m) / SR
        out[i:i + m] += 0.10 * np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 9)
    out *= env(n, 1.2, 3.0)
    return out / np.max(np.abs(out)) * 0.5


def impact(seconds=1.6):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (70 - 25 * t) * t) * np.exp(-t * 3.5)
    click = lowpass(rng.standard_normal(n), 2500) * np.exp(-t * 40) * 0.5
    x = body + click
    return x / np.max(np.abs(x)) * 0.6


def tick(seconds=0.25):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 60) * 0.5 + np.sin(2 * np.pi * 880 * t) * np.exp(-t * 35) * 0.3
    return x / np.max(np.abs(x)) * 0.35


def whoosh(seconds=1.1):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    sweep = np.zeros(n)
    acc, a_prev = 0.0, 0.0
    for i in range(n):
        cutoff = 300 + 2600 * np.sin(np.pi * t[i] / seconds) ** 2
        a = np.exp(-2 * np.pi * cutoff / SR)
        acc = (1 - a) * noise[i] + a * acc
        sweep[i] = acc
    x = sweep * np.sin(np.pi * t / seconds) ** 2
    return x / np.max(np.abs(x)) * 0.4


def pulse(seconds=0.6):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 95 * t) * np.exp(-t * 7) + 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 12)
    return x / np.max(np.abs(x)) * 0.45


def resolve(seconds=3.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(220, 0.5), (329.63, 0.35), (440, 0.2)])
    x *= np.minimum(t / 0.08, 1) * np.exp(-t * 1.3)
    return x / np.max(np.abs(x)) * 0.35


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 44.0
    out = ROOT / "assets/audio"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "bed.wav", bed(seconds).astype(np.float32), SR)
    for name, fn in [("impact", impact), ("tick", tick), ("whoosh", whoosh), ("pulse", pulse), ("resolve", resolve)]:
        sf.write(out / f"{name}.wav", fn().astype(np.float32), SR)
    print("ok", file=sys.stderr)


if __name__ == "__main__":
    main()
