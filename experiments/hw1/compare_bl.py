#!/usr/bin/env python3
"""
HW-1 investigation, step 6: full-device A/B, production vs experimental candidate B
(experiments/hw1/build/engine_bl.so built by make_bl.py + tools/gen2c.py).

Identical deterministic signals into both. Writes results/ab_*.json, plots and A/B renders
(audio/*.flac). The production engine and all production files are untouched.
"""
import json, os, subprocess, sys, time, shutil
import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, HERE)
import engine as ENG                     # noqa: E402
from engine import Engine, SO            # noqa: E402
from reproduce import spurs, spectrum, db  # noqa: E402

BL = os.path.join(HERE, "build", "engine_bl.so")
OUT = os.path.join(HERE, "results")
AUD = os.path.join(HERE, "audio")
NOM = 10 ** (-17 / 20)
ENGINES = {"production": None, "candidate_B": BL}


def run(which, sr, x, xr=None, auto=None, **p):
    e = Engine(sr, so=ENGINES[which], **p)
    e.silence(0.1)
    return e.run(x, xr, automation=auto)


def stepped(which, sr, freqs, **p):
    g = {}
    for f in [1000] + list(freqs):
        x = NOM * 0.1 * np.sin(2 * np.pi * f * np.arange(int(0.6 * sr)) / sr)
        y = run(which, sr, x, **p)[0][int(0.3 * sr):]
        fr, S = spectrum(y, sr)
        g[f] = float(db(S[np.argmin(np.abs(fr - f))] / (NOM * 0.1)))
    r = g[1000]
    return {f: round(g[f] - r, 2) for f in freqs}


