"""
HW-1 investigation: isolated numpy model of the memory-clock conversion core.

Re-implements, independently of the gen~ code, the clock-domain conversion as the source
describes it (tools/make_gen.py, "MEMORY CLOCK EMULATION"), with every stage switchable so
each mechanism can be isolated. Host-rate filters (pre/de-emphasis, 2-pole AA and reconstruction
filters, droop EQ, LOW/HIGH) are linear and time-invariant at the host rate; they can't create
new frequencies, so they're left out here and only change levels.

Stages (production):
  1. host -> tick: the input is linearly interpolated between host samples at each tick time
  2. ticks at 64 kHz (fv), word written / read (TIME 0: the same word)
  3. tick -> host: zero-order hold of each word until the next tick, integrated (box-averaged)
     over each host sample period
Candidates replace stage 1 and/or 3.
"""
import numpy as np
from scipy import signal


def tick_times(n_host, fs, fv=64000.0, phase0=0.0):
    """Tick instants in host-sample units: t = (k + 1 - phase0) * fs / fv (matches ph/tt logic)."""
    T = n_host / fs
    k = np.arange(int(T * fv) + 2)
    return (k + (1 - phase0)) * fs / fv


def in_linear(x, t):
    """Production stage 1: linear interpolation of host samples at fractional host times t
    (sample n spans (n-1, n]; the value at integer n is x[n])."""
    n = np.arange(len(x))
    return np.interp(t, n, x)


def out_zoh_box(q, t, n_host):
    """Production stage 3: ZOH of q[k] from t[k] to t[k+1], integrated over (n-1, n]."""
    # cumulative integral of the ZOH at tick instants
    dt = np.diff(np.concatenate([t, [t[-1] + (t[1] - t[0])]]))
    I_t = np.concatenate([[0.0], np.cumsum(q * dt)])
    tk = np.concatenate([[t[0]], t + dt])
    # before the first tick the hold value is 0
    nb = np.arange(n_host + 1, dtype=float)
    I_n = np.interp(nb, tk, I_t, left=0.0)
    return np.diff(I_n)


# ---------------------------------------------------------------- band-limited candidates
def kaiser_sinc_table(taps, phases, cutoff, beta):
    """Windowed-sinc polyphase table: taps per phase, `phases` sub-sample positions.
    cutoff in cycles/sample of the *source* rate (0.5 = Nyquist)."""
    half = taps // 2
    pos = (np.arange(-half + 1, half + 1)[None, :] - np.arange(phases)[:, None] / phases)
    h = 2 * cutoff * np.sinc(2 * cutoff * pos) * np.kaiser(taps, beta)[None, :]
    h /= h.sum(axis=1, keepdims=True)              # unity DC gain for every phase
    return h, half


def interp_bandlimited(x, t, taps=16, phases=256, cutoff=0.45, beta=8.0):
    """Evaluate the band-limited reconstruction of x (host rate) at fractional times t, using a
    polyphase windowed-sinc table with linear interpolation between table phases."""
    h, half = kaiser_sinc_table(taps, phases + 1, cutoff, beta) if False else kaiser_sinc_table(taps, phases, cutoff, beta)
    h = np.vstack([h, np.roll(h[0:1], 1, axis=1)])   # phase == 1.0 equals phase 0 shifted by one tap
    n0 = np.floor(t).astype(int)
    fr = t - n0
    pf = fr * phases
    pi = np.floor(pf).astype(int)
    pa = pf - pi
    xp = np.concatenate([np.zeros(taps), x, np.zeros(taps)])
    out = np.zeros(len(t))
    for j in range(taps):
        idx = n0 - half + 1 + j + taps
        idx = np.clip(idx, 0, len(xp) - 1)
        c = h[pi, j] * (1 - pa) + h[pi + 1, j] * pa
        out += c * xp[idx]
    return out


