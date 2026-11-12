"""
ECHOLIVITY SDD-3000 -- independent hardware reference models.

These functions encode what the *documentation* of the 1982 Korg SDD-3000 says, as plain
mathematics. They deliberately do NOT import or mirror the implementation under test
(tools/make_gen.py, src/gen/*.genexpr): no filter coefficients, curves or constants are
taken from it. Every model cites its source; where the documentation is silent the model
says so (UNKNOWN) and the test that uses it reports instead of judging.

Sources (see docs/validation/HARDWARE_REFERENCE.md for page references and confidence):
  SM  = Korg SDD-3000 Service Manual (1982), spec sheet (manual p.1 = PDF p.3),
        check & adjustment procedure (manual p.14-15 = PDF p.16-17)
  OM  = SDD-3000 Owner's Manual
  EMM = Electronics & Music Maker review, May 1983
"""
import numpy as np

# ------------------------------------------------------------------ SM spec sheet (PDF p.3)
SPEC = {
    "delay_ms": (0.0, 1023.0),          # "0 ~ 1023msec 1msec step (With full bandwidth)"
    "delay_step_ms": 1.0,
    "resp_effect_hz": (20.0, 17000.0),  # "20 ~ 17KHz +0.5dB -3dB (Effect)"
    "resp_effect_db": (-3.0, 0.5),
    "resp_direct_hz": (20.0, 20000.0),  # "20 ~ 20KHz +-0.5dB (Direct)"
    "resp_direct_db": (-0.5, 0.5),
    "dyn_range_db": {"direct": 110.0, "effect": 94.0},   # "A-Weighted"
    "sn_db": {"direct": 95.0, "effect": 88.0},           # "A-Weighted"
    "thd_pct_1k": {"direct": 0.005, "effect": 0.03},      # "Typical at 1KHz"
    "low_cut_hz": (125.0, 250.0, 500.0), "low_cut_db_oct": -3.0,
    "high_cut_hz": (8000.0, 4000.0, 2000.0), "high_cut_db_oct": -6.0,
    "vco_hz": (0.1, 15.0),              # "VCO frequency range 0.1Hz ~ 15Hz"
    "intensity_ratio": 2.0,             # "Intensity (0 - 2:1)"
    "input_clip_dbm": {"-30": -13.0, "-10": 7.0, "+4": 21.0},   # "Max (Clip) Level (VR at 5)"
    "output_clip_dbm": {"-20": -3.0, "-10": 7.0, "+4": 21.0},
    "clock_khz": 64.0, "clock_tol_khz": 2.0,               # SM p.15 sec.5
    "mod_clock_khz": (40.0, 78.0),                         # SM p.15 sec.6 (INT 10, FREQ 0, square)
}


# ------------------------------------------------------------------ delay timing
def hw_delay_ms(t_set_ms):
    """Hardware delay for a panel setting: integer milliseconds (SM: 1 ms step), realised on a
    64 kHz clock (SM p.15 sec.5) -> resolution 1/64 ms. Returns (expected_ms, tolerance_ms).
    Tolerance = one clock period: the hardware cannot be more precise than its clock."""
    t = float(np.clip(np.floor(t_set_ms + 0.5), *SPEC["delay_ms"]))
    return t, 1.0 / SPEC["clock_khz"]


# ------------------------------------------------------------------ frequency response masks
def response_mask(path):
    """Spec tolerance mask: (f_lo, f_hi, min_db, max_db) relative to 1 kHz."""
    if path == "effect":
        return SPEC["resp_effect_hz"] + SPEC["resp_effect_db"]
    return SPEC["resp_direct_hz"] + SPEC["resp_direct_db"]


# ------------------------------------------------------------------ feedback filters
def high_cut_db(f, fc):
    """HIGH cut: SM states -6 dB/oct at 8k/4k/2k = a first-order low-pass. The SM gives the
    'turn over freq' without defining it; the conventional -3 dB corner is assumed (Medium)."""
    f = np.asarray(f, float)
    return -10 * np.log10(1 + (f / fc) ** 2)


def low_cut_slope_db_oct():
    """LOW cut: SM states -3 dB/oct (an unusual half-order slope; could also be a misprint for
    -6 dB/oct -- UNKNOWN). The model only fixes the asymptotic slope well below the corner."""
    return SPEC["low_cut_db_oct"]


