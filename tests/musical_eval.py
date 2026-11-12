#!/usr/bin/env python3
"""
ECHOLIVITY SDD-3000 -- musical evaluation round (v1.0.2-rc4).

Renders dub programme material through the C build of the exact gen~ code and measures
what a dub engineer hears: repeat degradation, filtering in the loop, transient softening,
saturation and self-oscillation, controllability when the feedback is ridden, modulation
movement, stereo image, desk-level driving and EXT-loop timing.

Measurements only; nothing here changes the device. Writes
docs/validation/MUSICAL_EVALUATION.json and audio_examples/musical_eval/*.flac (16-bit, 48 kHz, lossless;
every file normalised to the same peak so character, not level, is compared).
All source material is synthesised (seeded, deterministic): no third-party samples.
"""
import json, os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(__file__))
from engine import Engine, ROOT, build

SR = 48000
NOM = 10 ** (-17 / 20)          # +4 dBm nominal == -17 dBFS in the host
BPM = 75.0                      # one-drop tempo
BEAT = 60.0 / BPM
OUT_WAV = os.path.join(ROOT, "audio_examples", "musical_eval")
OUT_JSON = os.path.join(ROOT, "docs", "validation", "MUSICAL_EVALUATION.json")
R = {}


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2) + 1e-30))


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-t / d)


# ------------------------------------------------------------------ material
rng = np.random.default_rng(2026)


def bp(x, f, q):
    b, a = signal.iirpeak(f / (SR / 2), q)
    return signal.lfilter(b, a, x)


def rimshot():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    click = rng.standard_normal(n) * env(n, 0.0002, 0.004)
    body = (np.sin(2 * np.pi * 1720 * t) * 0.6 + np.sin(2 * np.pi * 480 * t)) * env(n, 0.0003, 0.03)
    click = bp(click, 3200, 1.2) + 0.5 * bp(click, 6500, 1.0)
    y = 4.0 * click / np.abs(click).max() + body / np.abs(body).max()
    return 0.9 * y / np.abs(y).max()


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.03)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.22)
    return 0.9 * y


def snare():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    tone_ = np.sin(2 * np.pi * 190 * t) * env(n, 0.0005, 0.05)
    nz = bp(rng.standard_normal(n), 4500, 0.8) * env(n, 0.0005, 0.12)
    y = tone_ + 0.7 * nz / np.abs(nz).max()
    return 0.9 * y / np.abs(y).max()