def decimate_ticks_bandlimited(q, t, n_host, fs, fv, taps=16, phases=256, cutoff_hz=None, beta=8.0):
    """tick -> host by band-limited interpolation of the tick sequence at host instants, with
    the low-pass at min(fs, fv)/2 * 0.9 (removes the images above the host Nyquist before
    sampling). Equivalent to a polyphase resampler driven by the tick clock."""
    cutoff_hz = cutoff_hz or 0.45 * min(fs, fv)
    # host instant n (units of host samples) expressed in tick units
    tick0 = t[0]
    tick_period = (t[1] - t[0])
    pos = (np.arange(1, n_host + 1) - tick0) / tick_period      # fractional tick index
    c = cutoff_hz / fv
    return interp_bandlimited(q, pos, taps=taps, phases=phases, cutoff=c, beta=beta)


def chain(x, fs, fv=64000.0, stage_in="linear", stage_out="zoh_box", quant=None, taps=16):
    n = len(x)
    t = tick_times(n, fs, fv)
    t = t[t <= n - 1]
    if stage_in == "linear":
        q = in_linear(x, t)
    elif stage_in == "bandlimited":
        q = interp_bandlimited(x, t, taps=taps, cutoff=0.45 if fs < fv else 0.45 * fv / fs)
    else:
        raise ValueError(stage_in)
    if quant:
        q = quant(q)
    if stage_out == "zoh_box":
        return out_zoh_box(q, t, n)[:n]
    if stage_out == "bandlimited":
        return decimate_ticks_bandlimited(q, t, n, fs, fv, taps=taps)
    raise ValueError(stage_out)


# ================================================================ generalised core (v2)
# Tick instants for a (possibly modulated) clock, generated exactly like the gen~ code:
# per host sample n the tick phase advances by inc_n = fv_n / fs; ticks fall where it crosses
# an integer; t is in host-sample units on the interval (n-1, n].
def tick_times_mod(fv_per_host, fs, ph0=0.0):
    inc = np.asarray(fv_per_host, float) / fs
    phase_end = ph0 + np.cumsum(inc)                 # phase at the end of each host sample
    phase_start = phase_end - inc
    k_first = np.floor(phase_start) + 1
    k_last = np.floor(phase_end - 1e-12)
    counts = (k_last - k_first + 1).astype(int)
    counts = np.maximum(counts, 0)
    n_idx = np.repeat(np.arange(len(inc)), counts)
    ks = np.concatenate([np.arange(a, a + c) for a, c in zip(k_first.astype(np.int64), counts)]) if counts.sum() else np.zeros(0)
    t = n_idx + (ks - phase_start[n_idx]) / inc[n_idx] - 1.0 + 1.0   # sample n spans (n-1, n]
    # convert to the (n-1, n] convention: tick at fraction tau in host sample n is at n - 1 + tau
    tau = (ks - phase_start[n_idx]) / inc[n_idx]
    return n_idx - 1 + tau


def hold_durations(t):
    d = np.diff(t)
    return np.concatenate([d, [d[-1] if len(d) else 0.0]])


# ---- candidate A: cubic (Catmull-Rom) input interpolation + first-order-hold (linear) output,
#      integrated over the host period (FOH-box). Cheap polynomial upgrade of both stages.
def in_cubic(x, t):
    n0 = np.floor(t).astype(int)
    u = t - n0
    xp = np.concatenate([[0, 0], x, [0, 0, 0]])
    i = n0 + 2
    xm1, x0, x1, x2 = xp[i - 1], xp[i], xp[i + 1], xp[i + 2]
    return x0 + 0.5 * u * (x1 - xm1 + u * (2 * xm1 - 5 * x0 + 4 * x1 - x2 + u * (3 * (x0 - x1) + x2 - xm1)))


def out_foh_box(q, t, n_host, sub=8):
    """Linear interpolation between tick values (first-order hold), averaged over each host
    period with `sub` sub-samples (numerical integration)."""
    tt = (np.arange(n_host * sub) + 0.5) / sub - 0.5          # sub-sample instants in host units
    tt = tt - 0.5 + 0.5                                         # centre of (n-1, n] bins
    v = np.interp(tt + 0.0, t, q, left=0.0, right=0.0)
    return v.reshape(n_host, sub).mean(axis=1)


