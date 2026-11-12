#!/usr/bin/env python3
"""
ECHOLIVITY SDD-3000 -- hardware-reference validation suite.

Compares the device's DSP (the C build of the exact gen~ code, tests/engine.py) against the
independent reference models in reference_models.py, i.e. against what the 1982 Korg
documentation specifies -- NOT against the implementation's own constants.

Every result carries: measured value, reference value + source, tolerance, verdict.
Verdicts:
  CONSISTENT     measured within the tolerance derived from the documentation
  INCONSISTENT   outside it (a discrepancy to investigate; nothing is auto-"fixed")
  REPORTED       documentation gives no usable reference (UNKNOWN); number recorded only
  NOT COMPARABLE the quantity isn't modelled by design (e.g. analog noise floor)

This is a measurement of software against documents. It is not a hardware comparison and
cannot establish equivalence to an original unit.

Run:  python3 tests/hwref/hw_validation.py   (writes docs/validation/HARDWARE_VALIDATION.{json,md})
"""
import json, os, sys, time
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from engine import Engine, ROOT, build          # noqa: E402
import reference_models as RM                   # noqa: E402

SR = 48000
NOM = 10 ** (-17 / 20)       # project calibration: +4 dBm nominal -> -17 dBFS (peak) in Live (MANUAL)
# Transfer-function stimuli run 20 dB below nominal: the 50/15 us pre-emphasis lifts broadband HF
# content by up to ~10 dB, and noise/multitone peaks at nominal would reach the converter's
# overload point and make a linear transfer estimate invalid (found during development of this suite).
LIN = NOM * 0.1
OUT_JSON = os.path.join(ROOT, "docs", "validation", "HARDWARE_VALIDATION.json")
OUT_MD = os.path.join(ROOT, "docs", "validation", "HARDWARE_VALIDATION.md")
RES = []
RNG = np.random.default_rng(3000)


def dbm_amp(dbm):
    """dBm (project calibration) -> sample amplitude. A calibration of this software, not hardware."""
    return NOM * 10 ** ((dbm - 4.0) / 20)


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-30))


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2) + 1e-300))


def rec(area, name, measured, reference, tol, verdict, source, signal_used, method):
    RES.append(dict(area=area, name=name, measured=measured, reference=reference, tolerance=tol,
                    verdict=verdict, source=source, signal=signal_used, method=method))
    print(f"[{verdict:14s}] {area}: {name}: {measured}")


# ------------------------------------------------------------------ deterministic signals
def sig_impulse(n, at=0, a=0.5):
    x = np.zeros(n); x[at] = a; return x


def sig_sine(f, secs, amp):
    return amp * np.sin(2 * np.pi * f * np.arange(int(secs * SR)) / SR)


def sig_logsweep(f1, f2, secs, amp):
    t = np.arange(int(secs * SR)) / SR
    L = secs / np.log(f2 / f1)
    return amp * np.sin(2 * np.pi * f1 * L * (np.exp(t / L) - 1)), L


def sig_noise(secs, amp):
    return amp * RNG.standard_normal(int(secs * SR)) / 3.0


def sig_multitone(freqs, secs, amp):
    t = np.arange(int(secs * SR)) / SR
    ph = RNG.uniform(0, 2 * np.pi, len(freqs))
    x = sum(np.sin(2 * np.pi * f * t + p) for f, p in zip(freqs, ph))
    return amp * x / np.abs(x).max()


def sig_percussion(amp):
    n = int(0.2 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.04) +
         RNG.standard_normal(n) * np.exp(-t / 0.008))
    return amp * y / np.abs(y).max()


def run(x, xr=None, pre=0.05, **p):
    e = Engine(SR, **p)
    e.silence(pre)
    return e.run(x, xr)


# ------------------------------------------------------------------ helpers
def parabolic_peak(y):
    i = int(np.argmax(np.abs(y)))
    if 0 < i < len(y) - 1:
        a, b, c = np.abs(y[i - 1]), np.abs(y[i]), np.abs(y[i + 1])
        d = (a - 2 * b + c)
        return i + (0.5 * (a - c) / d if d != 0 else 0.0)
    return float(i)


def xcorr_lag(x, y, maxlag):
    c = signal.correlate(y[:len(x) + maxlag], x, mode="full", method="fft")[len(x) - 1:len(x) - 1 + maxlag]
    return parabolic_peak(c)


def h1_response(x, y, nper=16384):
    f, pxy = signal.csd(x, y, fs=SR, nperseg=nper)
    _, pxx = signal.welch(x, fs=SR, nperseg=nper)
    return f, np.abs(pxy / pxx)


def sweep_response(x, y, L, f1, nfft=None):
    """Farina log-sweep deconvolution (inverse filter with -6 dB/oct amplitude envelope)."""
    t = np.arange(len(x)) / SR
    inv = x[::-1] * np.exp(-t / L)
    ir = signal.fftconvolve(y, inv)
    k = int(np.argmax(np.abs(ir)))
    seg = ir[k - 2048:k + 8192] * signal.windows.tukey(10240, 0.1)
    H = np.abs(np.fft.rfft(seg, 65536))
    f = np.fft.rfftfreq(65536, 1 / SR)
    return f, H


