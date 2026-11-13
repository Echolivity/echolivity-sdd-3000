#!/usr/bin/env python3
"""
HW-1 remediation: offline calibration of candidate D (writes experiments/hw1/d_calibration.json).

Per host rate (44.1/48/88.2/96/176.4/192 kHz) it determines, from measurements of the C engine:

  eq       the droop-EQ (RBJ peaking, same structure as production) that makes the D memory path
           match the PRODUCTION effect-path magnitude (production with its shipping hf_comp = 1).
           Target = production as it sounds today, not a flatter "ideal" response.
  m        the host-rate biquad M of the TIME-0 short path, fitted so the short path has the same
           magnitude as the D memory path (min-phase, stable by construction).
  cmp      the memory-path latency compensation in whole memory ticks, so that the echo of a
           click lands at TIME + (short-path latency), i.e. constant latency from TIME 0 upwards.

Steps: build an uncalibrated engine (short path on, M = 1, cmp = 0) -> measure -> fit -> write.
"""
import json, os, subprocess, sys
import numpy as np
from scipy import signal, optimize

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from engine import Engine  # noqa
from fit_hfcomp import peq_db  # noqa

RATES = (44100, 48000, 88200, 96000, 176400, 192000)
PROD = os.path.join(ROOT, "build", "engine.so")
RAW = os.path.join(HERE, "build", "engine_draw.so")


def build(name, *args):
    subprocess.check_call([os.path.join(HERE, "build_d.sh"), name, *args])
    return os.path.join(HERE, "build", f"engine_{name}.so")


def measure(so, sr, T, **p):
    """Stepped-sine magnitude response (dB) of the wet path. Sines, not noise: on the production
    engine a noise/CSD estimate is biased by the very images under investigation (it reads
    +0.5 dB at 200 Hz where a sine reads +0.1 dB), so the ground truth is a tone at a time."""
    f = np.unique(np.concatenate([np.geomspace(100, 0.47 * sr, 52), [1000.0, 17000.0, 20000.0]]))
    out = []
    for f0 in f:
        e = Engine(sr, so=so, time_ms=T, feedback=0, balance=10, converter=1, **p)
        e.silence(0.05)
        n = int(0.4 * sr)
        x = np.sin(2 * np.pi * f0 * np.arange(n) / sr) * 0.014125   # -20 dB re nominal (as reproduce.py)
        y = e.run(x)[0][int(0.15 * sr):]
        tt = np.arange(len(y)) / sr                  # least-squares sine fit at f0 (no scalloping)
        A = np.stack([np.sin(2 * np.pi * f0 * tt), np.cos(2 * np.pi * f0 * tt), np.ones_like(tt)], 1)
        c = np.linalg.lstsq(A, y, rcond=None)[0]
        out.append(20 * np.log10(np.hypot(c[0], c[1]) / 0.014125))
    return f, np.array(out)


def echo_peak_ms(so, sr, T, **p):
    e = Engine(sr, so=so, time_ms=T, feedback=0, balance=10, **p)
    e.silence(1.2)
    n = int(sr * (T / 1000 + 0.2))
    x = np.zeros(n); x[0] = 0.5
    y = e.run(x)[0]
    i = int(np.argmax(np.abs(y)))
    a, b, c = y[i - 1], y[i], y[i + 1]
    den = a - 2 * b + c
    off = 0.5 * (a - c) / den if den != 0 else 0
    return (i + off) / sr * 1000


def biq(par):
    """min-phase, stable biquad from (gain, zero radius, zero angle, pole radius, pole angle)."""
    g, rz, tz, rp, tp = par
    rz = 0.97 / (1 + np.exp(-rz)); rp = 0.97 / (1 + np.exp(-rp))
    tz = np.pi / (1 + np.exp(-tz)); tp = np.pi / (1 + np.exp(-tp))
    b = np.array([1, -2 * rz * np.cos(tz), rz * rz])
    a = np.array([1, -2 * rp * np.cos(tp), rp * rp])
    b = b * (np.sum(a) / np.sum(b)) * np.exp(g)       # unity at DC times exp(g)
    return b, a


def fit_m(f, target_db, sr):
    band = (f >= 100) & (f <= min(20000, 0.45 * sr))
    def cost(par):
        b, a = biq(par)
        _, h = signal.freqz(b, a, worN=f[band], fs=sr)
        return 20 * np.log10(np.abs(h)) - target_db[band]
    best = None
    for tz in (-2, 0, 2, 4):
        for tp in (-3, -1, 1):
            r = optimize.least_squares(cost, [0, 0, tz, 0, tp], max_nfev=4000)
            if best is None or r.cost < best.cost:
                best = r
    b, a = biq(best.x)
    _, h = signal.freqz(b, a, worN=f[band], fs=sr)
    err = float(np.max(np.abs(20 * np.log10(np.abs(h)) - target_db[band])))
    return [float(b[0]), float(b[1]), float(b[2]), float(a[1]), float(a[2])], err


