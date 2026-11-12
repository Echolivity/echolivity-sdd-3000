#!/usr/bin/env python3
"""Write docs/TEST_REPORT.md from docs/TEST_RESULTS.json, docs/STATIC_CHECKS.json and
docs/REPRODUCIBILITY.json. Status vocabulary: PASS, FAIL, NOT VERIFIED."""
import json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D = os.path.join(ROOT, "docs")
E = json.load(open(os.path.join(D, "TEST_RESULTS.json")))
S = json.load(open(os.path.join(D, "STATIC_CHECKS.json")))
P = json.load(open(os.path.join(D, "REPRODUCIBILITY.json"))) if os.path.exists(os.path.join(D, "REPRODUCIBILITY.json")) else []
WAVS = sorted(f for f in os.listdir(os.path.join(ROOT, "audio_examples")) if f.endswith(".wav"))
REG = sorted(f for f in os.listdir(os.path.join(ROOT, "audio_examples", "regression")) if f.endswith(".wav"))


def cell(t):
    return str(t).replace("|", "/").replace("\n", " ")


ep = sum(r["pass"] for r in E)
ek = sum(1 for r in E if not r["pass"] and r.get("known_limitation"))
eu = len(E) - ep - ek

RUNTIME = [
    ("L-1 Device loading and gen~ compilation", "container/JSON checked; GenExpr subset rules; code identical to tested source"),
    ("L-2 Audio input/output and stereo routing", "plugin~/gen~/plugout~ routing checked; engine output modes tested"),
    ("L-3 Engine in Live matches the renders", "renders made by the tested engine"),
    ("L-4 Parameter automation", "158 definitions checked; engine automation and click tests PASS"),
    ("L-5 MIDI mapping", "all 38 panel parameters are live.* parameters (mappable by design)"),
    ("L-6 Tempo synchronisation and tempo automation", "live.observer chain checked; engine sync maths tested"),
    ("L-7 Preset saving and recall, .adv persistence, programs / WRITE", "120 stored-only slots + write/recall wiring checked"),
    ("L-8 Project save / reopen", "init sequence wiring checked; engine starts without ramps"),
    ("L-9 HOLD in Live", "engine HOLD tests PASS (engage, 108-case release matrix, re-engage)"),
    ("L-10 BYPASS in Live", "engine BYPASS tests PASS"),
    ("L-11 Sample-rate changes in Live", "engine rate-change test PASS (state kept)"),
    ("L-12 Invalid-input recovery in Live (gen~ fixnan)", "engine NaN/Inf tests PASS in the C model"),
    ("L-13 CPU in Live at 44.1-192 kHz", "C-build benchmark only (section 4)"),
    ("L-14 Latency reported to Live / PDC", "patcher latency 0; engine direct path 0 samples"),
    ("L-15 Interface appearance", "preview rendered from the same geometry, not by Max"),
]

L = ["# ECHOLIVITY SDD-3000 v1.0.2-rc5 — Test and validation report", "",
     "Status vocabulary: **PASS** = verified by an automated test or check. **FAIL** = the check fails "
     "(all current FAILs are known limitations of the unchanged v1.0 DSP, documented below). **NOT VERIFIED** = "
     "needs Max/Ableton Live, which was not available in the build environment. Static inspection is reported as "
     "*PASS (static)* and is never presented as runtime validation. Release-candidate status: the DSP acceptance "
     "criteria are met; Ableton Live validation is OUTSTANDING (`docs/LIVE_VALIDATION_CHECKLIST.md`).", "",
     "## Summary", "",
     "| Area | Result |", "|---|---|",
     f"| Engine tests (C build of the exact gen~ code) | {ep} PASS, {ek} FAIL (known limitation), {eu} unexpected FAIL — {len(E)} total |",
     f"| Static device checks (`tools/inspect_amxd.py`) | {sum(r['pass'] for r in S)}/{len(S)} PASS (static) |",
     f"| Reproducibility (`tools/verify_release.py`) | {sum(r['pass'] for r in P)}/{len(P)} PASS |",
     f"| Runtime behaviour inside Ableton Live / Max | {len(RUNTIME)} items BLOCKED (no Live available) |",
     "| Release decision | CONDITIONAL PASS, not production-ready (`docs/validation/RELEASE_DECISION.md`) |", "",
     "## 1. Engine tests", "",
     "`tools/gen2c.py` compiles the GenExpr embedded in the device to C, after enforcing a conservative "
     "GenExpr subset (whitelisted operators, depth-0 locals, no History read-after-write, no History writes in loops, "
     "no ternaries or `%`). Parameters are applied at 64-sample vector boundaries, as in gen~. Tests 1–25 are the "
     "v1.0 suite (measurements unchanged); 26–37 were added in v1.0.1; 38–41 in v1.0.2 (HOLD release matrix, "
     "re-engage, A/B regression against the v1.0.1 DSP, latency, per-rate CPU). Tests 30, 36 and 37 were "
     "known-limitation FAILs in v1.0.1 and are acceptance tests now; 42–44 were added in the final validation "
     "round (43 documents the pre-existing minor defect D-3). Source: `tests/run_tests.py`.", "",
     "| # | Test | Status | Measured | Reference |", "|---|---|---|---|---|"]
