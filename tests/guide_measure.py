"""Measurements behind the manual's gain-staging and feedback-riding guides (v1.0.2-rc8, 2026-11-24).

Engine (C build of the exact gen~ code), not Live. Writes docs/validation/GUIDE_MEASUREMENTS.json.
Method for the feedback rides is the same as musical_eval.eval_self_oscillation (kick + snare source at
-17 dBFS peaks, FEEDBACK 4 -> ride value for 4 s -> 5, BALANCE 6, HARD).
Run: python3 tests/guide_measure.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                      # noqa: E402
from scipy import signal                # noqa: E402
import musical_eval as M                # noqa: E402
from engine import Engine               # noqa: E402

SR = M.SR
OUT = os.path.join(HERE, "..", "docs", "validation", "GUIDE_MEASUREMENTS.json")


def level_law():
    """echo gain vs LEVEL at a low (linear) level, PRE off"""
    n = int(0.05 * SR)
    x = np.zeros(int(SR * 1.2))
    x[:n] = M.env(n, 0.002, 0.02) * np.sin(2 * np.pi * 1000 * np.arange(n) / SR) * 10 ** (-40 / 20)
    pk = {}
    for L in (2, 2.5, 3, 3.5, 4, 5, 6, 8, 10):
        y = Engine(SR, in_level=L, feedback=0, balance=10, wet_only=1, pre_on=0, time_ms=300).run(x)[0]
        pk[L] = np.abs(y[int(0.25 * SR):int(0.45 * SR)]).max()
    return {str(L): {"measured_db": round(20 * np.log10(pk[L] / pk[5]), 2),
                     "formula_40log10_L_over_5_db": round(40 * np.log10(L / 5), 2)} for L in pk}


def meter(peak_dbfs, **p):
    src = M.m_kick_snare()
    x = src / np.abs(src).max() * 10 ** (peak_dbfs / 20)
    return round(float(Engine(SR, feedback=0, time_ms=380, **p).run(x)[2].max()), 1)


def meter_checks():
    rows = []
    for pk, L in [(-17, 5), (-6, 5), (-6, 2.7), (-6, 3.7), (-6, 5.3), (-12, 3.7), (-18, 7.5), (0, 1.9)]:
        rows.append({"source_peak_dbfs": pk, "level": L, "meter_db": meter(pk, in_level=L),
                     "predicted_db": round(pk + 17 + 40 * np.log10(L / 5), 1)})
    drive = [{"drive_db": d, "comp": c, "meter_db": meter(-17, drive=d, pre_comp=c)}
             for d, c in [(0, 1), (12, 1), (24, 1), (12, 0), (24, 0)]]
    att = [{"att": "-10", "source_peak_dbfs": -31, "meter_db": meter(-31, in_range=1)},
           {"att": "-30", "source_peak_dbfs": -51, "meter_db": meter(-51, in_range=0)}]
    return rows, drive, att


def ride(T, lo, hi, fb_top=10, sat=0):
    src = M.m_kick_snare()
    t_up, t_dn = 2.5, 6.5
    auto = [(int(t_up * SR), {"feedback": fb_top}), (int(t_dn * SR), {"feedback": 5})]
    _, o = M.run(src, time_ms=T, feedback=4, balance=6, auto=auto, tail=10.0, lowcut=lo, highcut=hi, loop_sat=sat)
    y = o[0]
    seg = y[int((t_dn - 1.0) * SR):int(t_dn * SR)]
    f, P = signal.periodogram(seg * np.hanning(len(seg)), SR)
    f0 = float(f[np.argmax(P[f > 30]) + np.argmax(f > 30)])
    lvl = float(M.db(M.rms(seg)))
    pre = float(M.db(M.rms(y[int(1.5 * SR):int(2.5 * SR)])))
    bu = y[int(t_up * SR):int(t_dn * SR)]
    bb = np.convolve(np.abs(bu), np.ones(4800) / 4800, "same")
    tb = float(np.argmax(bb >= bb.max() * 10 ** (-1 / 20)) / SR)
    per = T / 1000.0
    post = [M.rms(y[int((t_dn + k * per) * SR):int((t_dn + (k + 1) * per) * SR)]) for k in range(int(6 / per))]
    drop = [M.db(v / max(post[0], 1e-12)) for v in post]
    rel = next((round((k + 1) * per, 2) for k, d in enumerate(drop) if d <= -30), None)
    return {"time_ms": T, "low": ["FLAT", "125", "250", "500"][lo], "high": ["FLAT", "8k", "4k", "2k"][hi],
            "feedback_ride": fb_top, "dominant_hz": round(f0, 1), "plateau_rms_dbfs": round(lvl, 1),
            "echo_rms_before_ride_dbfs": round(pre, 1), "growth_db": round(lvl - pre, 1),
            "buildup_s": round(tb, 2), "pullback_30db_s": rel}


RECIPES = [(600, 0, 0, 10), (600, 0, 0, 9), (600, 0, 0, 8), (600, 2, 0, 10), (300, 2, 1, 10), (150, 2, 1, 10),
           (150, 3, 0, 10), (100, 3, 1, 10), (50, 3, 3, 10), (150, 3, 3, 10)]

if __name__ == "__main__":
    rows, drive, att = meter_checks()
    R = {"level_law": level_law(), "meter_checks": rows, "drive_comp": drive, "att": att,
         "rides": [ride(*r) for r in RECIPES]}
    json.dump(R, open(OUT, "w"), indent=1)
    print(json.dumps(R["meter_checks"]))
    for r in R["rides"]:
        print(r)