def stepped_sine_db(freqs, ref_f=1000.0, amp=None, absolute=False, **p):
    """Gain of each frequency measured ALONE (one tone per run): valid for a non-time-invariant
    system. The 64 kHz clock emulation inside a 44.1/48 kHz host is not LTI (it creates alias
    components), so multitone/noise/sweep estimates are biased by aliases; this is the primary
    frequency-response method of the suite."""
    amp = LIN if amp is None else amp
    out = {}
    for f in [ref_f] + [q for q in freqs if q != ref_f]:
        x = sig_sine(f, 0.6, amp)
        y = run(x, **p)[0][int(0.3 * SR):]
        xs = x[int(0.3 * SR):]
        n = len(y)
        w = signal.windows.blackmanharris(n)
        fr = np.fft.rfftfreq(n, 1 / SR)
        k = int(np.argmin(np.abs(fr - f)))
        Y = np.abs(np.fft.rfft(y * w))[k - 2:k + 3].max()
        X = np.abs(np.fft.rfft(xs * w))[k - 2:k + 3].max()
        out[f] = float(db(Y / X))
    r = 0.0 if absolute else out[ref_f]
    return {f: out[f] - r for f in freqs}


def at(f, H, fq):
    return float(np.interp(fq, f, H))


def thd(y, f0, nh=10):
    w = signal.windows.blackmanharris(len(y))
    S = np.abs(np.fft.rfft(y * w)) ** 2
    fr = np.fft.rfftfreq(len(y), 1 / SR)
    def band(fc):
        m = np.abs(fr - fc) < 3 * SR / len(y)
        return S[m].sum()
    p1 = band(f0)
    ph = sum(band(k * f0) for k in range(2, nh + 1) if k * f0 < SR / 2 - 200)
    return 100 * np.sqrt(ph / p1)


def thdn_aw(y, f0):
    """THD+N, A-weighted, 20 Hz-20 kHz: fundamental removed by spectral notch (+-30 Hz)."""
    w = signal.windows.blackmanharris(len(y))
    S = np.abs(np.fft.rfft(y * w)) ** 2
    fr = np.fft.rfftfreq(len(y), 1 / SR)
    aw = 10 ** (RM.a_weighting_db(np.maximum(fr, 1)) / 10)
    band = (fr >= 20) & (fr <= 20000)
    fund = np.abs(fr - f0) < 30
    p1 = (S[fund]).sum()
    pn = (S[band & ~fund] * aw[band & ~fund]).sum()
    return pn, p1


# ================================================================== measurements
def m_delay_timing():
    base = None
    errs = []
    for T in (0, 1, 10, 100, 333, 500, 1023):
        n = int(SR * (T / 1000 + 0.15))
        y = run(sig_impulse(n), time_ms=T, feedback=0, balance=10)[0]
        pk = parabolic_peak(y) / SR * 1000
        if base is None:
            base = pk
            continue
        exp, tol = RM.hw_delay_ms(T)
        errs.append((T, pk - base, exp))
    worst = max(abs(m - e) for _, m, e in errs)
    exp, tol = RM.hw_delay_ms(1)
    rec("Delay", "delay time 1-1023 ms (impulse)", f"worst |error| {worst * 1000:.2f} us; path latency {base * 1000:.1f} us",
        "integer ms (1 ms step)", f"+-{tol * 1000:.1f} us (one 64 kHz clock)",
        "CONSISTENT" if worst <= tol else "INCONSISTENT", "SM p.1; SM p.15 sec.5", "impulse", "parabolic peak, TIME 0 as latency reference")
    # 1 ms step: 100.4 requested -> 100
    y = run(sig_impulse(int(SR * 0.25)), time_ms=100.4, time_mode=0, feedback=0, balance=10)[0]
    m = parabolic_peak(y) / SR * 1000 - base
    rec("Delay", "1 ms step (100.4 ms requested)", f"{m:.4f} ms", "100 ms", "+-15.6 us",
        "CONSISTENT" if abs(m - 100) <= tol else "INCONSISTENT", "SM p.1", "impulse", "authentic 1 ms mode")
    # percussion (transient) gives the same delay as the impulse
    x = np.concatenate([sig_percussion(NOM), np.zeros(int(SR * 0.6))])
    y = run(x, time_ms=333, feedback=0, balance=10)[0]
    lag = xcorr_lag(x[:int(0.2 * SR)], y, int(0.5 * SR)) / SR * 1000 - base
    rec("Delay", "delay with a transient (percussion, cross-correlation)", f"{lag:.4f} ms", "333 ms", "+-15.6 us",
        "CONSISTENT" if abs(lag - 333) <= tol else "INCONSISTENT", "SM p.1", "transient percussion", "cross-correlation lag")


RESP_F = [20, 31.5, 50, 100, 200, 500, 2000, 4000, 6000, 8000, 10000, 12500, 14000, 15000, 16000, 17000]


