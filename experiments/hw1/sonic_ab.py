#!/usr/bin/env python3
"""
HW-1 remediation: sonic-identity A/B, production vs candidate D, ALL nine factory programs.

Material (synthesised, seeded; tests/musical_eval.py generators): dense dub mix, rimshot, kick+snare,
organ skank, dub bass, and a bright hats/ride figure (nothing below ~6 kHz).

Per program it reports:
  * 1/3-octave band levels of the full output (dense mix), 31.5 Hz-16 kHz: difference D - production
  * top octave in detail: 10, 12.5, 16 kHz bands
  * fold-down: energy below 4 kHz in the wet output for the bright hats figure (images land there)
  * transients: rimshot repeats - per-repeat peak level, crest factor and waveform correlation
    (after alignment) between engines, repeats 1..6
  * feedback-filter behaviour: per-repeat band levels (1/2/4/8/12/16 kHz) of a click train
Renders: every program, dense mix, production and D with ONE common gain per pair (level differences
are audible as they are), FLAC 16-bit 48 kHz, 6 s. Writes results/sonic_ab.json and audio_d/*.flac.
"""
import json, os, shutil, subprocess, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, HERE)
from engine import Engine  # noqa
import musical_eval as ME  # noqa
from reproduce import spectrum  # noqa

SR = 48000
NOM = 10 ** (-17 / 20)
OUT = os.path.join(HERE, "results")
AUD = os.path.join(HERE, "audio_d")
ENG = {"production": os.path.join(ROOT, "build", "engine.so"),
       "candidate_D": os.path.join(HERE, "build", "engine_d.so")}
FC = 1000 * 2 ** (np.arange(-15, 13) / 3)      # 31.5 Hz .. 16 kHz


def run(so, x, tail=4.0, **p):
    xx = np.concatenate([x, np.zeros(int(tail * SR))])
    e = Engine(SR, so=so, **p)
    e.silence(0.1)
    return e.run(xx)[:2]


def bands(y):
    fr, S = spectrum(y, SR)
    P = S ** 2
    return np.array([10 * np.log10(P[(fr >= f / 2 ** (1 / 6)) & (fr < f * 2 ** (1 / 6))].sum() + 1e-30) for f in FC])


def hats():
    rng = np.random.default_rng(31)
    x = np.zeros(int(SR * 7))
    for k in range(16):
        n = int(0.05 * SR)
        hh = signal.lfilter(*signal.butter(4, [7000 / (SR / 2), 16000 / (SR / 2)], "band"), rng.standard_normal(n))
        hh *= np.exp(-np.arange(n) / (0.012 * SR))
        s = int(k * ME.BEAT / 2 * SR)
        x[s:s + n] += 0.6 * hh / np.abs(hh).max()
    return x / np.abs(x).max() * NOM


def norm(x):
    return x / np.abs(x).max() * NOM


def rim_repeats(y, T_ms, k_max=6, t0=0.1):
    """Segments of the k-th repeat of a single rimshot placed at t0."""
    segs = []
    for k in range(1, k_max + 1):
        c = int((t0 + k * T_ms / 1000) * SR)
        a, b = c - int(0.004 * SR), c + int(0.03 * SR)
        if b < len(y):
            segs.append(y[a:b])
    return segs


def save_pair(name, ys):
    os.makedirs(AUD, exist_ok=True)
    g = 0.7 / max(max(np.abs(y).max() for y in ys.values()), 1e-9)   # one gain for the pair
    for w, y in ys.items():
        y = np.atleast_2d(y)[:, :int(6 * SR)] * g
        wav = os.path.join(AUD, f"{name}_{w}.wav")
        wavfile.write(wav, SR, (np.clip(y.T, -1, 1) * 32767).astype(np.int16))
        if shutil.which("ffmpeg"):
            subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "flac", "-compression_level", "8",
                                   "-fflags", "+bitexact", "-flags:a", "+bitexact", wav[:-4] + ".flac"])
            os.unlink(wav)


