#!/usr/bin/env python3
"""FEEDBACK 10 self-oscillation: steady output offset (mean of 2 s windows, last 6 s of a 16 s tail)
for several loop options, production vs candidate D. Shows whether the 'tail DC' of t_feedback_extreme
is a property of the conversion or of the oscillation mode. Writes results/fb10_tail_modes.json."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine
sr = 48000
ENG = {"production": os.path.join(ROOT, "build", "engine.so"), "candidate_D": os.path.join(HERE, "build", "engine_d.so")}


def probe(so, secs=16, seed=22, T=37, **p):
    rng = np.random.default_rng(seed)
    e = Engine(sr, so=so, time_ms=T, feedback=10, balance=10, in_range=0, in_level=10, **p)
    x = np.concatenate([rng.uniform(-1, 1, sr * 4) + 0.5, np.zeros(sr * secs)])
    y = e.run(x, rng.uniform(-1, 1, len(x)))
    n = len(y[0])
    return {ch: [round(float(np.mean(y[c][i:i + 2 * sr])), 4) for i in range(n - 6 * sr, n - 2 * sr + 1, 2 * sr)]
            for c, ch in ((0, "L"), (1, "R"))}


CASES = {"RND INT10 true stereo (the t_feedback_extreme case)": dict(out_mode=3, waveform=2, intensity=10, frequency=8),
         "RND INT10 mono": dict(waveform=2, intensity=10, frequency=8),
         "SQUARE INT10 true stereo": dict(out_mode=3, waveform=1, intensity=10, frequency=8),
         "TRI INT10 true stereo": dict(out_mode=3, waveform=0, intensity=10, frequency=8),
         "no modulation, true stereo": dict(out_mode=3),
         "RND INT5 true stereo": dict(out_mode=3, waveform=2, intensity=5, frequency=8)}
res = {}
for name, p in CASES.items():
    for w, so in ENG.items():
        res[f"{name}: {w}"] = probe(so, **p)
        print(name, w, res[f"{name}: {w}"], flush=True)
json.dump(res, open(os.path.join(HERE, "results", "fb10_tail_modes.json"), "w"), indent=1)