LOW_CUT_TURNOVER_DB = (-3.5, -1.5)   # UNKNOWN definition of 'turn over': accept -1.5..-3.5 dB


# ------------------------------------------------------------------ feedback law
def feedback_db_per_repeat(fb):
    """OM application notes: feedback 'above about 7' oscillates -> loop gain = FB/7 is an
    INFERENCE (Medium): it assumes a linear pot and unity at 7. Returns dB per repeat for a
    1 kHz tone with flat filters (SM response at 1 kHz is the 0 dB reference)."""
    return 20 * np.log10(max(fb, 1e-9) / 7.0)


def repeats_filtered_db(k, f, fc_high=None):
    """k passes through the loop each apply the filter once (SM block diagram p.3: filters
    after the memory inside the regeneration path) -> attenuation is k x single-pass."""
    a = 0.0
    if fc_high:
        a += float(high_cut_db(f, fc_high))
    return k * a


# ------------------------------------------------------------------ modulation
def vco_rate_endpoints():
    """SM: 0.1-15 Hz. The knob law between the endpoints is UNKNOWN (not documented)."""
    return SPEC["vco_hz"]


def min_delay_ratio(intensity_knob):
    """SM 'Intensity (0 - 2:1)', OM: the delay only gets shorter. At full intensity the
    shortest delay is 1/2 of the set delay. The law at intermediate settings is UNKNOWN; only
    the endpoint (knob 10 -> 0.5) is modelled."""
    return 0.5 if intensity_knob >= 10 else None


def sm_mod_clock_ratio():
    """SM p.15 sec.6: square wave, INT 10, FREQ 0 -> clock 40 kHz (min) to 78 kHz (max):
    ratio 1.95 (tolerances +-1/+-2 kHz -> 1.85..2.05). Consistent with 'up to 2:1'."""
    lo, hi = SPEC["mod_clock_khz"]
    return hi / lo, ((hi - 2) / (lo + 1), (hi + 2) / (lo - 1))


# ------------------------------------------------------------------ converter
def quantiser_12p1(x, fs=1.0, threshold=0.5):
    """'12-bit plus one' gain-ranged converter (parts list: 12-bit DAC; EMM/UAD: gain ranging).
    Independent textbook model: 12-bit mid-tread quantiser over +-fs; samples below
    threshold*fs are quantised with a step half as large (one extra bit). The real threshold,
    switching dynamics and emphasis are UNKNOWN; only the 6 dB step is modelled."""
    x = np.asarray(x, float)
    q = 2 * fs / 2 ** 12
    big = np.abs(x) >= threshold * fs
    y = np.where(big, np.round(x / q) * q, np.round(x / (q / 2)) * (q / 2))
    return np.clip(y, -fs, fs - q)


def ideal_sine_snr_db(bits):
    return 6.02 * bits + 1.76


# ------------------------------------------------------------------ gain structure
def output_range_offsets_db():
    """SM output clip levels -3 / +7 / +21 dBm for the -20 / -10 / +4 ranges -> the ranges are
    fixed pads of -24 dB and -14 dB relative to +4 (derived, High)."""
    c = SPEC["output_clip_dbm"]
    return {"-20": c["-20"] - c["+4"], "-10": c["-10"] - c["+4"], "+4": 0.0}


def input_range_offsets_db():
    c = SPEC["input_clip_dbm"]
    return {"-30": c["-30"] - c["+4"], "-10": c["-10"] - c["+4"], "+4": 0.0}


# ------------------------------------------------------------------ outputs (OM)
def stereo_relations():
    """OM: DIRECT, +MIX = direct + effect, -MIX = direct - effect; STEREO A = DIRECT/+MIX,
    STEREO B = +MIX/-MIX. Hence (+MIX) + (-MIX) = 2 x DIRECT exactly (High)."""
    return {"stereoB_sum_equals_2x_direct": True, "stereoA_left_is_direct": True}


# ------------------------------------------------------------------ weighting
def a_weighting_db(f):
    """IEC 61672 A-weighting (standard formula; used for the SM's A-weighted figures)."""
    f = np.asarray(f, float)
    f2 = f * f
    ra = (12194.0 ** 2 * f2 * f2) / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2))
                                    * (f2 + 12194.0 ** 2))
    return 20 * np.log10(np.maximum(ra, 1e-30)) + 2.0