def main():
    if len(sys.argv) > 1:
        ENG["candidate_D"] = os.path.abspath(sys.argv[1])
    progs = json.load(open(os.path.join(ROOT, "presets", "factory_programs.json")))["programs"]
    dense = norm(ME.m_dense())
    hh = hats()
    rim = np.zeros(int(0.1 * SR)); rim = np.concatenate([rim, norm(ME.rimshot())])
    clicks = np.zeros(int(0.2 * SR)); clicks[int(0.1 * SR)] = 0.5
    res = []
    for pr in progs:
        v = dict(pr["values"])
        name = f"P{pr['slot']} {pr['name']}"
        r = {"program": name}
        # 1. dense mix, programme balance (what the user hears)
        o = {w: run(so, dense, **v) for w, so in ENG.items()}
        d = bands(o["candidate_D"][0]) - bands(o["production"][0])
        r["dense_band_diff_db"] = {f"{f:.0f}": round(float(x), 2) for f, x in zip(FC, d)}
        r["dense_max_abs_diff_31Hz_8k_db"] = round(float(np.abs(d[FC <= 8100]).max()), 2)
        r["dense_diff_10k_12k5_16k_db"] = [round(float(x), 2) for x in d[FC > 9000]]
        rms = {w: float(np.sqrt(np.mean(o[w][0] ** 2))) for w in o}
        r["dense_level_diff_db"] = round(20 * np.log10(rms["candidate_D"] / rms["production"]), 2)
        save_pair(f"P{pr['slot']}_dense", o)
        # 2. bright hats, wet only: fold-down below 4 kHz
        vw = dict(v); vw["balance"] = 10
        fd = {}
        for w, so in ENG.items():
            y = run(so, hh, **vw)[0]
            fr, S = spectrum(y, SR); P = S ** 2
            fd[w] = round(float(10 * np.log10(P[(fr > 20) & (fr < 4000)].sum() / P[fr > 20].sum())), 1)
        r["hats_wet_energy_below_4k_db"] = fd
        # 3. transients: rimshot repeats (wet only)
        ro = {w: run(so, rim, tail=3.0, **vw)[0] for w, so in ENG.items()}
        T = v["time_ms"] if not v.get("sync") else None
        if T and T >= 20 and v.get("intensity", 0) <= 1.5:
            sp, sd = rim_repeats(ro["production"], T), rim_repeats(ro["candidate_D"], T)
            rows = []
            for k, (a, b) in enumerate(zip(sp, sd), 1):
                if np.abs(a).max() < 1e-6:
                    break
                c = signal.correlate(b, a, "full"); lag = np.argmax(np.abs(c)) - (len(a) - 1)
                bb = np.roll(b, -lag)
                corr = float(np.dot(a, bb) / np.sqrt(np.dot(a, a) * np.dot(bb, bb)))
                rows.append(dict(repeat=k, peak_diff_db=round(20 * np.log10(np.abs(b).max() / np.abs(a).max()), 2),
                                 crest_prod_db=round(20 * np.log10(np.abs(a).max() / np.sqrt(np.mean(a ** 2))), 2),
                                 crest_D_db=round(20 * np.log10(np.abs(b).max() / np.sqrt(np.mean(b ** 2))), 2),
                                 waveform_corr=round(corr, 4), lag_us=round(lag / SR * 1e6, 1)))
            r["rimshot_repeats"] = rows
        # 4. feedback filters: click train, per-repeat band levels
        if T and T >= 50 and v.get("feedback", 0) > 0 and v.get("intensity", 0) <= 1.5:
            co = {w: run(so, clicks, tail=3.0, **vw)[0] for w, so in ENG.items()}
            fb = []
            for k in range(1, 6):
                c = int((0.1 + k * T / 1000) * SR)
                if c + int(0.02 * SR) > len(co["production"]):
                    break
                seg = {w: co[w][c - int(0.002 * SR): c + int(0.02 * SR)] for w in co}
                if np.abs(seg["production"]).max() < 1e-7:
                    break
                row = {"repeat": k}
                for fb_f in (1000, 2000, 4000, 8000, 12000, 16000):
                    lv = {}
                    for w, s in seg.items():
                        H = np.abs(np.fft.rfft(s * np.hanning(len(s)), 8192)); fr = np.fft.rfftfreq(8192, 1 / SR)
                        lv[w] = 20 * np.log10(np.mean(H[(fr > fb_f / 1.12) & (fr < fb_f * 1.12)]) + 1e-12)
                    row[f"{fb_f}"] = round(lv["candidate_D"] - lv["production"], 2)
                fb.append(row)
            r["feedback_repeat_band_diff_db"] = fb
        res.append(r)
        print(name, "dense max|diff| 31-8k %.2f dB, top %s, level %+.2f dB, hats<4k %s" % (
            r["dense_max_abs_diff_31Hz_8k_db"], r["dense_diff_10k_12k5_16k_db"], r["dense_level_diff_db"], fd), flush=True)
    json.dump(dict(note="production vs candidate D, all factory programs (see docstring)", programs=res),
              open(os.path.join(OUT, "sonic_ab.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