def fit_eq(f, d_db, prod_db, sr):
    """Two RBJ peaking sections (the production droop-EQ structure plus one more) so that the D
    memory path matches the production effect path; one section can't follow production's
    broad +1 dB 5-12 kHz shelf (its linear-interpolation compensation) and its top-octave cut."""
    band = (f > 300) & (f < min(19000, 0.43 * sr))
    def cost(x):
        f1, g1, q1, f2, g2, q2 = x
        if not (1000 < f1 < 0.45 * sr and 1000 < f2 < 0.45 * sr and 0.2 < q1 < 3 and 0.2 < q2 < 3
                and -6 < g1 < 6 and -6 < g2 < 6):
            return 1e9
        r = d_db + peq_db(f, sr, f1, g1, q1) + peq_db(f, sr, f2, g2, q2) - prod_db
        # guard: never above production (+0.3 dB) above 21 kHz (up to 0.47 fs) - an ultrasonic boost
        # would raise the regeneration-loop gain where nobody listens
        guard = (f > 21000) & (prod_db > -60)
        # service-manual effect-path spec, 20 Hz-17 kHz +0.5/-3 dB, with 0.25 dB margin. Production's
        # tone response misses it at 48/96 kHz (-3.43 dB at 17 kHz; its rms test reading includes image
        # energy); where production is compliant this term is inactive and production is matched.
        spec = (f >= 20) & (f <= 17000)
        a_ = d_db[spec] + peq_db(f[spec], sr, f1, g1, q1) + peq_db(f[spec], sr, f2, g2, q2)
        viol = np.maximum(-2.75 - a_, 0) + np.maximum(a_ - 0.35, 0)
        # no EQ boost above 21 kHz (keeps the regeneration loop's ultrasonic gain at or below D's own)
        us = f > 21000
        eqg = peq_db(f[us], sr, f1, g1, q1) + peq_db(f[us], sr, f2, g2, q2) if us.any() else np.zeros(1)
        viol = np.concatenate([viol, np.maximum(eqg - 1.0, 0)])
        over = np.maximum(r[guard] - 0.3, 0)
        return np.mean(r[band] ** 2) + (50 * np.mean(over ** 2) if over.size else 0.0) + 200 * np.sum(viol ** 2)
    best = None
    for f1 in (6000, 9000, 12000):
        for f2 in (16000, 18000, 19500, 0.4 * sr):
            r = optimize.minimize(cost, [min(f1, 0.4 * sr), 0.5, 0.7, min(f2, 0.44 * sr), -1, 1.5],
                                  method="Nelder-Mead", options=dict(maxiter=10000, xatol=0.5, fatol=1e-9))
            if best is None or r.fun < best.fun:
                best = r
    x = best.x
    res = d_db + peq_db(f, sr, *x[:3]) + peq_db(f, sr, *x[3:]) - prod_db
    a17 = float(np.interp(17000, f, d_db + peq_db(f, sr, *x[:3]) + peq_db(f, sr, *x[3:])))
    print(f"   {sr}: response at 17 kHz {a17:+.2f} dB (production {np.interp(17000, f, prod_db):+.2f})")
    return [float(v) for v in x], float(np.max(np.abs(res[band])))


def main():
    raw = build("draw", "--cal", "/nonexistent")
    cal = {"note": "fitted by experiments/hw1/fit_d.py", "rates": {}, "eq": {}, "default_cmp_ticks": 0, "fit": {}}
    for sr in RATES:
        f, prod = measure(PROD, sr, 20, hf_comp=1)
        _, dmem = measure(raw, sr, 20, hf_comp=0)
        _, dshort = measure(raw, sr, 0, hf_comp=0)
        n1 = np.interp(1000, f, prod)
        prod_n, dmem_n, dshort_n = prod - n1, dmem - np.interp(1000, f, dmem), dshort - np.interp(1000, f, dshort)
        eq, eq_err = fit_eq(f, dmem_n, prod_n, sr)
        m, m_err = fit_m(f, dmem - dshort, sr)
        cal["eq"][str(sr)] = eq
        cal["rates"][str(sr)] = {"m": m}
        cal["fit"][str(sr)] = {"eq_max_err_db_300Hz_to_19k": round(eq_err, 3), "m_max_err_db": round(m_err, 3)}
        print(sr, "eq", np.round(eq, 3), "err", round(eq_err, 2), "| M err", round(m_err, 3), flush=True)
    # latency: with the fitted M (which has its own small delay) measure short vs memory path
    tmp = os.path.join(HERE, "build", "cal_tmp.json")
    json.dump(cal, open(tmp, "w"))
    mid = build("dmid", "--cal", tmp)
    for sr in RATES:
        base = echo_peak_ms(mid, sr, 0)
        lat = np.mean([echo_peak_ms(mid, sr, T) - T for T in (10, 100, 500)])
        ticks = int(round((lat - base) * 64))
        cal["rates"][str(sr)]["cmp_ticks"] = ticks
        cal["fit"][str(sr)].update(short_latency_ms=round(base, 5), memory_latency_uncomp_ms=round(lat, 5),
                                   cmp_ticks=ticks, residual_us=round((lat - base - ticks / 64) * 1000, 2))
        print(sr, "TIME0 %.4f ms, memory path +%.4f ms -> cmp %d ticks, residual %.1f us"
              % (base, lat, ticks, (lat - base - ticks / 64) * 1000), flush=True)
    cal["default_cmp_ticks"] = int(np.median([cal["rates"][str(s)]["cmp_ticks"] for s in RATES]))
    json.dump(cal, open(os.path.join(HERE, "d_calibration.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