def m_frequency_response():
    flo, fhi, dmin, dmax = RM.response_mask("effect")
    for host in (48000, 44100, 96000):
        global SR
        sr0, SR = SR, host
        try:
            g = stepped_sine_db([f for f in RESP_F if f <= min(fhi, host / 2 - 100)],
                                time_ms=0, feedback=0, balance=10, converter=1)
        finally:
            SR = sr0
        lo, hi = min(g.values()), max(g.values())
        ok = lo >= dmin - 0.05 and hi <= dmax + 0.05
        rec("Frequency response", f"effect path 20 Hz-17 kHz at host {host / 1000:g} kHz (re 1 kHz)",
            f"min {lo:+.2f} / max {hi:+.2f} dB; " + ", ".join(f"{k:g}: {v:+.2f}" for k, v in g.items()),
            "+0.5 / -3 dB", "mask", "CONSISTENT" if ok else "INCONSISTENT", "SM p.1",
            "sine, one frequency at a time", "stepped sine, fundamental bin")
    # direct path: BALANCE 0, PRE off (the character stage is a modern approximation)
    flo, fhi, dmin, dmax = RM.response_mask("direct")
    g = stepped_sine_db([20, 50, 100, 1000 * 2, 10000, 15000, 20000], balance=0, pre_on=0)
    lo, hi = min(g.values()), max(g.values())
    rec("Frequency response", "direct path 20 Hz-20 kHz (PRE off)", f"min {lo:+.3f} / max {hi:+.3f} dB",
        "+-0.5 dB", "mask", "CONSISTENT" if lo >= dmin and hi <= dmax else "INCONSISTENT", "SM p.1",
        "sine, stepped", "fundamental bin")
    # cross-check with broadband methods: white noise (H1 + coherence) and a log sweep (Farina).
    xn = sig_noise(8.0, LIN)
    y = run(xn, time_ms=0, feedback=0, balance=10, converter=1)[0]
    f, H = h1_response(xn, y)
    _, coh = signal.coherence(xn, y, fs=SR, nperseg=16384)
    H = H / at(f, H, 1000)
    xs, L = sig_logsweep(10, 23000, 6.0, LIN)
    ys = run(np.concatenate([xs, np.zeros(SR)]), time_ms=0, feedback=0, balance=10, converter=1)[0]
    fs_, Hs = sweep_response(np.concatenate([xs, np.zeros(SR)]), ys, L, 10)
    Hs = Hs / at(fs_, Hs, 1000)
    g = stepped_sine_db([100, 5000, 10000, 15000, 17000], time_ms=0, feedback=0, balance=10, converter=1)
    rows = [f"{p:g} Hz: sine {g[p]:+.2f} / noise {db(at(f, H, p)):+.2f} / sweep {db(at(fs_, Hs, p)):+.2f} dB"
            for p in g]
    lowcoh = float(np.min(coh[(f > 12000) & (f < 17000)]))
    rec("Frequency response", "broadband cross-check (noise H1, log sweep) vs stepped sine",
        "; ".join(rows) + f"; min coherence 12-17 kHz {lowcoh:.3f}", "same response by all methods if LTI", "n/a",
        "REPORTED", "method check", "white noise, log sweep, sines", "Welch H1 + coherence; Farina deconvolution")


def m_aliasing():
    """Emulating the 64 kHz clock inside the host rate is not LTI: report the largest
    non-harmonic spur for single high tones (the hardware's analog output has no in-band folding)."""
    rows, worst = [], -999.0
    for host in (44100, 48000):
        global SR
        sr0, SR = SR, host
        try:
            for f0 in (1000, 5000, 10000, 12500, 15000, 17000, 20000):
                if f0 > host / 2 - 500:
                    continue
                x = sig_sine(f0, 0.8, LIN)       # 20 dB below nominal: no converter overload
                y = run(x, time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)[0][int(0.3 * SR):]
                w = signal.windows.blackmanharris(len(y))
                S = np.abs(np.fft.rfft(y * w))
                fr = np.fft.rfftfreq(len(y), 1 / SR)
                k0 = int(np.argmin(np.abs(fr - f0)))
                # linear operating point (CLEAN, PRE off, -20 dB): any component other than the tone
                # itself is an artefact of the clock-domain conversion
                mask = (np.abs(fr - f0) > 40) & (fr > 20)
                kmax = int(np.argmax(S * mask))
                spur = float(db(S[kmax] / S[k0]))
                worst = max(worst, spur)
                rows.append(f"{host / 1000:g} kHz host, {f0 / 1000:g} kHz tone: {spur:.1f} dB at {fr[kmax]:.0f} Hz")
        finally:
            SR = sr0
    rec("Distortion", "in-band alias spurs from the 64 kHz clock emulation (single tones)", "; ".join(rows),
        "hardware: none in-band (analog output after a 64 kHz reconstruction filter)", "n/a", "REPORTED",
        "SM p.3 (clocked converter); emulation artefact", "high sine tones", "largest non-harmonic bin")


