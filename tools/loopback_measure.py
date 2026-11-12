#!/usr/bin/env python3
"""
ECHOLIVITY SDD-3000 -- optional physical measurement through an audio interface.

Measures the device *as it runs in Ableton Live* (or any other unit) through a real audio
interface, with the interface's own loopback measured first and divided out. This measures
the software in Live through your converters; it does NOT establish equivalence to an
original 1982 SDD-3000.

  generate  -> writes the stimulus WAV (sync click, level tones, log sweep, silence) + a manifest
               (the capture chain's latency must be below 1.9 s)
  analyze   -> loopback capture + device capture -> latency, frequency response (loopback
               removed), 1 kHz THD / total distortion, noise floor, clipping check, report

Workflow (details: docs/validation/HARDWARE_MEASUREMENT.md):
  1. python3 tools/loopback_measure.py generate --rate 48000 --out stim.wav
  2. Loopback: cable interface OUT 1 -> IN 1. Play stim.wav from a Live audio track routed to
     OUT 1, record IN 1 on another track (Monitor Off) -> loopback.wav
  3. Device: same chain with ECHOLIVITY on the playback track (e.g. TIME 0, FB 0, BAL 10,
     CLEAN) -> device.wav. Do not touch interface gains between steps 2 and 3.
  4. python3 tools/loopback_measure.py analyze --stimulus stim.wav --loopback loopback.wav \
        --device device.wav --conditions "Live 12.1, RME Babyface, 48 kHz, buffer 256" --out report
"""
import argparse, json, os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

LAYOUT = [  # (name, seconds)
    ("silence_pre", 1.0), ("click", 2.0), ("tone_1k_-20", 3.0), ("tone_1k_-10", 3.0),
    ("gap", 0.5), ("sweep", 8.0), ("gap2", 1.0), ("silence_noise", 3.0), ("tail", 1.0)]
SWEEP = (10.0, 22000.0)


def build_stimulus(sr):
    parts, marks, t = [], {}, 0
    for name, secs in LAYOUT:
        n = int(secs * sr)
        x = np.zeros(n)
        tt = np.arange(n) / sr
        if name == "click":
            x[int(0.1 * sr)] = 0.5
        elif name.startswith("tone_1k"):
            lvl = float(name.split("_")[-1])
            x = 10 ** (lvl / 20) * np.sin(2 * np.pi * 1000 * tt)
            x[:int(0.01 * sr)] *= np.linspace(0, 1, int(0.01 * sr))
            x[-int(0.01 * sr):] *= np.linspace(1, 0, int(0.01 * sr))
        elif name == "sweep":
            f1, f2 = SWEEP
            L = secs / np.log(f2 / f1)
            x = 10 ** (-30 / 20) * np.sin(2 * np.pi * f1 * L * (np.exp(tt / L) - 1))   # -30 dBFS: below the device overload
            fade = int(0.02 * sr)
            x[:fade] *= np.linspace(0, 1, fade); x[-fade:] *= np.linspace(1, 0, fade)
        marks[name] = (t, t + n)
        parts.append(x)
        t += n
    return np.concatenate(parts), marks


def read(path):
    sr, x = wavfile.read(path)
    if x.dtype.kind == "i":
        x = x / float(np.iinfo(x.dtype).max)
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x[:, 0]
    return sr, x


def align(stim, cap, sr, marks):
    """Latency from the sync click (cross-correlation over the first 2 s)."""
    a, b = marks["click"]
    # the click sits 0.1 s into a 2 s silent section: search only up to the end of that section
    # (latency < 1.9 s), so later tones can never be mistaken for the click
    click_at = a + int(0.1 * sr)
    win = np.abs(cap[:b])
    return int(np.argmax(win)) - click_at


def sweep_ir(stim, cap, sr, marks):
    a, b = marks["sweep"]
    x = stim[a:b]
    y = cap[a:b + int(1.0 * sr)]
    secs = (b - a) / sr
    L = secs / np.log(SWEEP[1] / SWEEP[0])
    inv = x[::-1] * np.exp(-np.arange(len(x)) / sr / L)
    ir = signal.fftconvolve(y, inv)
    k = int(np.argmax(np.abs(ir)))
    seg = ir[max(k - 4096, 0):k + 65536]
    H = np.abs(np.fft.rfft(seg * signal.windows.tukey(len(seg), 0.1), 1 << 17))
    f = np.fft.rfftfreq(1 << 17, 1 / sr)
    return f, H


