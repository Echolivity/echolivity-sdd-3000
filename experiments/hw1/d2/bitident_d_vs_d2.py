#!/usr/bin/env python3
"""D2 must equal D everywhere except the HOLD release switch. Compare all 8 outputs, sample by sample:
9 factory programs x 4 output modes x 44.1/48/96 kHz (dense mix + decorrelated R), random per-vector
automation of every non-HOLD parameter (20 s), HOLD engage only, and HOLD release (expected to differ).
-> results/bitident_d_vs_d2.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine
import musical_eval as ME
D = os.path.join(ROOT, "experiments/hw1/audit/build/engine_cand.so"); D2 = os.path.join(HERE, "build/engine_d2.so")
NOM = 10 ** (-17 / 20)
progs = json.load(open(os.path.join(ROOT, "presets", "factory_programs.json")))["programs"]
xl = ME.m_dense(); xl = xl / np.abs(xl).max() * NOM; xr = np.roll(xl, 600) * 0.8
res = {}


def cmp(sr, xa, xb=None, auto=None, **p):
    a = Engine(sr, so=D, **p).run(xa, xb, automation=auto); b = Engine(sr, so=D2, **p).run(xa, xb, automation=auto)
    return float(np.max(np.abs(a - b)))


for sr in (44100, 48000, 96000):
    for pr in progs:
        for mode in (0, 1, 2, 3):
            v = dict(pr["values"]); v["out_mode"] = mode
            res[f"{sr}|P{pr['slot']}|mode{mode}"] = cmp(sr, xl, xr if mode == 3 else None, **v)
    print(sr, "programs max diff", max(v for k, v in res.items() if k.startswith(str(sr))), flush=True)
rng = np.random.default_rng(7)
names = ["time_ms", "feedback", "balance", "intensity", "frequency", "lowcut", "highcut", "fb_inv", "waveform", "out_mode", "converter", "in_level", "drive", "loop_sat", "time_glide"]
rngs = {"time_ms": (0, 1023), "feedback": (0, 10), "balance": (0, 10), "intensity": (0, 10), "frequency": (0, 10), "lowcut": (0, 3), "highcut": (0, 3),
        "fb_inv": (0, 1), "waveform": (0, 3), "out_mode": (0, 3), "converter": (0, 1), "in_level": (0, 10), "drive": (0, 10), "loop_sat": (0, 1), "time_glide": (0, 1)}
auto = [(i * 64, {n: float(rng.uniform(*rngs[n]))}) for i, n in enumerate(rng.choice(names, 15000))]
x = rng.uniform(-0.3, 0.3, 48000 * 20)
res["random automation 20 s (no HOLD)"] = cmp(48000, x, rng.uniform(-0.3, 0.3, len(x)), auto=auto)
res["HOLD engage only (never released), T 380"] = cmp(48000, np.tile(xl, 3), None, auto=[(48000, {"hold": 1})], time_ms=380, feedback=3)
res["HOLD release, T 120 (expected to differ)"] = cmp(48000, np.tile(xl, 3), None, auto=[(48000, {"hold": 1}), (96000, {"hold": 0})], time_ms=120, feedback=3)
for k in list(res)[-3:]:
    print(k, res[k])
json.dump(res, open(os.path.join(HERE, "results", "bitident_d_vs_d2.json"), "w"), indent=1)
