#!/usr/bin/env python3
"""
HW-1 investigation, steps 2-3: attribution and candidate evaluation on the isolated
conversion-core model (convmodel.py). Writes results/candidates.json and plots.
"""
import json, os, time
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import convmodel as C
from reproduce import spurs, spectrum, db

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
CANDS = ["production", "A_cubic_foh", "B_bandlimited", "C_os4"]
RATES = (44100, 48000, 96000)
SWEEP = [100, 200, 500, 1000, 2000, 3000, 5000, 7000, 8000, 10000, 12000, 14000, 15000, 16000, 17000, 18000, 19000, 20000]
AMP = 0.01


def quant13(q):
    """12-bit + range bit, as documented (independent re-statement)."""
    big = np.abs(q) >= 0.5
    return np.where(big, np.round(q * 2048) / 2048, np.round(q * 4096) / 4096)


def tone(f, fs, secs=1.0, amp=AMP):
    return amp * np.sin(2 * np.pi * f * np.arange(int(secs * fs)) / fs)


def worst_spur(name, fs, freqs=SWEEP):
    rows = []
    for f0 in freqs:
        if f0 >= fs / 2 - 300:
            continue
        y = C.run_candidate(name, tone(f0, fs), fs)[fs // 2:]
        a0, sp = spurs(y, fs, f0, n=2, floor_db=-200)
        rows.append((f0, sp[0] if sp else None))
    w = max(rows, key=lambda r: r[1][1] if r[1] else -999)
    return w, rows


def passband(name, fs):
    pts = [20, 50, 100, 1000, 5000, 10000, 15000, 17000]
    g = {}
    for f0 in pts:
        y = C.run_candidate(name, tone(f0, fs, 1.0), fs)[fs // 2:]
        fr, S = spectrum(y, fs)
        g[f0] = float(db(S[np.argmin(np.abs(fr - f0))] / AMP))
    r = g[1000]
    return {k: round(v - r, 2) for k, v in g.items()}


def latency(name, fs):
    n = fs // 2
    x = np.zeros(n); x[1000] = 1.0
    x = signal.lfilter(*signal.butter(4, 8000 / (fs / 2)), x)        # band-limited click
    y = C.run_candidate(name, x * 0.1, fs)
    c = signal.correlate(y, x, mode="full")
    k = np.argmax(c) - (len(x) - 1)
    return float(k / fs * 1000)


def modulated(name, fs, f0=17000):
    """Clock modulated like INTENSITY 2, TRI 0.45 Hz: fv = 64k * (1 + 0.2 * tri)."""
    secs = 4.0
    n = int(secs * fs)
    tri = signal.sawtooth(2 * np.pi * 0.45 * np.arange(n) / fs, 0.5) * 0.5 + 0.5
    fv = 64000 * (1 + 0.2 * tri)
    y = C.run_candidate(name, tone(f0, fs, secs), fs, mod=fv)[fs:]
    fr, S = spectrum(y, fs)
    P = S ** 2
    band = np.abs(fr - f0) < 300
    return float(10 * np.log10(P[~band & (fr > 20)].sum() / P[band].sum()))


def quant_char(name, fs):
    """Converter character preserved? 1 kHz at -10 dB re full scale, 13-bit on vs off:
    error power relative to the signal (the gain-ranged quantisation 'grain')."""
    x = tone(1000, fs, 1.5, amp=0.316)
    a = C.run_candidate(name, x, fs, quant=quant13)[fs // 2:]
    b = C.run_candidate(name, x, fs)[fs // 2:]
    return float(db(np.sqrt(np.mean((a - b) ** 2)) / np.sqrt(np.mean(b ** 2))))


def macs(name, fs, taps=32, fv=64000.0):
    """Multiply-accumulates per host sample per channel for the conversion only (estimate)."""
    tps = fv / fs
    if name == "production":
        return round(tps * (2 + 2), 1)                     # lerp + ZOH accumulate
    if name == "A_cubic_foh":
        return round(tps * 10 + 8 * 2, 1)
    if name.startswith("B_"):
        # per tick: taps MACs + taps kernel lookups (table + lerp ~2 MAC) for the input;
        # per host sample: ~taps*tps scattered output taps with lookup
        return round(tps * taps * 3 + taps * tps * 3, 1)
    if name == "C_os4":
        # 2 x (halfband up 2 stages ~ 24 + 12 taps, polyphase -> ~half) + same down, conversion at 4x
        return round((12 + 6) * 2 + (12 + 6) * 2 * 4 / 4 + tps * 4, 1)
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    R = {}
    for name in CANDS:
        t0 = time.time()
        r = dict(worst_spur={}, sweep={}, passband={}, latency_ms={}, modulated_17k_db={}, quant_error_db={}, macs={})
        for fs in RATES:
            w, rows = worst_spur(name, fs)
            r["worst_spur"][fs] = dict(f_in=w[0], spur_hz=w[1][0] if w[1] else None, rel_db=w[1][1] if w[1] else None)
            r["sweep"][fs] = rows
            r["passband"][fs] = passband(name, fs)
            r["latency_ms"][fs] = round(latency(name, fs), 3)
            r["modulated_17k_db"][fs] = round(modulated(name, fs), 1) if fs <= 48000 else round(modulated(name, fs, 15000), 1)
            r["quant_error_db"][fs] = round(quant_char(name, fs), 1)
            r["macs"][fs] = macs(name, fs)
        r["model_runtime_s"] = round(time.time() - t0, 1)
        R[name] = r
        print(name, json.dumps({k: r[k] for k in ("worst_spur", "latency_ms", "modulated_17k_db", "quant_error_db", "macs")}))
    json.dump(R, open(os.path.join(OUT, "candidates.json"), "w"), indent=1, default=str)
    # ---- plots: worst spur vs input frequency, per rate
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
    for ax, fs in zip(axs, RATES):
        for name in CANDS:
            rows = R[name]["sweep"][fs]
            ax.plot([r[0] for r in rows], [r[1][1] if r[1] else -200 for r in rows], marker="o", ms=3, label=name)
        ax.set_title(f"host {fs / 1000:g} kHz: largest unwanted component")
        ax.set_xscale("log"); ax.set_xlabel("input tone (Hz)"); ax.grid(alpha=.3); ax.set_ylim(-170, 0)
    axs[0].set_ylabel("dB re wanted tone"); axs[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "spurs_vs_frequency.png"), dpi=110)
    # ---- spectra for the 17 kHz case at 48 kHz
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for name in CANDS:
        y = C.run_candidate(name, tone(17000, 48000), 48000)[24000:]
        fr, S = spectrum(y, 48000)
        ax.plot(fr, db(S / AMP), lw=0.8, label=name)
    ax.set_xlim(0, 24000); ax.set_ylim(-180, 5); ax.grid(alpha=.3); ax.legend(fontsize=8)
    ax.set_title("17 kHz tone through the conversion core, 48 kHz host"); ax.set_xlabel("Hz"); ax.set_ylabel("dB re input")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "spectrum_17k_48k.png"), dpi=110)
    # ---- passband
    fig, ax = plt.subplots(figsize=(8, 4))
    for name in CANDS:
        pb = R[name]["passband"][48000]
        ax.plot(list(pb.keys()), list(pb.values()), marker="o", label=name)
    ax.axhline(-3, color="k", lw=0.6, ls="--"); ax.set_xscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    ax.set_title("conversion-core response re 1 kHz, 48 kHz host (before the droop EQ)"); ax.set_xlabel("Hz"); ax.set_ylabel("dB")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "passband_48k.png"), dpi=110)


if __name__ == "__main__":
    main()