for i, r in enumerate(E, 1):
    st = "PASS" if r["pass"] else ("**FAIL** (known limitation)" if r.get("known_limitation") else "**FAIL**")
    L.append(f"| {i} | {cell(r['test'])} | {st} | {cell(r['detail'])} | {cell(r['spec'])} |")

L += ["", "## 2. Static device checks — PASS (static)", "",
      "Inspection of `dist/ECHOLIVITY SDD-3000.amxd`; nothing was executed in Max or Live.", "",
      "| Check | Status | Detail |", "|---|---|---|"]
for r in S:
    L.append(f"| {cell(r['check'])} | {'PASS (static)' if r['pass'] else '**FAIL**'} | {cell(r['detail'])} |")

L += ["", "## 3. Runtime integration in Ableton Live — BLOCKED (not executed)", "",
      "Step-by-step procedures and pass criteria: `docs/LIVE_VALIDATION_CHECKLIST.md`.", "",
      "No Max or Live installation was available, so none of the following has been observed running. "
      "The right-hand column shows only the static evidence that exists.", "",
      "| Item | Status | Static evidence only |", "|---|---|---|"]
for item, ev in RUNTIME:
    L.append(f"| {item} | BLOCKED | {ev} |")
L += ["", "Suggested manual check: drag `audio_examples/00_dry_source.wav` onto a track, insert the device, step "
      "through programs 1–9 comparing with the matching renders, automate Delay Time / Feedback / High Cut / Hold, "
      "save and reopen the Set, save and load an .adv preset, and watch Live's CPU meter with 8 instances.", "",
      "### Static-review risks (NOT VERIFIED, not changed)", "",
      "These follow from the patch logic and depend on Live/Max runtime behaviour I could not observe. No change was "
      "made without reproducible evidence.",
      "- **Re-selecting the active program** (including M) re-runs the recall. If `live.tab` re-outputs when the "
      "selected cell is clicked again, unsaved edits are discarded.",
      "- **Loading an .adv preset onto a running device:** the Program parameter's change triggers a recall. If Live "
      "restores the Program parameter before the stored program slots, the recall can use the previous slot contents. "
      "Loading a Set is not affected: program logic stays disabled until `live.thisdevice` reports the device ready.",
      "- **Automating Program** moves the stored controls. Any automation lanes on those controls will be "
      "overridden by Live, as with any device that sets its own parameters.", "",
      "## 4. Performance and latency", "",
      "### CPU (C build of the gen~ code — not inside Live)", ""] + open(os.path.join(D, "measurements", "cpu_c_build.md")).read().splitlines() + [
      "", "### Latency", "",
      "No look-ahead, no internal buffering; the patcher declares `latency: 0`. Measured (test 40): direct path "
      "0 samples; effect path at TIME 0 = 1 sample (44.1/48 kHz) to 3 samples (96 kHz) of filter group delay. "
      "In Live: NOT VERIFIED (L-14).", "",
      "### Standalone benchmark vs. Live", "",
      "The benchmark runs the C translation of the same GenExpr with gcc -O2. In Live, gen~ generates and compiles "
      "its own code; Max adds scheduling and Live adds device overhead. Expect different absolute numbers. "
      "The relative statement (v1.0.2 costs the same as v1.0.1) is the meaningful result here.", "",
      "## 5. Audio regression comparison (v1.0.1 vs v1.0.2-rc1, identical input and settings)", "",
      "Click excess = dB by which the >5 kHz content exceeds the 'HOLD kept' and 'never held' references in both "
      "absolute and level-relative terms (the same metric as test 38).", ""] + open(os.path.join(D, "measurements", "regression_audio.md")).read().splitlines() + [
      "", "All 19 v1.0.1 demo renders re-render **bit-identically** with v1.0.2-rc1. The engineering change report "
      "(`docs/ENGINEERING_CHANGES.md`) lists every intentional sonic difference.", "",
      "## 6. Outstanding issues", "", "See `docs/OUTSTANDING_ISSUES.md`.", "",
      "## 7. Reproducibility", "",
      "| Check | Status | Detail |", "|---|---|---|"]
for r in P:
    L.append(f"| {cell(r['check'])} | {'PASS' if r['pass'] else '**FAIL**'} | {cell(r['detail'])} |")
L += ["", "Checksums of every shipped file: `SHA256SUMS.txt`.", "",
      "## 8. Output protection", "",
      "Measured curves and the distinction from a 0 dBFS limiter: `docs/OUTPUT_PROTECTION.md`.", "",
      "## 9. Audio examples", "",
      f"`audio_examples/` contains {len(WAVS)} WAV files (48 kHz, 16-bit stereo): the dry source plus "
      f"{len(WAVS) - 1} renders made by the tested engine. They re-render bit-identically from the v1.0.1 source "
      "(section 5).", ""]
for w in WAVS:
    L.append(f"- `{w}`")
L += ["", f"`audio_examples/regression/` ({len(REG)} files, v1.0.1 vs v1.0.2-rc1, see section 5):", ""]
for w in REG:
    L.append(f"- `regression/{w}`")
L.append("")
open(os.path.join(D, "TEST_REPORT.md"), "w").write("\n".join(L))
print(f"TEST_REPORT.md: engine {ep}/{len(E)} PASS ({ek} known FAIL, {eu} unexpected), static "
      f"{sum(r['pass'] for r in S)}/{len(S)}, reproducibility {sum(r['pass'] for r in P)}/{len(P)}, "
      f"{len(RUNTIME)} NOT VERIFIED")