def ab_spurs():
    rows = []
    for sr in (44100, 48000, 96000):
        for f0 in (100, 1000, 3000, 5000, 8000, 10000, 12000, 14000, 15000, 16000, 17000, 18000, 19000, 20000):
            if f0 > sr / 2 - 300:
                continue
            x = NOM * 0.1 * np.sin(2 * np.pi * f0 * np.arange(sr) / sr)
            r = dict(host=sr, f_in=f0)
            for w in ENGINES:
                y = run(w, sr, x, time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)[0][sr // 2:]
                fr, S = spectrum(y, sr)
                k0 = np.argmin(np.abs(fr - f0)); a0 = S[k0 - 3:k0 + 4].max()
                m = (np.abs(fr - f0) > 25) & (fr > 15) & (fr <= 20000)
                k = int(np.argmax(S * m))
                r[w] = dict(worst_audible_spur_db=round(float(db(S[k] / a0)), 1), spur_hz=float(fr[k]),
                            wanted_db=round(float(db(a0 / (NOM * 0.1))), 2))
            rows.append(r)
    return rows


def ab_conditions():
    """Default character (13-bit, PRE on), feedback, modulation, nominal level; 48 kHz."""
    out = []
    sr = 48000
    conds = [("default character, nominal level", dict(time_ms=0, feedback=0, balance=10), 1.0),
             ("feedback 5 @ 50 ms", dict(time_ms=50, feedback=5, balance=10, converter=1, pre_on=0), 0.1),
             ("modulation INT 2 TRI", dict(time_ms=100, feedback=0, balance=10, converter=1, pre_on=0, intensity=2, frequency=3), 0.1)]
    for name, p, amp in conds:
        for f0 in (10000, 17000):
            x = NOM * amp * np.sin(2 * np.pi * f0 * np.arange(3 * sr) / sr)
            r = dict(condition=name, f_in=f0)
            for w in ENGINES:
                y = run(w, sr, x, **p)[0][sr:]
                fr, S = spectrum(y, sr)
                P = S ** 2
                band = np.abs(fr - f0) < 400            # wanted incl. modulation sidebands
                r[w] = round(float(10 * np.log10(P[(~band) & (fr > 20) & (fr <= 20000)].sum() / P[band].sum())), 1)
            out.append(r)
    return out


def ab_thd():
    sr = 48000
    rows = {}
    for w in ENGINES:
        x = NOM * np.sin(2 * np.pi * 1000 * np.arange(3 * sr) / sr)
        y = run(w, sr, x, time_ms=0, feedback=0, balance=10)[0][sr:sr + 131072]
        win = signal.windows.blackmanharris(len(y))
        S = np.abs(np.fft.rfft(y * win)) ** 2
        fr = np.fft.rfftfreq(len(y), 1 / sr)
        fund = np.abs(fr - 1000) < 30
        band = (fr >= 20) & (fr <= 20000)
        harm = sum(S[np.abs(fr - k * 1000) < 30].sum() for k in range(2, 11))
        rows[w] = dict(thd_pct=round(float(100 * np.sqrt(harm / S[fund].sum())), 4),
                       thdn_pct=round(float(100 * np.sqrt(S[band & ~fund].sum() / S[fund].sum())), 4))
    return rows


def ab_timing():
    """Absolute echo time (impulse peak) and repeat period with feedback; modulation depth."""
    rows = []
    for sr in (44100, 48000, 96000):
        for T in (0, 1, 10, 100, 500, 1023):
            x = np.zeros(int(sr * (T / 1000 + 0.1))); x[0] = 0.5
            r = dict(host=sr, time_ms=T)
            for w in ENGINES:
                y = run(w, sr, x, time_ms=T, feedback=0, balance=10, converter=1)[0]
                i = int(np.argmax(np.abs(y)))
                a, b_, c = np.abs(y[i - 1:i + 2])
                frac = 0.5 * (a - c) / (a - 2 * b_ + c) if (a - 2 * b_ + c) != 0 else 0
                r[w] = round((i + frac) / sr * 1000, 4)
            rows.append(r)
    # feedback repeat period
    sr = 48000
    x = np.zeros(int(sr * 0.6)); x[0] = 0.5
    per = {}
    for w in ENGINES:
        y = run(w, sr, x, time_ms=50, feedback=6, balance=10, converter=1)[0]
        pk, _ = signal.find_peaks(np.abs(y), height=0.05 * np.abs(y).max(), distance=int(0.04 * sr))
        per[w] = [round(float(v) / sr * 1000, 3) for v in np.diff(pk[:6])]
    return rows, per


def ab_modulation():
    """Depth (click train) and rate at INT 10, FREQ 0, TRI."""
    sr = 48000
    n = int(24 * sr)
    x = np.zeros(n); idx = np.arange(int(0.1 * sr), n - int(0.5 * sr), int(0.05 * sr)); x[idx] = 0.5
    r = {}
    for w in ENGINES:
        y = run(w, sr, x, time_ms=400, feedback=0, balance=10, intensity=10, frequency=0, waveform=0, converter=1)[0]
        pk, _ = signal.find_peaks(np.abs(y), height=0.2 * np.abs(y).max(), distance=int(0.02 * sr))
        m = min(len(pk), len(idx))
        ds = (pk[:m] - idx[:m]) / sr * 1000
        ds = ds[idx[:m] > 2 * sr]
        r[w] = dict(min_ms=round(float(ds.min()), 2), max_ms=round(float(ds.max()), 2), ratio=round(float(ds.min() / ds.max()), 4))
    return r


def ab_response():
    out = {}
    pts = [20, 50, 100, 500, 2000, 5000, 8000, 10000, 12500, 15000, 16000, 17000, 18000, 19000]
    for sr in (44100, 48000, 96000):
        out[sr] = {w: stepped(w, sr, [p for p in pts if p < sr / 2 - 300], time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)
                   for w in ENGINES}
    return out


def ab_cpu():
    exe = os.path.join(HERE, "build", "bench")
    subprocess.check_call(["gcc", "-O2", "-o", exe, os.path.join(ROOT, "tests", "bench_engine.c"), "-ldl"])
    res = {}
    for w, so in (("production", SO), ("candidate_B", BL)):
        txt = subprocess.run([exe, so, "quick"], capture_output=True, text=True).stdout
        res[w] = txt.strip().splitlines()[-6:]
    return res


# ---------------------------------------------------------------- musical A/B renders
def musical():
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import musical_eval as ME
    progs = json.load(open(os.path.join(ROOT, "presets", "factory_programs.json")))["programs"]
    os.makedirs(AUD, exist_ok=True)
    rng = np.random.default_rng(31)
    sr = 48000
    # bright material: closed hats + ride-like noise every 1/8 at 75 BPM, plus a rimshot
    beat = 60 / 75.0
    x = np.zeros(int(sr * 7))
    for k in range(16):
        n = int(0.05 * sr)
        hh = signal.lfilter(*signal.butter(4, [7000 / (sr / 2), 16000 / (sr / 2)], "band"), rng.standard_normal(n))
        hh *= np.exp(-np.arange(n) / (0.012 * sr))
        s = int(k * beat / 2 * sr)
        x[s:s + n] += 0.6 * hh / np.abs(hh).max()
    x = x / np.abs(x).max() * NOM            # bright source only: nothing below ~6 kHz
    rows = []
    for pr in progs:
        v = dict(pr["values"])
        v["balance"] = 10                             # wet only: hear the repeats
        o = {w: run(w, sr, np.concatenate([x, np.zeros(4 * sr)]), **v)[:2] for w in ENGINES}
        # inharmonic fold-down: energy below 4 kHz in the wet output (the source has none below ~6 kHz)
        r = dict(program=f"P{pr['slot']} {pr['name']}")
        for w in ENGINES:
            y = o[w][0]
            fr, S = spectrum(y, sr)
            P = S ** 2
            r[w] = dict(energy_below_4k_db=round(float(10 * np.log10(P[(fr > 20) & (fr < 4000)].sum() / P[fr > 20].sum())), 1))
        rows.append(r)
        if pr["slot"] in (1, 4, 7):
            for w in ENGINES:
                save(f"P{pr['slot']}_hats_{w}", o[w])
    # character check on full-range material: 1/3-octave band levels, every program, dense mix
    xd = ME.m_dense()
    xd = np.concatenate([xd * NOM / np.abs(xd).max(), np.zeros(3 * sr)])
    fc = 1000 * 2 ** (np.arange(-15, 13) / 3)          # 31.5 Hz .. 16 kHz
    char = []
    for pr in progs:
        v = dict(pr["values"])
        lv = {}
        for w in ENGINES:
            y = run(w, sr, xd, **v)[0]
            fr, S = spectrum(y, sr)
            P = S ** 2
            lv[w] = np.array([10 * np.log10(P[(fr >= f / 2 ** (1 / 6)) & (fr < f * 2 ** (1 / 6))].sum() + 1e-30) for f in fc])
            if pr["slot"] in (1, 3, 5):
                save(f"P{pr['slot']}_dense_mix_{w}", run(w, sr, xd, **v)[:2])
        d = lv["candidate_B"] - lv["production"]
        lo = d[fc <= 8000]; hi = d[fc > 8000]
        char.append(dict(program=f"P{pr['slot']} {pr['name']}", max_abs_band_diff_31Hz_8k_db=round(float(np.abs(lo).max()), 2),
                         band_diff_10k_12k5_16k_db=[round(float(v), 1) for v in hi]))
    return rows, char


def save(name, y):
    y = np.atleast_2d(y)
    y = y / max(np.abs(y).max(), 1e-9) * 0.7
    wav = os.path.join(AUD, name + ".wav")
    wavfile.write(wav, 48000, (np.clip(y.T, -1, 1) * 32767).astype(np.int16))
    if shutil.which("ffmpeg"):
        subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "flac", "-compression_level", "8",
                               "-fflags", "+bitexact", "-flags:a", "+bitexact", os.path.join(AUD, name + ".flac")])
        os.unlink(wav)