def m_filters():
    for idx, fc in ((1, 8000.0), (2, 4000.0), (3, 2000.0)):
        pts = [fc / 4, fc / 2, fc, min(2 * fc, 16000)]
        a = stepped_sine_db(pts, absolute=True, time_ms=0, feedback=0, balance=10, converter=1, highcut=idx)
        b = stepped_sine_db(pts, absolute=True, time_ms=0, feedback=0, balance=10, converter=1)
        rel = {p: a[p] - b[p] for p in pts}
        dev = max(abs(rel[p] - float(RM.high_cut_db(p, fc))) for p in pts)
        rec("Feedback filters", f"HIGH {fc / 1000:g} kHz (re FLAT)",
            f"at fc {rel[fc]:+.2f} dB, at {pts[-1] / 1000:g} kHz {rel[pts[-1]]:+.2f} dB (model {float(RM.high_cut_db(pts[-1], fc)):+.2f}); max dev {dev:.2f} dB",
            "1st-order low-pass, -3 dB at fc, -6 dB/oct", "+-0.5 dB (fc/4..2fc)",
            "CONSISTENT" if dev <= 0.5 else "INCONSISTENT", "SM p.1 (-6 dB/OCT); corner definition assumed",
            "sine, stepped", "gain(setting) - gain(FLAT)")
    for idx, fc in ((1, 125.0), (2, 250.0), (3, 500.0)):
        pts = [fc / 8, fc / 4, fc]
        a = stepped_sine_db(pts, absolute=True, time_ms=0, feedback=0, balance=10, converter=1, lowcut=idx)
        b = stepped_sine_db(pts, absolute=True, time_ms=0, feedback=0, balance=10, converter=1)
        rel = {p: a[p] - b[p] for p in pts}
        slope = rel[fc / 4] - rel[fc / 8]
        atfc = rel[fc]
        lo_t, hi_t = RM.LOW_CUT_TURNOVER_DB
        rec("Feedback filters", f"LOW {fc:g} Hz slope (fc/8 -> fc/4), default 3 dB mode", f"{slope:.2f} dB/oct",
            "3 dB/oct", "+-0.5 dB/oct", "CONSISTENT" if abs(slope - 3.0) <= 0.5 else "INCONSISTENT",
            "SM p.1 (-3dB/OCT; possibly a misprint -- UNKNOWN)", "sine, stepped", "gain ratio")
        rec("Feedback filters", f"LOW {fc:g} Hz level at the turnover frequency", f"{atfc:+.2f} dB",
            "turnover definition not given", f"{lo_t}..{hi_t} dB accepted",
            "CONSISTENT" if lo_t <= atfc <= hi_t else "INCONSISTENT", "SM p.1; definition UNKNOWN", "sine, stepped", "gain ratio")
    # filters act once per repeat (SM block diagram): repeat k is attenuated k x single-pass
    T = 0.2
    x = np.concatenate([np.hanning(int(0.05 * SR)) * sig_sine(4000, 0.05, NOM), np.zeros(int(1.5 * SR))])
    yf = run(x, time_ms=200, feedback=7, balance=10, highcut=2, converter=1)[0]
    y0 = run(x, time_ms=200, feedback=7, balance=10, converter=1)[0]
    devs = []
    for k in range(1, 5):
        s = int((k * T) * SR)
        r = db(rms(yf[s:s + int(0.06 * SR)]) / rms(y0[s:s + int(0.06 * SR)]))
        devs.append((k, round(float(r), 2), round(RM.repeats_filtered_db(k, 4000, 4000), 2)))
    worst = max(abs(a - b) for _, a, b in devs)
    rec("Feedback filters", "HIGH 4 kHz acts once per repeat (4 kHz burst, FB 7)",
        f"repeat k filtered/flat: {[(k, a) for k, a, _ in devs]}", f"k x {RM.high_cut_db(4000, 4000):.2f} dB",
        "+-0.3 dB per repeat", "CONSISTENT" if worst <= 0.3 * 4 else "INCONSISTENT",
        "SM p.3 block diagram (filters inside regeneration path)", "sine burst", "per-repeat RMS ratio")


def m_feedback():
    rows, worst = [], 0.0
    for fb in (2.0, 3.5, 5.0, 6.5, 7.0):
        x = np.concatenate([sig_sine(1000, 0.05, NOM) * np.hanning(int(0.05 * SR)), np.zeros(int(1.4 * SR))])
        y = run(x, time_ms=200, feedback=fb, balance=10, converter=1)[0]
        lv = [rms(y[int(k * 0.2 * SR):int(k * 0.2 * SR) + int(0.06 * SR)]) for k in range(1, 6)]
        d = float(np.mean(np.diff(db(np.array(lv)))))
        ref = RM.feedback_db_per_repeat(fb)
        worst = max(worst, abs(d - ref))
        rows.append(f"FB {fb}: {d:+.2f} (ref {ref:+.2f})")
    rec("Feedback", "decay per repeat, 1 kHz, flat filters", "; ".join(rows), "20 log10(FB/7) dB",
        "+-0.25 dB", "CONSISTENT" if worst <= 0.25 else "INCONSISTENT",
        "OM 'above about 7 causes oscillation' -> FB/7 is an INFERENCE (Medium)", "sustained 1 kHz burst",
        "mean level step between repeats")
    # SM p.15 sec.7: FB 10 @ 50 ms, LOW 500 / HIGH 2k oscillates after a 100 ms pulse; LEVEL 0 -> none
    x = np.concatenate([sig_sine(1000, 0.1, NOM), np.zeros(int(5 * SR))])
    y = run(x, time_ms=50, feedback=10, balance=10, lowcut=3, highcut=3)[0]
    late = rms(y[-SR:])
    y0 = run(x, time_ms=50, feedback=10, balance=10, lowcut=3, highcut=3, in_level=0)[0]
    rec("Feedback", "SM check 7: FB 10, 50 ms, 500 Hz/2 kHz", f"sustains at {db(late):.1f} dBFS after 5 s; LEVEL 0 -> peak {db(np.abs(y0).max()):.0f} dBFS",
        "oscillation; none without input", "qualitative", "CONSISTENT" if late > 1e-3 and np.abs(y0).max() == 0 else "INCONSISTENT",
        "SM p.15 sec.7", "100 ms pulse (SM Fig.5)", "level after 5 s")