# ---- candidate B: band-limited kernels defined in continuous (host) time.
#      input : x_c(t) = sum_n x[n] h(t - n), evaluated at each tick  (lowpass fc_in)
#      output: y[n]   = sum_k q_k * d_k * h(n - D - t_k)              (lowpass fc_out)
#      Works unchanged with a modulated clock because the kernels live in host time.
def bl_kernel(taps, fc_norm, window="blackmanharris"):
    """Continuous kernel h(u), |u| < taps/2 (host samples), cutoff fc_norm (cycles/host sample)."""
    half = taps / 2
    def h(u):
        u = np.asarray(u, float)
        w = np.zeros_like(u)
        m = np.abs(u) < half
        z = (u[m] + half) / taps                      # 0..1 across the support
        if window == "blackmanharris":
            ww = 0.35875 - 0.48829 * np.cos(2 * np.pi * z) + 0.14128 * np.cos(4 * np.pi * z) - 0.01168 * np.cos(6 * np.pi * z)
        else:
            ww = 0.5 - 0.5 * np.cos(2 * np.pi * z)
        w[m] = 2 * fc_norm * np.sinc(2 * fc_norm * u[m]) * ww
        return w
    return h


def in_bandlimited(x, t, taps=32, fc_hz=20000.0, fs=48000.0):
    h = bl_kernel(taps, fc_hz / fs)
    D = taps // 2                                   # look-ahead -> constant latency of D host samples
    ts = t - D                                      # evaluate the input D samples in the past
    n0 = np.floor(ts).astype(int)
    xp = np.concatenate([np.zeros(taps + 2), x, np.zeros(taps + 2)])
    out = np.zeros(len(t))
    norm = np.zeros(len(t))
    for j in range(-D + 1, D + 1):
        idx = n0 + j
        c = h(ts - idx)
        out += c * xp[np.clip(idx + taps + 2, 0, len(xp) - 1)]
        norm += c
    return out / np.maximum(norm, 1e-12) * 1.0, D   # unity-gain normalisation per phase


def out_bandlimited(q, t, n_host, taps=32, fc_hz=20000.0, fs=48000.0):
    h = bl_kernel(taps, fc_hz / fs)
    D = taps // 2
    d = hold_durations(t)                          # each tick weighted by its hold time
    y = np.zeros(n_host + taps + 2)
    # scatter each tick into the host samples within the kernel support
    base = np.floor(t).astype(int)
    for j in range(-D, D + 2):
        n = base + j
        c = h(n - t - D * 0) * d
        np.add.at(y, np.clip(n + D, 0, len(y) - 1), c * q)
    return y[:n_host], D


# ---- candidate C: x4 oversampling around the production conversion core
def os4_chain(x, fs, fv_per_host, quant=None):
    up = signal.resample_poly(x, 4, 1, window=("kaiser", 10.0))           # linear-phase polyphase
    fv_os = np.repeat(np.asarray(fv_per_host, float), 4)
    t = tick_times_mod(fv_os, fs * 4)
    t = t[(t > 0) & (t < len(up) - 1)]
    q = in_linear(up, t)
    if quant:
        q = quant(q)
    y_os = out_zoh_box(q, t, len(up))
    return signal.resample_poly(y_os, 1, 4, window=("kaiser", 10.0))[:len(x)]


def run_candidate(name, x, fs, fv=64000.0, mod=None, quant=None, taps=32, fc_hz=None):
    """Return host-rate output of the conversion core for a candidate. mod: array of fv per host sample."""
    n = len(x)
    fv_arr = np.full(n, fv) if mod is None else mod
    if fc_hz is None:
        fc_hz = 19000.0 if fs < 46000 else 20000.0
    if name == "C_os4":
        return os4_chain(x, fs, fv_arr, quant)
    t = tick_times_mod(fv_arr, fs)
    t = t[(t > 0) & (t < n - 1)]
    if name == "production":
        q = in_linear(x, t)
        q = quant(q) if quant else q
        return out_zoh_box(q, t, n)
    if name == "A_cubic_foh":
        q = in_cubic(x, t)
        q = quant(q) if quant else q
        return out_foh_box(q, t, n)
    if name.startswith("B_bandlimited"):
        q, D1 = in_bandlimited(x, t, taps=taps, fc_hz=fc_hz, fs=fs)
        q = quant(q) if quant else q
        y, D2 = out_bandlimited(q, t, n, taps=taps, fc_hz=fc_hz, fs=fs)
        return y
    raise ValueError(name)