def plots(spr, resp):
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
    for ax, sr in zip(axs, (44100, 48000, 96000)):
        rr = [r for r in spr if r["host"] == sr]
        for w, st in (("production", "o-"), ("candidate_B", "s-")):
            ax.plot([r["f_in"] for r in rr], [r[w]["worst_audible_spur_db"] for r in rr], st, ms=3, label=w)
        ax.set_xscale("log"); ax.grid(alpha=.3); ax.set_title(f"full device, host {sr / 1000:g} kHz"); ax.set_xlabel("input tone (Hz)")
        ax.set_ylim(-170, 0)
    axs[0].set_ylabel("largest unwanted component 20 Hz-20 kHz (dB re tone)"); axs[0].legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "ab_spurs_full_device.png"), dpi=110)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, sr in zip(axs, (44100, 48000, 96000)):
        for w in ("production", "candidate_B"):
            g = resp[sr][w]
            ax.plot(list(g.keys()), list(g.values()), marker="o", ms=3, label=w)
        ax.axhline(-3, color="k", ls="--", lw=.6); ax.axhline(0.5, color="k", ls="--", lw=.6)
        ax.axvline(17000, color="k", ls=":", lw=.6)
        ax.set_xscale("log"); ax.grid(alpha=.3); ax.set_title(f"effect-path response, {sr / 1000:g} kHz"); ax.set_xlabel("Hz")
    axs[0].set_ylabel("dB re 1 kHz"); axs[0].legend(); axs[0].set_ylim(-8, 3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "ab_response_full_device.png"), dpi=110)
    fig, ax = plt.subplots(figsize=(10, 4))
    for w in ENGINES:
        x = NOM * 0.1 * np.sin(2 * np.pi * 17000 * np.arange(48000) / 48000)
        y = run(w, 48000, x, time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)[0][24000:]
        fr, S = spectrum(y, 48000)
        ax.plot(fr, db(S / (NOM * 0.1)), lw=.8, label=w)
    ax.set_xlim(0, 24000); ax.set_ylim(-180, 5); ax.grid(alpha=.3); ax.legend(); ax.set_xlabel("Hz"); ax.set_ylabel("dB re input")
    ax.set_title("full device, 17 kHz tone, 48 kHz host (CLEAN, PRE off)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "ab_spectrum_17k_48k.png"), dpi=110)


def main():
    os.makedirs(OUT, exist_ok=True)
    ENG.build()
    R = {}
    R["spurs"] = ab_spurs(); print("spurs done")
    R["conditions"] = ab_conditions(); print("conditions", R["conditions"])
    R["thd"] = ab_thd(); print("thd", R["thd"])
    R["timing"], R["feedback_period_ms"] = ab_timing(); print("timing", R["feedback_period_ms"])
    R["modulation"] = ab_modulation(); print("mod", R["modulation"])
    R["response"] = ab_response(); print("response done")
    R["cpu"] = ab_cpu(); print("cpu", R["cpu"])
    R["musical_foldown"], R["musical_character"] = musical(); print("musical", R["musical_foldown"], R["musical_character"])
    json.dump(R, open(os.path.join(OUT, "ab_full_device.json"), "w"), indent=1, default=str)
    plots(R["spurs"], R["response"])


if __name__ == "__main__":
    main()
