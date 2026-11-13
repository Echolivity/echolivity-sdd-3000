#!/usr/bin/env python3
"""
Audit C: spectral integrity, production vs candidate D, 44.1 / 48 / 96 kHz, TIME 0 (short path) and
TIME 20 (memory path), two operating points:
  'clean'   : CLEAN converter, PRE off  (linear operating point: isolates the conversion)
  'default' : 13-bit gain-ranged converter, PRE on (what ships)

Single tones 100 Hz-19 kHz at -40 / -20 / -6 dB re nominal (+4 dBm = -17 dBFS) -> fundamental gain,
harmonics H2-H9 (folded at the host Nyquist), THD, THD+N (20 Hz-20 kHz), worst INHARMONIC line
(not DC, not the fundamental, not a folded harmonic), noise floor (median per-bin level, lines excluded).
Twin/two-tone IMD: SMPTE 60 Hz + 7 kHz (4:1), CCIF 19 + 20 kHz and 13 + 14 kHz (1:1).
Phase: least-squares phase of stepped tones (TIME 20) minus the pure delay -> group delay per band.
Usage: audit_spectral.py production=SO candidate_D=SO   -> results/audit_spectral.json
"""
import json, os, sys
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from engine import Engine  # noqa
NOM = 10 ** (-17 / 20)
OUT = os.path.join(HERE, "results")
FREQS = [100, 1000, 5000, 10000, 15000, 17000, 19000]
LEVELS = [-40, -20, -6]
OPS = {"clean": dict(converter=1, pre_on=0), "default": dict()}


def run(so, sr, x, T, op, secs_pre=0.1):
    e = Engine(sr, so=so, time_ms=T, feedback=0, balance=10, **OPS[op])
    e.silence(secs_pre)
    return e.run(x)[0]


def spec(y, sr):
    w = signal.windows.blackmanharris(len(y))
    S = np.abs(np.fft.rfft(y * w)) / (w.sum() / 2)
    return np.fft.rfftfreq(len(y), 1 / sr), S


def fold(f, sr):
    f = f % sr
    return sr - f if f > sr / 2 else f


def line(fr, S, f, w=3):
    k = int(np.argmin(np.abs(fr - f)))
    return S[max(k - w, 0):k + w + 1].max()


def analyse_tone(y, sr, f0):
    fr, S = spec(y, sr)
    a0 = line(fr, S, f0)
    harm = {}
    mask = (fr > 20) & (np.abs(fr - f0) > 25)
    for k in range(2, 10):
        fh = fold(k * f0, sr)
        harm[k] = fh
        mask &= np.abs(fr - fh) > 25
    hl = {k: 20 * np.log10(line(fr, S, fh) / a0 + 1e-30) for k, fh in harm.items() if 20 < fh < 20000}
    thd = 10 * np.log10(sum(10 ** (v / 10) for v in hl.values()) + 1e-30)
    band = (fr >= 20) & (fr <= 20000)
    P = S ** 2
    nonfund = band & (np.abs(fr - f0) > 25)
    # THD+N: everything in band but the fundamental (window ENBW cancels in the ratio of sums)
    thdn = 10 * np.log10(P[nonfund].sum() / P[band & ~nonfund].sum())
    inh = np.where(mask & band, S, 0)
    k = int(np.argmax(inh))
    floor = 20 * np.log10(np.median(S[mask & band]) / a0 + 1e-30)
    return dict(fund_dbfs=round(float(20 * np.log10(a0)), 2), H=dict((str(k_), round(v, 1)) for k_, v in hl.items()),
                thd_db=round(float(thd), 1), thdn_db=round(float(thdn), 1),
                worst_inharmonic=dict(hz=float(round(fr[k], 1)), db=round(float(20 * np.log10(inh[k] / a0 + 1e-30)), 1)),
                noise_floor_db_per_bin=round(float(floor), 1))


