# Preset compatibility report — v1.0.2-rc4

## Static checks (executed): `tools/check_compat.py`, v1.0.1 device vs rc4 device

| Check | Status | Detail |
|---|---|---|
| same parameter set (long names) | PASS (static) | 158 vs 158; only in old: []; only in new: [] |
| identical definitions (type, range, enum, initial, visibility, units, object, scripting name) | PASS (static) | 158/158 identical |
| other attributes: only Modulation Mode / recall Order differ (intended in 1.0.2-rc3) | PASS (static) | 157 parameters differ only in ['parameter_modmode', 'parameter_order'] |
| identical Push/Configure banks | PASS (static) | 3 banks |
| automatable / stored-only split | PASS (static) | 38 automatable + 120 stored-only |
| factory programs in the device == presets/factory_programs.json | PASS (static) | 120/120 stored values match |
| factory programs file unchanged since v1.0 | PASS | `presets/factory_programs.json` matches `docs/baseline/v1.0_core_files.sha256` |

Interpretation: Live identifies device parameters by their long names. All 158 are present with identical definitions (rc3 adds only Modulation Mode on 13 dials and a recall Order; neither changes stored values), so Sets and `.adv` presets saved with v1.0, v1.0.1 or rc1 address the same parameters with the same ranges. **That Live actually restores them is BLOCKED (L-7, L-8).**

## The two documented edge cases

| Edge case | Finding | Status |
|---|---|---|
| `.adv` hot-loading | **D-1:** root cause traced. The start-up sequence re-runs on every preset load (documented `live.thisdevice` behaviour) while program logic is enabled, so the active slot is recalled over the restored panel. In M this restores the stale manual snapshot. Predicted repro L-7a. | fix applied in rc3; confirmation in Live BLOCKED (L-7a) |
| Program re-selection | **D-2:** if `live.tab` re-outputs on a click on the selected cell, re-selecting M restores the stale manual snapshot. Predicted repro L-7b. | suspected; reproduction BLOCKED |

Set save/reopen is not affected by D-1: on a fresh instance, program logic stays disabled until initialisation completes. Details: `DEFECTS.md`.