def bass_note(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    e = np.minimum(t / 0.008, 1) * np.where(t > dur - 0.04, np.maximum((dur - t) / 0.04, 0), 1)
    return 0.8 * y * e * np.exp(-t / 3.0)


def organ_stab(freqs, dur=0.14):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f in freqs:
        for h, a in ((1, 1.0), (2, 0.5), (3, 0.35), (4, 0.2), (6, 0.12), (8, 0.08)):
            if f * h < 12000:
                y += a * np.sin(2 * np.pi * f * h * t)
    e = np.minimum(t / 0.003, 1) * np.where(t > dur - 0.02, np.maximum((dur - t) / 0.02, 0), 1)
    return 0.6 * y * e / np.abs(y).max()


def place(buf, x, t):
    s = int(t * SR)
    e = min(len(buf), s + len(x))
    if s < len(buf):
        buf[s:e] += x[:e - s]


def spring(x):
    """Crude spring-tank send: dispersive allpass chain + two recirculating combs (chirpy, boingy)."""
    y = x.copy()
    for _ in range(12):
        y = signal.lfilter([-0.62, 1.0], [1.0, -0.62], y)
    out = np.zeros(len(y) + int(2.5 * SR))
    out[:len(y)] = y
    for dl, g in ((int(0.0371 * SR), 0.78), (int(0.0533 * SR), 0.74)):
        b = np.zeros(dl + 1); b[0] = 1
        a = np.zeros(dl + 1); a[0] = 1; a[-1] = -g
        out = out + 0.5 * signal.lfilter(b, a, out)
    out = bp(out, 2200, 0.7) + 0.3 * out
    return 0.7 * out / np.abs(out).max()


def plate(x):
    out = np.zeros(len(x) + int(3.0 * SR))
    out[:len(x)] = x
    d = rng.standard_normal(int(2.8 * SR)) * np.exp(-np.arange(int(2.8 * SR)) / (0.7 * SR))
    d = signal.lfilter(*signal.butter(2, 7000 / (SR / 2)), d)
    w = signal.fftconvolve(out, d)[:len(out)]
    return 0.7 * w / np.abs(w).max()


def bars(n):
    return np.zeros(int(n * 4 * BEAT * SR + 0.5 * SR))


def m_rimshot():
    x = bars(2)
    place(x, rimshot(), 2 * BEAT)          # beat 3 (one drop), bar 1 only: isolated hit
    return x


def m_kick_snare():
    x = bars(2)
    for b in range(2):
        place(x, kick(), (b * 4 + 2) * BEAT)
        place(x, snare(), (b * 4 + 2) * BEAT)
    return x


def m_bass():
    x = bars(2)
    line = [(0.0, 55.0, 1.4), (1.5, 65.4, 0.45), (2.0, 73.4, 1.4), (3.5, 61.7, 0.45),
            (4.0, 55.0, 1.4), (5.5, 82.4, 0.45), (6.0, 73.4, 1.9)]
    for t, f, d in line:
        place(x, bass_note(f, d * BEAT), t * BEAT)
    return x


def m_organ():
    x = bars(2)
    am, dm = (220.0, 261.6, 329.6), (293.7, 349.2, 440.0)
    for b in range(8):
        place(x, organ_stab(am if (b // 4) % 2 == 0 else dm), (b + 0.5) * BEAT)
    return x


def m_spring_send():
    x = bars(2)
    place(x, snare(), 2 * BEAT)
    return spring(x)[:len(x)]


def m_plate_send():
    x = bars(2)
    place(x, rimshot(), 2 * BEAT)
    return plate(x)[:len(x)]


def m_dense():
    x = bars(2)
    for b in range(2):
        place(x, kick(), (b * 4 + 2) * BEAT)
        place(x, snare(), (b * 4 + 2) * BEAT)
        for k in range(8):
            hh = bp(rng.standard_normal(int(0.04 * SR)), 9000, 1.0) * env(int(0.04 * SR), 0.0005, 0.01)
            place(x, 0.25 * hh / np.abs(hh).max(), (b * 4 + k * 0.5) * BEAT)
    x += 0.8 * m_bass()[:len(x)] + 0.5 * m_organ()[:len(x)]
    return 0.9 * x / np.abs(x).max()


MATERIAL = {"1_rimshot": m_rimshot, "2_kick_snare": m_kick_snare, "3_dub_bass": m_bass,
            "4_organ_skank": m_organ, "5a_spring_send": m_spring_send, "5b_plate_send": m_plate_send,
            "6_dense_mix": m_dense}

# ---------------------------------------------------------------- settings
T38 = round(0.75 * BEAT * 1000)           # dotted 1/8 at 75 BPM = 600 ms
SET = {
    "conservative": dict(time_ms=T38, feedback=3, balance=4),
    "dub_throw": dict(time_ms=T38, feedback=6, balance=6, lowcut=2, highcut=2),
    "dark_long": dict(time_ms=T38, feedback=6.8, balance=6, lowcut=1, highcut=3),
    "extreme_soft": dict(time_ms=T38, feedback=9, balance=6, lowcut=2, highcut=2, loop_sat=1),
}


def run(x, level_db=-17.0, xr=None, auto=None, tail=6.0, **p):
    g = 10 ** (level_db / 20) / max(np.abs(x).max(), 1e-9)
    xx = np.concatenate([x * g, np.zeros(int(tail * SR))])
    xr_ = None if xr is None else np.concatenate([xr * g, np.zeros(int(tail * SR))])
    e = Engine(SR, **p)
    e.silence(0.1)
    o = e.run(xx, xr_, automation=auto)
    return xx, o


def save(name, y, norm=True):
    os.makedirs(OUT_WAV, exist_ok=True)
    y = np.atleast_2d(y)
    if norm:
        y = y / max(np.abs(y).max(), 1e-9) * 0.7      # same peak for every file: compare character, not level
    wav = os.path.join(OUT_WAV, name + ".wav")
    wavfile.write(wav, SR, (np.clip(y.T, -1, 1) * 32767).astype(np.int16))
    # lossless FLAC keeps the package small; WAV is kept only if ffmpeg is unavailable
    import shutil, subprocess
    if shutil.which("ffmpeg"):
        subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "flac",
                               "-compression_level", "8", "-fflags", "+bitexact", "-flags:a", "+bitexact",
                               os.path.join(OUT_WAV, name + ".flac")])
        os.unlink(wav)


# ------------------------------------------------------------- measurements
def repeat_stats(y, t0, T, k_max, win=0.08):
    rows = []
    for k in range(1, k_max + 1):
        s = int((t0 + k * T) * SR)
        seg = y[s - int(0.005 * SR): s + int(win * SR)]
        if len(seg) < 64:
            break
        f, P = signal.periodogram(seg * np.hanning(len(seg)), SR)
        cen = float((f * P).sum() / max(P.sum(), 1e-30))
        hf = float(P[f > 4000].sum() / max(P.sum(), 1e-30))
        pk, r = np.abs(seg).max(), rms(seg)
        a = np.abs(signal.hilbert(seg))
        a = np.convolve(a, np.ones(48) / 48, "same")
        i90 = int(np.argmax(a >= 0.9 * a.max()))
        i10 = int(np.argmax(a >= 0.1 * a.max()))
        rows.append(dict(k=k, level_db=float(db(r)), centroid_hz=cen, hf_share_pct=100 * hf,
                         crest_db=float(db(pk / r)), attack_ms=1000 * (i90 - i10) / SR))
    return rows


def eval_repeat_degradation():
    """Single rimshot, wet only, FEEDBACK 5: what each repeat loses."""
    out = {}
    x = m_rimshot()
    t0 = 2 * BEAT
    for name, p in (("FLAT/FLAT", {}), ("LOW 250 / HIGH 4k", dict(lowcut=2, highcut=2)),
                    ("LOW 125 / HIGH 2k", dict(lowcut=1, highcut=3)),
                    ("FLAT, CLEAN converter", dict(converter=1))):
        xx, o = run(x, time_ms=400, feedback=5, balance=10, tail=4.0, **p)
        out[name] = repeat_stats(o[0], t0, 0.4, 7)
    src = repeat_stats(np.concatenate([np.zeros(int(0.4 * SR)), xx]), t0, 0.4, 1)[0]
    out["source"] = src
    R["repeat_degradation"] = out


def eval_noise_floor():
    """Converter 'grain': 13-bit minus CLEAN (same path otherwise) = the converter's own error,
    measured per repeat against the repeat's level, for a sustained bass line at two input levels."""
    x = m_bass()
    rows = {}
    for lvl in (-17, -35):
        o = {}
        for conv in (0, 1):
            xx, oo = run(x, level_db=lvl, time_ms=T38, feedback=6, balance=10, converter=conv, tail=8.0)
            o[conv] = oo[0]
        err = o[0] - o[1]
        per = []
        for t in range(1, 13):
            a, b = int(t * SR), int((t + 1) * SR)
            per.append(dict(second=t, signal_dbfs=float(db(rms(o[1][a:b]))),
                            converter_error_db_re_signal=float(db(rms(err[a:b]) / rms(o[1][a:b])))))
        rows[f"input {lvl} dBFS"] = per
    xx, oo = run(np.zeros(SR), level_db=-200, time_ms=400, feedback=6, balance=10, tail=2.0)
    rows["idle_output_dbfs"] = float(db(rms(oo[0][-SR:])))
    R["noise_floor"] = rows


def osc_metrics(y, t_on):
    s = int(t_on * SR)
    seg = y[s:]
    f, P = signal.periodogram(seg[-int(1.0 * SR):] * np.hanning(int(1.0 * SR)), SR)
    f0 = float(f[np.argmax(P)])
    harm = float(P[f > 2.5 * max(f0, 50)].sum() / max(P.sum(), 1e-30))
    return f0, harm


def eval_self_oscillation():
    """FEEDBACK ridden like a desk send: 4 -> 10 (hold 4 s) -> 5. Measures build-up, the
    oscillation's level and tone, and how quickly it can be pulled back."""
    x = m_kick_snare()
    rows = {}
    for name, p in (("HARD (authentic)", dict(loop_sat=0)), ("SOFT", dict(loop_sat=1)),
                    ("HARD, LOW 500 / HIGH 2k", dict(loop_sat=0, lowcut=3, highcut=3)),
                    ("SOFT, LOW 500 / HIGH 2k", dict(loop_sat=1, lowcut=3, highcut=3))):
        t_up, t_dn = 2.5, 6.5
        auto = [(int(t_up * SR), {"feedback": 10}), (int(t_dn * SR), {"feedback": 5})]
        xx, o = run(x, time_ms=T38, feedback=4, balance=6, auto=auto, tail=10.0, **p)
        y = o[0]
        seg = y[int((t_dn - 1.0) * SR):int(t_dn * SR)]
        f, P = signal.periodogram(seg * np.hanning(len(seg)), SR)
        f0 = float(f[np.argmax(P[f > 30]) + np.argmax(f > 30)])
        pk = float(db(np.abs(seg).max()))
        lv = float(db(rms(seg)))
        hfshare = float(100 * P[f > 3000].sum() / P.sum())
        # pull-back: level per delay period after FB 10 -> 5; time to fall 30 dB below the plateau
        P_ = T38 / 1000.0
        post = [rms(y[int((t_dn + k * P_) * SR):int((t_dn + (k + 1) * P_) * SR)]) for k in range(14)]
        drop = [db(v / max(post[0], 1e-12)) for v in post]
        rel = next((round((k + 1) * P_, 2) for k, d in enumerate(drop) if d <= -30), None)
        # build-up: time after FB -> 10 for the level to reach -1 dB of its plateau
        bu = y[int(t_up * SR):int(t_dn * SR)]
        b = np.convolve(np.abs(bu), np.ones(4800) / 4800, "same")
        tb = float(np.argmax(b >= b.max() * 10 ** (-1 / 20)) / SR)
        rows[name] = dict(plateau_rms_dbfs=lv, plateau_peak_dbfs=pk, dominant_hz=f0,
                          hf_above_3k_pct=hfshare, buildup_s=tb, pullback_30db_s=rel)
        save(f"7_ride_fb_4-10-5_{name.split()[0].strip(',').lower()}{'_filtered' if 'LOW' in name else ''}",
             o[:2])
    R["self_oscillation_ride"] = rows


def eval_long_evolving():
    """20 s: FEEDBACK 8 SOFT, RND modulation, HIGH swept 8k -> 2k -> FLAT, one spring-send hit."""
    x = np.concatenate([m_spring_send(), np.zeros(int(4 * SR))])
    auto = [(int(4 * SR), {"highcut": 1}), (int(8 * SR), {"highcut": 2}), (int(12 * SR), {"highcut": 3}),
            (int(16 * SR), {"highcut": 0, "feedback": 5})]
    xx, o = run(x, time_ms=T38, feedback=8, balance=6, loop_sat=1, waveform=2, intensity=1.5,
                frequency=2, lowcut=1, auto=auto, tail=10.0)
    y = o[0]
    lv = [float(db(rms(y[int(t * SR):int((t + 1) * SR)]))) for t in range(0, int(len(y) / SR) - 1)]
    R["long_evolving"] = dict(level_per_second_dbfs=lv, peak_dbfs=float(db(np.abs(o[:2]).max())))
    save("8_long_evolving_fb8_soft_rnd_highsweep", o[:2])


def eval_modulation():
    """Pitch movement of the repeats (1 kHz tone, wet only, FB 0) per INTENSITY and FREQUENCY."""
    rows = []
    x = np.sin(2 * np.pi * 1000 * np.arange(int(6 * SR)) / SR)
    for T in (380, 40):
        for fr in (2, 3):
            for it in (0.5, 1, 2, 5):
                xx, o = run(x, level_db=-17, time_ms=T, feedback=0, balance=10, intensity=it, frequency=fr,
                            waveform=0, tail=0.5)
                y = o[0][int(2 * SR):int(5.5 * SR)]
                ph = np.unwrap(np.angle(signal.hilbert(y)))
                fi = np.diff(ph) * SR / (2 * np.pi)
                fi = signal.medfilt(fi, 201)[2000:-2000]
                cents = 1200 * np.log2(np.maximum(fi, 1) / 1000)
                rows.append(dict(time_ms=T, frequency_knob=fr, rate_hz=round(0.1 * 150 ** (fr / 10), 3),
                                 intensity=it, pitch_dev_cents_peak=float(np.percentile(np.abs(cents), 99))))
    R["modulation"] = rows


def eval_transients_drive():
    """Desk driving: snare into the input at rising level (ATT +4, LEVEL 5); converter + preamp."""
    rows = []
    x = m_kick_snare()
    for lvl in (-17, -11, -5, -2, 0, 4):
        xx, o = run(x, level_db=lvl, time_ms=T38, feedback=0, balance=10, tail=1.0)
        s = int((2 * BEAT + T38 / 1000) * SR)
        seg = o[0][s - 240: s + int(0.12 * SR)]
        ref = xx[int(2 * BEAT * SR) - 240: int(2 * BEAT * SR) + int(0.12 * SR)]
        g = rms(seg) / rms(ref)
        rows.append(dict(input_peak_dbfs=lvl, echo_gain_db=float(db(g)),
                         crest_src_db=float(db(np.abs(ref).max() / rms(ref))),
                         crest_echo_db=float(db(np.abs(seg).max() / rms(seg)))))
        if lvl in (-17, 0, 4):
            save(f"9_desk_drive_snare_{'+' if lvl > 0 else ''}{lvl}dBFS", o[:2])
    R["desk_drive"] = rows


def eval_gain_staging():
    """Where the converter starts to overload, against the HEADROOM meter: CLEAN converter and PRE off
    (to isolate the converter clip), material scaled to each peak level and compared with a -40 dBFS
    linear reference."""
    rows = []
    for mname, fn in (("kick+snare", m_kick_snare), ("dub bass", m_bass), ("organ skank", m_organ)):
        x = fn()
        _, o = run(x, level_db=-40, time_ms=T38, feedback=0, balance=10, tail=1.0, converter=1, pre_on=0)
        ref = o[0] / 10 ** (-40 / 20)
        for lvl in (-20, -17, -14, -11, -8, -5, 0):
            _, o = run(x, level_db=lvl, time_ms=T38, feedback=0, balance=10, tail=1.0, converter=1, pre_on=0)
            e = o[0] / 10 ** (lvl / 20) - ref
            rows.append(dict(material=mname, input_peak_dbfs=lvl, meter_max_db=float(o[2].max()),
                             nonlinear_error_db=float(db(rms(e) / rms(ref)))))
    R["gain_staging"] = rows


def eval_stereo():
    rows = {}
    x = m_organ()
    for name, p in (("MONO", dict(out_mode=0)), ("STEREO A", dict(out_mode=1)), ("STEREO B", dict(out_mode=2)),
                    ("TRUE ST, mono source", dict(out_mode=3)), ("TRUE ST, WIDTH 200", dict(out_mode=3, width=2))):
        xx, o = run(x, time_ms=T38, feedback=4, balance=6, tail=3.0, **p)
        L, Rr = o[0], o[1]
        c = float(np.corrcoef(L, Rr)[0, 1])
        side = float(db(rms(L - Rr) / max(rms(L + Rr), 1e-12)))
        rows[name] = dict(lr_correlation=c, side_to_mid_db=side, mono_sum_change_db=float(
            db(rms(0.5 * (L + Rr)) / max(np.sqrt(0.5 * (rms(L) ** 2 + rms(Rr) ** 2)), 1e-12))))
    R["stereo"] = rows


def eval_ext_loop_timing():
    """EXT loop: extra delay per pass for typical buffer sizes; drift against a synced 3/8."""
    rows = []
    for buf in (64, 128, 256, 512):
        lat_ms = 1000 * buf / SR
        drift4 = 4 * lat_ms
        rows.append(dict(buffer=buf, extra_ms_per_pass=round(lat_ms, 2), drift_after_4_repeats_ms=round(drift4, 1),
                         drift_pct_of_16th_at_75bpm=round(100 * drift4 / (BEAT * 250), 1)))
    # simulated: EXT through a 'spring' track (one-pole darkening + 256-sample latency) vs INT
    x = m_rimshot()
    xx, o_int = run(x, time_ms=T38, feedback=5, balance=6, tail=4.0)
    e = Engine(SR, time_ms=T38, feedback=5, balance=6, fb_route=1, **{"return": 5})
    e.silence(0.1)
    g = 10 ** (-17 / 20) / np.abs(x).max()
    xx = np.concatenate([x * g, np.zeros(int(4 * SR))])
    o_ext = e.run(xx, loop_latency=256)
    save("10_ext_loop_rimshot_latency256", o_ext[:2])
    save("10_int_loop_rimshot_reference", o_int[:2])
    R["ext_loop_timing"] = rows


def render_material():
    for mname, fn in MATERIAL.items():
        x = fn()
        save(f"{mname}__dry", x / max(np.abs(x).max(), 1e-9))
        for sname in ("conservative", "dub_throw") + (("dark_long",) if mname in ("1_rimshot", "4_organ_skank", "5a_spring_send") else ()):
            xx, o = run(x, tail=5.0, **SET[sname])
            save(f"{mname}__{sname}", o[:2])
    # extreme soft on the dense mix only
    xx, o = run(m_dense(), tail=6.0, **SET["extreme_soft"])
    save("6_dense_mix__extreme_soft_fb9", o[:2])


def main():
    build()
    eval_repeat_degradation()
    eval_noise_floor()
    eval_self_oscillation()
    eval_long_evolving()
    eval_modulation()
    eval_transients_drive()
    eval_gain_staging()
    eval_stereo()
    eval_ext_loop_timing()
    if "--no-audio" not in sys.argv:
        render_material()
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(R, open(OUT_JSON, "w"), indent=1)
    print(json.dumps(R, indent=1)[:12000])


if __name__ == "__main__":
    main()