def inst_delay_track(T, intensity, freq, waveform, secs, win=0.08, hop=0.01):
    """Track the instantaneous delay with short-window cross-correlation of white noise."""
    x = sig_noise(secs, NOM)
    y = run(x, time_ms=T, feedback=0, balance=10, intensity=intensity, frequency=freq, waveform=waveform,
            converter=1)[0]
    w, h = int(win * SR), int(hop * SR)
    maxd = int((T / 1000 + 0.01) * SR)
    ds, ts = [], []
    for s in range(maxd + w, len(y) - w, h):
        seg = y[s:s + w]
        ref = x[s - maxd:s + w]
        c = signal.correlate(ref, seg, mode="valid", method="fft")
        k = parabolic_peak(c)
        ds.append((maxd - k) / SR * 1000)
        ts.append(s / SR)
    # a 9-point median removes isolated false correlation peaks (pitch-shifted windows)
    return np.array(ts), signal.medfilt(np.array(ds), 9)


def m_modulation():
    # depth at INTENSITY 10: delay ranges from T down to T/2. Measured with a click train (each
    # click's echo time = the delay at that moment); robust to the pitch shift of moving delays.
    per = 0.05
    n = int(24 * SR)
    x = np.zeros(n); idx_in = np.arange(int(0.1 * SR), n - int(0.5 * SR), int(per * SR)); x[idx_in] = 0.5
    y = run(x, time_ms=400, feedback=0, balance=10, intensity=10, frequency=0, waveform=0, converter=1)[0]
    pk, _ = signal.find_peaks(np.abs(y), height=0.2 * np.abs(y).max(), distance=int(0.02 * SR))
    m = min(len(pk), len(idx_in))
    ds = (pk[:m] - idx_in[:m]) / SR * 1000
    ds = ds[idx_in[:m] > 2 * SR]
    r = float(ds.min() / ds.max())
    rec("Modulation", "depth at INTENSITY 10 (TRI, 0.1 Hz)", f"delay {ds.min():.1f}..{ds.max():.1f} ms, ratio {r:.3f} ({m} clicks)",
        f"{RM.min_delay_ratio(10)} (2:1, delay only shortens)", "+-0.01", "CONSISTENT" if abs(r - 0.5) <= 0.01 and ds.max() <= 400.5 else "INCONSISTENT",
        "SM p.1 'Intensity (0 - 2:1)'; OM", "click train (20 Hz)", "echo time of each click")
    # square at INTENSITY 10: two states (SM p.15 sec.6 measures the clock in this mode)
    ts, ds = inst_delay_track(400, 10, 0, 1, 24.0)
    ds = ds[ts > 2.0]
    hi_, lo_ = np.percentile(ds, 95), np.percentile(ds, 5)
    ratio_sm, (rmin, rmax) = RM.sm_mod_clock_ratio()
    rq = float(hi_ / lo_)
    rec("Modulation", "SQUARE, INTENSITY 10: delay ratio of the two states", f"{hi_:.1f}/{lo_:.1f} ms = {rq:.3f}",
        f"clock 78/40 kHz = {ratio_sm:.2f} (SM); 2.00 (spec 2:1)", f"{rmin:.2f}..{rmax:.2f} (SM tolerances)",
        "CONSISTENT" if rmin <= rq <= rmax else "INCONSISTENT", "SM p.15 sec.6; SM p.1",
        "white noise", "delay tracking")
    # rate endpoints: pitch of a 1 kHz probe; modulation frequency = peak of the instantaneous-frequency spectrum
    for knob, ref in ((0, RM.vco_rate_endpoints()[0]), (10, RM.vco_rate_endpoints()[1])):
        secs = 42.0 if knob == 0 else 4.0
        x = sig_sine(1000, secs, NOM)
        y = run(x, time_ms=100, feedback=0, balance=10, intensity=2, frequency=knob, waveform=0)[0][SR:]
        ph = np.unwrap(np.angle(signal.hilbert(y)))
        fi = np.diff(ph) * SR / (2 * np.pi)
        fi = signal.decimate(signal.medfilt(fi, 31), 40)
        fsr = SR / 40
        F = np.abs(np.fft.rfft((fi - fi.mean()) * np.hanning(len(fi)), 1 << 22))
        fr = np.fft.rfftfreq(1 << 22, 1 / fsr)
        m = (fr > 0.03) & (fr < 40)
        est = float(fr[m][np.argmax(F[m])])
        rec("Modulation", f"rate at FREQUENCY {knob}", f"{est:.3f} Hz", f"{ref} Hz", "+-2 %",
            "CONSISTENT" if abs(est / ref - 1) <= 0.02 else "INCONSISTENT", "SM p.1 'VCO 0.1Hz ~ 15Hz'",
            "1 kHz sine", "instantaneous frequency spectrum")
    rec("Modulation", "FREQUENCY knob law between 0.1 and 15 Hz", "exponential (implementation-defined)",
        "not documented", "n/a", "REPORTED", "UNKNOWN", "-", "-")
    rec("Modulation", "waveform shapes (TRI sharp peak / rounded trough; RND smoothing)",
        "see engine test 'modulation waveforms'", "SM Fig.3 sketch; SM sec.3 'integrated'", "n/a", "REPORTED",
        "SM p.14 (drawings, not quantitative)", "-", "-")


