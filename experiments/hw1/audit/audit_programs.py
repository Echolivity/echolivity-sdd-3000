#!/usr/bin/env python3
"""Audit G: factory programs, stereo image and gain. Dense mix (L) + a decorrelated copy (R, 13 ms offset,
polarity-flipped organ) through every program in every OUTPUT MODE, production vs candidate D.
Per output: rms level per channel, L/R correlation, side/mid energy ratio. -> results/audit_programs.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine
import musical_eval as ME
engs = dict(a.split("=", 1) for a in sys.argv[1:])
SR = 48000; NOM = 10 ** (-17 / 20)
progs = json.load(open(os.path.join(ROOT, "presets", "factory_programs.json")))["programs"]
xl = ME.m_dense(); xl = xl / np.abs(xl).max() * NOM
xr = np.roll(xl, int(0.013 * SR)) * 0.8
xl = np.concatenate([xl, np.zeros(3 * SR)]); xr = np.concatenate([xr, np.zeros(3 * SR)])
db = lambda v: float(20 * np.log10(v + 1e-30))
res = {}
for pr in progs:
    for mode in (0, 1, 2, 3):
        for name, so in engs.items():
            v = dict(pr["values"]); v["out_mode"] = mode
            e = Engine(SR, so=os.path.abspath(so), **v); e.silence(0.1)
            y = e.run(xl, xr if mode == 3 else None)[:2]
            L, R = y
            m, s = (L + R) / 2, (L - R) / 2
            res[f"P{pr['slot']}|mode{mode}|{name}"] = dict(rms_L_db=round(db(np.sqrt(np.mean(L ** 2))), 2), rms_R_db=round(db(np.sqrt(np.mean(R ** 2))), 2),
                                                            corr=round(float(np.corrcoef(L, R)[0, 1]) if np.std(R) > 0 and np.std(L) > 0 else 1.0, 4),
                                                            side_mid_db=round(db(np.sqrt(np.mean(s ** 2))) - db(np.sqrt(np.mean(m ** 2))), 2))
    print(pr["name"], flush=True)
json.dump(res, open(os.path.join(HERE, "results", "audit_programs.json"), "w"), indent=1)