def tone_metrics(cap, sr, marks, name):
    a, b = marks[name]
    y = cap[a + int(0.5 * sr): b - int(0.5 * sr)]
    w = signal.windows.blackmanharris(len(y))
    S = np.abs(np.fft.rfft(y * w)) ** 2
    fr = np.fft.rfftfreq(len(y), 1 / sr)
    fund = np.abs(fr - 1000) < 30
    band = (fr >= 20) & (fr <= 20000)
    harm = sum(S[np.abs(fr - k * 1000) < 30].sum() for k in range(2, 11))
    t = np.arange(len(y)) / sr
    amp = np.hypot(2 * np.mean(y * np.sin(2 * np.pi * 1000 * t)), 2 * np.mean(y * np.cos(2 * np.pi * 1000 * t)))
    return dict(level_dbfs_peak=float(20 * np.log10(amp + 1e-30)),
                thd_pct=float(100 * np.sqrt(harm / S[fund].sum())),
                total_distortion_noise_pct=float(100 * np.sqrt(S[band & ~fund].sum() / S[fund].sum())))


def analyze(args):
    sr_s, stim = read(args.stimulus)
    _, marks = build_stimulus(sr_s)
    caps = {}
    for key in ("loopback", "device"):
        sr, cap = read(getattr(args, key))
        if sr != sr_s:
            sys.exit(f"{key}: sample rate {sr} != stimulus {sr_s}")
        lag = align(stim, cap, sr, marks)
        cap = cap[lag:lag + len(stim) + sr]
        caps[key] = dict(cap=cap, lag=lag, peak_dbfs=float(20 * np.log10(np.abs(cap).max() + 1e-30)))
    sr = sr_s
    rep = dict(conditions=args.conditions, sample_rate=sr, warnings=[])
    for key, c in caps.items():
        rep[f"{key}_latency_samples"] = c["lag"]
        rep[f"{key}_peak_dbfs"] = round(c["peak_dbfs"], 2)
        if c["peak_dbfs"] > -1.0:
            rep["warnings"].append(f"{key}: capture peaks at {c['peak_dbfs']:.1f} dBFS -- possible clipping, lower the levels and repeat")
    rep["device_latency_re_loopback_samples"] = caps["device"]["lag"] - caps["loopback"]["lag"]
    f, Hl = sweep_ir(stim, caps["loopback"]["cap"], sr, marks)
    _, Hd = sweep_ir(stim, caps["device"]["cap"], sr, marks)
    rel = 20 * np.log10(np.maximum(Hd, 1e-12) / np.maximum(Hl, 1e-12))
    rel -= np.interp(1000, f, rel)
    pts = [20, 50, 100, 500, 1000, 2000, 5000, 10000, 15000, 17000, 20000]
    rep["response_re_loopback_db"] = {str(p): round(float(np.interp(p, f, rel)), 2) for p in pts if p < sr / 2}
    for key, c in caps.items():
        rep[f"{key}_tone_-10"] = tone_metrics(c["cap"], sr, marks, "tone_1k_-10")
        rep[f"{key}_tone_-20"] = tone_metrics(c["cap"], sr, marks, "tone_1k_-20")
        a, b = marks["silence_noise"]
        n = c["cap"][a + int(0.5 * sr):b - int(0.5 * sr)]
        rep[f"{key}_noise_floor_dbfs"] = round(float(20 * np.log10(np.sqrt(np.mean(n ** 2)) + 1e-30)), 1)
    rep["note"] = ("Response is the device capture divided by the loopback capture (interface response and "
                   "level removed). Distortion/noise figures include the interface; compare with the loopback "
                   "figures. These are measurements of the software through this interface, not of an original unit.")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    json.dump(rep, open(args.out + ".json", "w"), indent=1)
    L = [f"# Loopback measurement", "", f"Conditions: {args.conditions}", f"Sample rate: {sr} Hz", ""]
    L += [f"- {k}: {v}" for k, v in rep.items() if k not in ("conditions", "sample_rate")]
    open(args.out + ".md", "w").write("\n".join(L) + "\n")
    print(json.dumps(rep, indent=1))
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--rate", type=int, default=48000)
    g.add_argument("--out", default="stim.wav")
    a = sub.add_parser("analyze")
    for k in ("stimulus", "loopback", "device", "out"):
        a.add_argument("--" + k, required=True)
    a.add_argument("--conditions", default="(not recorded)")
    args = ap.parse_args()
    if args.cmd == "generate":
        x, marks = build_stimulus(args.rate)
        wavfile.write(args.out, args.rate, (x * 0.999 * 2147483647).astype(np.int32))
        json.dump(dict(rate=args.rate, layout=LAYOUT, marks={k: list(v) for k, v in marks.items()}),
                  open(os.path.splitext(args.out)[0] + "_manifest.json", "w"), indent=1)
        print(f"wrote {args.out} ({len(x) / args.rate:.1f} s, 32-bit PCM)")
    else:
        analyze(args)


if __name__ == "__main__":
    main()
