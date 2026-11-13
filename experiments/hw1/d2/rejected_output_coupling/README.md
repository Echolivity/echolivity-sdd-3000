# REJECTED: D2-oc (1 Hz output AC coupling)

This variant is kept only for the record and for reproducibility (`make_d.py --d2-oc`).

| Effect | Result |
|---|---|
| FB 10 tail offset | Removed: 0/30 seeds, max 6.1e-4 (`audit_fb10.json`) |
| FB 10 peak | −12.4 dBFS against a −13 dBFS bound |
| BYPASS release stale echo | −169 dBFS against −180 dBFS |
| HOLD release convergence to never-held at T + 80 ms | −80 to −110 dB against −120 dB |

It caused three regressions against original thresholds (`audit_engine_suite.json`, 40/51). Per the brief, the correction was stopped and not adopted.

- `audit_hold.json`, `audit_spectral.json` and `audit_timing.json` were measured on D2-oc. In those files the key `candidate_D2` refers to D2-oc.
- The factory-program run was stopped when the regression was found.