def imd(y, sr, kind):
    fr, S = spec(y, sr)
    if kind == "SMPTE":
        ref = line(fr, S, 7000)
        prods = {f"7k{'+' if n > 0 else '-'}{abs(n) * 60}": line(fr, S, 7000 + n * 60) for n in (-4, -3, -2, -1, 1, 2, 3, 4)}
        tot = 10 * np.log10(sum((v / ref) ** 2 for v in prods.values()))
        return dict(imd_db=round(float(tot), 1))
    f1, f2 = (19000, 20000) if kind == "CCIF19/20" else (13000, 14000)
    ref = line(fr, S, f2)
    out = {"d2 (f2-f1)": line(fr, S, f2 - f1), "d3 (2f1-f2)": line(fr, S, 2 * f1 - f2)}
    if 2 * f2 - f1 < 20000:
        out["d3 (2f2-f1)"] = line(fr, S, 2 * f2 - f1)
    res = {k: round(float(20 * np.log10(v / ref + 1e-30)), 1) for k, v in out.items()}
    # worst line that is none of the inputs, their IM products up to 3rd order or harmonics
    known = [f1, f2, f2 - f1, 2 * f1 - f2, 2 * f2 - f1, f1 + f2, 2 * f1, 2 * f2] + [fold(k * f, sr) for k in range(2, 6) for f in (f1, f2)]
    m = (fr > 20) & (fr < 20000)
    for f in known:
        m &= np.abs(fr - f) > 25
    k = int(np.argmax(np.where(m, S, 0)))
    res["worst_other_line"] = dict(hz=float(round(fr[k], 1)), db=round(float(20 * np.log10(S[k] / ref + 1e-30)), 1))
    return res


def phase_gd(so, sr):
    """group delay (ms re TIME) from the LS phase of stepped tones, TIME 20 ms, default operating point"""
    fs = np.array([500, 1000, 2000, 4000, 6000, 8000, 10000, 12000, 14000, 15000, 16000, 17000])
    ph = []
    for f in fs:
        n = int(0.5 * sr)
        x = NOM * 0.1 * np.sin(2 * np.pi * f * np.arange(n) / sr)
        y = run(so, sr, x, 20, "default", secs_pre=0.05)
        seg = slice(int(0.2 * sr), n)
        t = np.arange(n)[seg] / sr
        A = np.stack([np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)], 1)
        c = np.linalg.lstsq(A, y[seg], rcond=None)[0]
        p = np.arctan2(c[1], c[0]) + 2 * np.pi * f * 0.020     # remove the nominal 20 ms
        ph.append(p)
    ph = np.unwrap(np.array(ph))
    gd = -np.gradient(ph, 2 * np.pi * fs) * 1000
    return {str(int(f)): round(float(g), 4) for f, g in zip(fs, gd)}


def main():
    engs = dict(a.split("=", 1) for a in sys.argv[1:])
    res = {}
    for name, so in engs.items():
        so = os.path.abspath(so)
        r = {"tones": {}, "imd": {}, "phase_group_delay_ms": {}}
        for sr in (44100, 48000, 96000):
            for T in (0, 20):
                for op in OPS:
                    for lv in LEVELS:
                        for f0 in FREQS:
                            x = NOM * 10 ** (lv / 20) * np.sin(2 * np.pi * f0 * np.arange(int(1.25 * sr)) / sr)
                            y = run(so, sr, x, T, op)[int(0.25 * sr):]
                            r["tones"][f"{sr}|T{T}|{op}|{lv}|{f0}"] = analyse_tone(y, sr, f0)
                    for kind in ("SMPTE", "CCIF19/20", "CCIF13/14"):
                        n = int(1.25 * sr); t = np.arange(n) / sr
                        if kind == "SMPTE":
                            x = NOM * 0.25 * (0.8 * np.sin(2 * np.pi * 60 * t) + 0.2 * np.sin(2 * np.pi * 7000 * t))
                        else:
                            f1, f2 = (19000, 20000) if kind == "CCIF19/20" else (13000, 14000)
                            x = NOM * 0.25 * (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t))
                        y = run(so, sr, x, T, op)[int(0.25 * sr):]
                        r["imd"][f"{sr}|T{T}|{op}|{kind}"] = imd(y, sr, kind)
                print(name, sr, "T", T, flush=True)
            r["phase_group_delay_ms"][str(sr)] = phase_gd(so, sr)
        res[name] = r
        json.dump(res, open(os.path.join(OUT, "audit_spectral.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