def m_levels_and_clipping():
    # input clip points: 1 dB compression on the direct path (BALANCE 0), PRE on
    rows, ok = [], True
    for idx, name in ((0, "-30"), (1, "-10"), (2, "+4")):
        spec = RM.SPEC["input_clip_dbm"][name]
        found = None
        for dbm in np.arange(spec - 12, spec + 6, 0.25):
            a = dbm_amp(dbm)
            y = run(sig_sine(1000, 0.2, a), balance=0, in_range=idx)[0][int(0.1 * SR):]
            y_lin = run(sig_sine(1000, 0.2, dbm_amp(spec - 20)), balance=0, in_range=idx)[0][int(0.1 * SR):]
            g = db(rms(y) / a) - db(rms(y_lin) / dbm_amp(spec - 20))
            if g <= -1.0:
                found = dbm
                break
        rows.append(f"ATT {name}: 1 dB compression at {found:+.2f} dBm (spec clip {spec:+.0f})")
        ok &= found is not None and abs(found - spec) <= 1.0
    rec("Levels", "input clip points (1 dB compression, LEVEL 5)", "; ".join(rows), "-13 / +7 / +21 dBm",
        "+-1 dB ('clip' definition not given)", "CONSISTENT" if ok else "INCONSISTENT", "SM p.1",
        "high-level 1 kHz sine, stepped", "gain drop vs low level")
    # output attenuator ranges are pads of -24 / -14 dB (from the SM clip levels)
    ref = RM.output_range_offsets_db()
    x = sig_sine(1000, 0.3, NOM)
    l4 = rms(run(x, balance=0, out_range=2)[0][SR // 10:])
    got = {}
    for idx, name in ((0, "-20"), (1, "-10")):
        got[name] = round(float(db(rms(run(x, balance=0, out_range=idx)[0][SR // 10:]) / l4)), 3)
    ok = all(abs(got[k] - ref[k]) <= 0.1 for k in got)
    rec("Levels", "output range offsets", f"{got}", f"{ {k: ref[k] for k in got} } dB", "+-0.1 dB",
        "CONSISTENT" if ok else "INCONSISTENT", "SM p.1 (derived from output clip levels)", "1 kHz sine", "level ratio")
    # input range offsets (-30/-10 are +34/+14 dB more sensitive)
    ref_i = RM.input_range_offsets_db()
    a = dbm_amp(-30)
    l4 = rms(run(sig_sine(1000, 0.3, a), balance=0, in_range=2, pre_on=0)[0][SR // 10:])
    got = {name: round(float(db(rms(run(sig_sine(1000, 0.3, a), balance=0, in_range=idx, pre_on=0)[0][SR // 10:]) / l4)), 2)
           for idx, name in ((0, "-30"), (1, "-10"))}
    ok = all(abs(got[k] + ref_i[k]) <= 0.5 for k in got)
    rec("Levels", "input range sensitivity", f"gain re +4: {got} dB", f"{ {k: -ref_i[k] for k in got} } dB (from clip levels)",
        "+-0.5 dB", "CONSISTENT" if ok else "INCONSISTENT", "SM p.1 (derived)", "low-level 1 kHz sine", "level ratio, PRE off")
    # converter overload point on the effect path (not specified; reported)
    found = None
    for dbm in np.arange(0, 22, 0.25):
        a = dbm_amp(dbm)
        y = run(sig_sine(1000, 0.25, a), time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)[0][SR // 10:]
        g = db(rms(y) / a) - db(rms(run(sig_sine(1000, 0.25, NOM), time_ms=0, feedback=0, balance=10, converter=1, pre_on=0)[0][SR // 10:]) / NOM)
        if g <= -1.0:
            found = dbm
            break
    rec("Levels", "effect-path converter overload (1 dB compression)", f"{found:+.2f} dBm (= nominal {found - 4:+.1f} dB)",
        "not specified (headroom meter red = +3 dB, OM)", "n/a", "REPORTED", "OM meter scale; SM silent",
        "high-level 1 kHz sine", "gain drop")
    return found


def m_distortion_noise(conv_clip_dbm):
    # THD at 1 kHz, nominal level (+4 dBm), effect and direct
    y = run(sig_sine(1000, 2.0, NOM), time_ms=0, feedback=0, balance=10)[0][SR // 2:SR // 2 + 65536]
    t_eff = thd(y, 1000)
    y = run(sig_sine(1000, 2.0, NOM), balance=0)[0][SR // 2:SR // 2 + 65536]
    t_dir = thd(y, 1000)
    rec("Distortion", "THD 1 kHz at +4 dBm, effect path (13-bit, PRE on)", f"{t_eff:.4f} %", "0.03 % typical", "<= 0.09 % (3x typical)",
        "CONSISTENT" if t_eff <= 0.09 else "INCONSISTENT", "SM p.1 ('typical'; measurement level not stated)",
        "sustained 1 kHz sine", "harmonics 2-10, Blackman-Harris FFT")
    # "TOTAL DISTORTION" (SM wording): everything except the fundamental, 20 Hz-20 kHz, unweighted
    y = run(sig_sine(1000, 3.0, NOM), time_ms=0, feedback=0, balance=10)[0][SR:SR + 131072]
    w = signal.windows.blackmanharris(len(y))
    S = np.abs(np.fft.rfft(y * w)) ** 2
    fr = np.fft.rfftfreq(len(y), 1 / SR)
    band = (fr >= 20) & (fr <= 20000)
    fund = np.abs(fr - 1000) < 30
    td = 100 * np.sqrt(S[band & ~fund].sum() / S[fund].sum())
    rec("Distortion", "total distortion + noise 1 kHz at +4 dBm, effect path (13-bit, PRE on)", f"{td:.4f} %",
        "0.03 % typical ('TOTAL DISTORTION')", "<= 0.09 % (3x typical)", "CONSISTENT" if td <= 0.09 else "INCONSISTENT",
        "SM p.1 (bandwidth/weighting not stated)", "sustained 1 kHz sine", "all non-fundamental power 20 Hz-20 kHz")
    rec("Distortion", "THD 1 kHz at +4 dBm, direct path (PRE on)", f"{t_dir:.4f} %", "0.005 % typical", "<= 0.015 % (3x typical)",
        "CONSISTENT" if t_dir <= 0.015 else "INCONSISTENT", "SM p.1", "sustained 1 kHz sine", "harmonics 2-10")
    # dynamic range, effect path: AES17-style, 1 kHz at -60 dB re the converter overload point, A-weighted
    ref_amp = dbm_amp(conv_clip_dbm)
    a = ref_amp * 10 ** (-60 / 20)
    y = run(sig_sine(1000, 3.0, a), time_ms=0, feedback=0, balance=10, pre_on=0)[0][SR:SR + 131072]
    pn, p1 = thdn_aw(y, 1000)
    # level of the -60 dB tone corresponds to (ref - 60 dB): DR = 60 + 10log10(p1/pn)
    dr = 60 + 10 * np.log10(p1 / pn)
    rec("Noise", "dynamic range, effect path (A-wtd, -60 dB tone re converter overload)", f"{dr:.1f} dB",
        "94 dB", "+-4 dB (reference level and bandwidth of the SM figure not stated)",
        "CONSISTENT" if abs(dr - 94) <= 4 else "INCONSISTENT", "SM p.1 'DYNAMIC RANGE 94dB (Effect) A-Weighted'",
        "low-level 1 kHz sine", "AES17-style THD+N, A-weighted 20 Hz-20 kHz")
    # quantisation: gain-ranging step of ~6 dB in the error level (13-bit minus CLEAN)
    lv, err = [], []
    for rel in (-2, -4, -8, -10, -14, -20):
        a = ref_amp * 10 ** (rel / 20)
        x = sig_sine(997, 1.5, a)
        y13 = run(x, time_ms=0, feedback=0, balance=10, pre_on=0)[0][SR // 2:]
        ycl = run(x, time_ms=0, feedback=0, balance=10, pre_on=0, converter=1)[0][SR // 2:]
        lv.append(rel); err.append(float(db(rms(y13 - ycl) / rms(ycl))))
    absn = [e + l for e, l in zip(err, lv)]     # error level relative to the overload point
    step = max(absn) - min(absn)
    model = RM.quantiser_12p1
    m_hi = db(rms(model(sig_sine(997, 0.5, 0.7)) - sig_sine(997, 0.5, 0.7)))
    m_lo = db(rms(model(sig_sine(997, 0.5, 0.2)) - sig_sine(997, 0.5, 0.2)))
    rec("Quantisation", "gain-ranging: converter error level, large vs small signals",
        f"error re overload point at {lv} dB: {[round(v, 1) for v in absn]} dB -> spread {step:.1f} dB",
        f"one range bit: {m_hi - m_lo:.1f} dB step (12+1-bit model)", "5..7.5 dB", "CONSISTENT" if 5.0 <= step <= 7.5 else "INCONSISTENT",
        "PARTS (12-bit DAC) + EMM/UAD (gain ranging); threshold UNKNOWN", "1 kHz sines, 6 levels",
        "13-bit minus CLEAN residual")
    rec("Noise", "S/N ratio (idle noise)", "digital silence (no analog noise modelled)", "88 dB (Effect), 95 dB (Direct)",
        "n/a", "NOT COMPARABLE", "SM p.1; RESEARCH_NOTES D (not modelled)", "silence", "-")


def m_stereo():
    x = sig_noise(2.0, NOM)
    o = run(x, time_ms=50, feedback=3, balance=5, out_mode=2)
    d = run(x, time_ms=50, feedback=3, balance=5, out_mode=1)[0]   # STEREO A left = DIRECT
    resid = db(rms(o[0] + o[1] - 2 * d) / rms(d))
    rec("Stereo / outputs", "STEREO B: (+MIX) + (-MIX) = 2 x DIRECT", f"residual {resid:.0f} dB", "exact identity",
        "< -80 dB", "CONSISTENT" if resid < -80 else "INCONSISTENT", "OM (output definitions)", "white noise", "algebraic residual")
    xr = sig_noise(2.0, NOM)
    o = run(x, np.zeros_like(x), time_ms=50, feedback=5, balance=6, out_mode=3)
    sep = db(rms(o[1]) / rms(o[0]))
    rec("Stereo / outputs", "TRUE ST channel separation (L in, R silent)", f"{sep:.0f} dB", "no hardware reference (modern mode)",
        "n/a", "REPORTED", "modern feature", "white noise", "R/L level")


def m_clicks_and_ceiling():
    rec("Transitions", "parameter-transition clicks", "see engine tests 'parameter changes are click-free', HOLD tests",
        "hardware jumped addresses (likely audible); click-free is a project requirement", "n/a", "REPORTED",
        "RESEARCH_NOTES B (engineering choice, not hardware)", "-", "-")
    x = sig_sine(1000, 0.5, 4.0)
    y = run(x, balance=0, out_gain=12)[0]
    rec("Levels", "output safety ceiling with extreme input (+24 dBFS sine, +12 dB gain)", f"peak {db(np.abs(y).max()):+.2f} dBFS",
        "no hardware reference (software safeguard)", "never above +12.04 dBFS", "REPORTED" if np.abs(y).max() <= 4.0 else "INCONSISTENT",
        "docs/OUTPUT_PROTECTION.md", "high-level sine", "peak")


def m_loopback_selftest():
    """Validate tools/loopback_measure.py on a simulated interface (latency, band-limiting, gain,
    noise) with the C engine as the device: the analysis must recover the device's own response."""
    import importlib.util, tempfile
    from scipy.io import wavfile
    spec = importlib.util.spec_from_file_location("lbm", os.path.join(ROOT, "tools", "loopback_measure.py"))
    lbm = importlib.util.module_from_spec(spec); spec.loader.exec_module(lbm)
    stim, marks = lbm.build_stimulus(SR)
    b, a = signal.butter(2, [5 / (SR / 2), 21000 / (SR / 2)], btype="band")
    def iface(x, lat=293):
        y = signal.lfilter(b, a, x) * 10 ** (-1 / 20)
        y = np.concatenate([np.zeros(lat), y]) + RNG.standard_normal(len(x) + lat) * 1e-5
        return y
    dev = run(stim, time_ms=0, feedback=0, balance=10, converter=1)[0]
    d = tempfile.mkdtemp()
    for name, sig in (("stim", stim), ("loop", iface(stim)), ("dev", iface(dev))):
        wavfile.write(os.path.join(d, name + ".wav"), SR, sig.astype(np.float32))
    ns = type("A", (), dict(stimulus=os.path.join(d, "stim.wav"), loopback=os.path.join(d, "loop.wav"),
                            device=os.path.join(d, "dev.wav"), out=os.path.join(d, "rep"),
                            conditions="simulated interface (self-test)"))
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        rep = lbm.analyze(ns)
    pts = [100, 1000, 5000, 10000]
    g = stepped_sine_db(pts, time_ms=0, feedback=0, balance=10, converter=1)
    dev_ = max(abs(rep["response_re_loopback_db"][str(p)] - g[p]) for p in pts)
    lat_ok = rep["loopback_latency_samples"] == 293
    rec("Method", "loopback analysis self-test (simulated interface)",
        f"latency found {rep['loopback_latency_samples']} (true 293); device-vs-loopback response within {dev_:.2f} dB of stepped sine (100 Hz-10 kHz)",
        "recover the device response", "+-0.3 dB, exact latency", "CONSISTENT" if dev_ <= 0.3 and lat_ok else "INCONSISTENT",
        "tools/loopback_measure.py", "measurement stimulus", "simulated capture, analyze()")


def write_reports(t0):
    meta = dict(generated_by="tests/hwref/hw_validation.py", host_rate=SR, device_under_test="C build of src/gen/echolivity_core.genexpr (tests/engine.py); not Ableton Live",
                calibration="+4 dBm nominal = -17 dBFS peak (project calibration)")
    json.dump(dict(meta=meta, results=RES), open(OUT_JSON, "w"), indent=1)
    cnt = {v: sum(r["verdict"] == v for r in RES) for v in ("CONSISTENT", "INCONSISTENT", "REPORTED", "NOT COMPARABLE")}
    L = ["# Hardware-reference validation results", "",
         "*Generated by `tests/hwref/hw_validation.py`. Do not edit by hand.*", "",
         "Device under test: the C build of the exact gen~ code at 48 kHz, **not Ableton Live and not original hardware**. "
         "References: `tests/hwref/reference_models.py`, derived from the Korg documentation only "
         "(sources and confidence: `HARDWARE_REFERENCE.md`).", "",
         f"**Summary:** {cnt['CONSISTENT']} consistent with the documentation, {cnt['INCONSISTENT']} inconsistent, "
         f"{cnt['REPORTED']} reported without a documented reference, {cnt['NOT COMPARABLE']} not comparable. "
         "\"Consistent\" means the software meets the documented figure within the stated tolerance; it does **not** mean the "
         "software is equivalent to an original unit.", "",
         "| Area | Measurement | Measured | Reference (source) | Tolerance | Verdict | Signal / method |", "|---|---|---|---|---|---|---|"]
    for r in RES:
        L.append(f"| {r['area']} | {r['name']} | {str(r['measured']).replace('|', '/')} | {r['reference']} ({r['source']}) | "
                 f"{r['tolerance']} | **{r['verdict']}** | {r['signal']}; {r['method']} |")
    open(OUT_MD, "w").write("\n".join(L) + "\n")
    print(cnt)
    return cnt


def main():
    build()
    t0 = time.time()
    m_delay_timing()
    m_frequency_response()
    m_aliasing()
    m_filters()
    m_feedback()
    m_modulation()
    clip = m_levels_and_clipping()
    m_distortion_noise(clip)
    m_stereo()
    m_clicks_and_ceiling()
    m_loopback_selftest()
    cnt = write_reports(t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
