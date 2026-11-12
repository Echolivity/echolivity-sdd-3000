#!/usr/bin/env python3
"""
Fit the per-sample-rate droop-compensation EQ (tools/hfcomp_table.json).

The original memory runs at 64 kHz with a zero-order-hold DAC. Emulating that
clock inside a host running at 44.1-192 kHz adds two non-authentic losses:
linear interpolation of the input at tick times and box-averaging of the DAC
output over each host sample. This script measures the effect-path response
of the real engine with compensation off, then fits one RBJ peaking EQ per
host rate so the effect path matches the *authentic* target:

  target(f) = ZOH(64 kHz) x 2-pole AA x 2-pole reconstruction
              (analog Butterworth corners chosen for -3 dB @ 17 kHz,
               the service-manual effect-path spec)
"""
import json, os, sys
import numpy as np
from scipy import signal, optimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tests"))
from engine import Engine, build  # noqa

FA = 23941.0
RATES = [44100, 48000, 88200, 96000, 176400, 192000]


def target_db(f):
    zoh = np.abs(np.sinc(f / 64000.0))
    # analog 2-pole Butterworth, squared (AA + reconstruction)
    fc = optimize.brentq(lambda c: 20 * np.log10(np.abs(np.sinc(17000 / 64000))
                                                 / (1 + (17000 / c) ** 4)) + 3.0, 15000, 60000)
    b = 1 / (1 + (f / fc) ** 4)
    return 20 * np.log10(zoh * b), fc


def measure(sr):
    e = Engine(sr, time_ms=20, feedback=0, balance=10, converter=1, hf_comp=0)
    rng = np.random.default_rng(0)
    x = rng.standard_normal(int(sr * 8)) * 0.02
    y = e.run(x)[0]
    d = int(sr * 0.02) + 2
    xx, yy = x[:-d], y[d:]
    f, pxy = signal.csd(xx, yy, fs=sr, nperseg=8192)
    _, pxx = signal.welch(xx, fs=sr, nperseg=8192)
    return f, 20 * np.log10(np.abs(pxy / pxx))


def peq_db(f, sr, f0, gdb, q):
    A = 10 ** (gdb / 40)
    w = 2 * np.pi * f0 / sr
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    _, h = signal.freqz(b, a, worN=f, fs=sr)
    return 20 * np.log10(np.abs(h))


def main():
    build()
    out = []
    for sr in RATES:
        f, m = measure(sr)
        tgt, fc = target_db(f)
        m = m - np.interp(1000, f, m)          # normalise at 1 kHz
        hi = min(19000, 0.43 * sr)
        band = (f > 300) & (f < hi)
        guard = (f > 300) & (f < 0.49 * sr)

        def cost(p):
            f0, gdb, q = p
            if not (2000 < f0 < 0.45 * sr and -1 < gdb < 9 and 0.2 < q < 3):
                return 1e9
            r = m + peq_db(f, sr, f0, gdb, q)
            err = r[band] - tgt[band]
            over = np.maximum(r[guard] - np.maximum(tgt[guard], -40) - 0.3, 0)
            return np.mean(err ** 2) + 50 * np.mean(over ** 2)

        best = None
        for f0 in np.linspace(8000, min(0.44 * sr, 40000), 12):
            for q in (0.4, 0.7, 1.0):
                r = optimize.minimize(cost, [f0, 4.0, q], method="Nelder-Mead",
                                      options=dict(maxiter=3000, xatol=1, fatol=1e-6))
                if best is None or r.fun < best.fun:
                    best = r
        f0, gdb, q = best.x
        res = m + peq_db(f, sr, f0, gdb, q)
        err = np.max(np.abs(res[band] - tgt[band]))
        print(f"{sr:6d} Hz: EQ f0={f0:8.0f} gain={gdb:5.2f} dB Q={q:4.2f}  max err {err:.2f} dB "
              f"(uncomp @17k {np.interp(17000, f, m):+.2f}, comp {np.interp(17000, f, res):+.2f}, "
              f"target {np.interp(17000, f, tgt):+.2f})")
        out.append([sr, FA, float(f0), float(gdb), float(q)])
    json.dump({"note": "fitted by tools/fit_hfcomp.py; analog target corner %.0f Hz" % fc,
               "rates": out}, open(os.path.join(HERE, "hfcomp_table.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
