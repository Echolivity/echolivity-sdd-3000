# CPU and latency benchmark report — v1.0.2-rc4

**rc4 update:** the EXT loop adds one send ceiling per channel. Quick check (C build, 48 kHz, block 128, 1 instance, same VM): rc4 4.4 % vs rc3 3.8 % of one core (includes VM noise). Plugin latency stays 0; the external loop itself adds Live's routing latency to each EXT repeat (see Manual).

## 1. Latency (three different things)

| Quantity | What it is | ECHOLIVITY | Status |
|---|---|---|---|
| Plugin-reported latency (PDC) | samples the device asks Live to compensate | **0**: patcher `latency: 0`; no look-ahead, no internal buffering | value in file: static PASS; Live's readout: **BLOCKED** (L-14) |
| Processing delay of the DSP | inherent signal delay | direct path **0 samples**; effect path at TIME 0: 1 sample (44.1/48 kHz), 3 samples (96 kHz) of filter group delay (test 40) | measured (C build) |
| Audio-buffer latency | Live's I/O buffer (e.g. 128 samples ≈ 2.9 ms at 44.1 kHz), the same for every device | not a device property | n/a |

Because PDC is 0 and the dry path has no delay, inserting ECHOLIVITY adds no latency beyond Live's own buffer. Not observed in Live.

## 2. CPU — C build of the gen~ code (NOT Live)

`tests/bench_engine.c`, gcc -O2, one thread, Intel Xeon 2.1 GHz shared VM (2 vCPU). Each instance has independent state; 8 instances run sequentially on one core (Live would spread tracks across cores, so this is the worst case). TRUE STEREO, modulation on. *Automation* = time, feedback, intensity and balance change every block. *HOLD+FB10* = FEEDBACK 10 with HOLD engaged after 1 s. Values: average % of one core.

| Rate | Block | 1× static | 1× automation | 1× HOLD+FB10 | 8× static | 8× automation | 8× HOLD+FB10 |
|---|---|---|---|---|---|---|---|
| 44.1 kHz | 32 | 3.7 | 3.7 | 3.6 | 30.6 | 29.7 | 29.0 |
| 44.1 kHz | 64 | 3.6 | 3.7 | 2.8 | 28.3 | 30.2 | 24.9 |
| 44.1 kHz | 128 | 2.8 | 3.4 | 3.7 | 30.9 | 24.9 | 30.3 |
| 44.1 kHz | 256 | 3.5 | 3.6 | 3.7 | 33.6 | 33.6 | 30.8 |
| 44.1 kHz | 512 | 2.8 | 2.8 | 3.7 | 31.7 | 29.0 | 27.7 |
| 44.1 kHz | 1024 | 3.4 | 3.4 | 3.5 | 28.2 | 32.1 | 30.0 |
| 48 kHz | 32 | 3.9 | 4.0 | 4.3 | 34.3 | 33.9 | 30.9 |
| 48 kHz | 64 | 3.0 | 3.7 | 4.0 | 32.0 | 31.9 | 31.4 |
| 48 kHz | 128 | 4.2 | 4.0 | 4.0 | 32.2 | 29.5 | 31.2 |
| 48 kHz | 256 | 3.8 | 3.6 | 4.3 | 32.3 | 32.7 | 32.5 |
| 48 kHz | 512 | 4.1 | 3.9 | 4.1 | 31.5 | 35.6 | 30.7 |
| 48 kHz | 1024 | 4.3 | 4.0 | 4.0 | 31.7 | 36.5 | 30.8 |
| 88.2 kHz | 32 | 7.2 | 7.0 | 6.9 | 56.6 | 58.5 | 53.3 |
| 88.2 kHz | 64 | 7.2 | 8.1 | 7.5 | 60.4 | 61.6 | 56.0 |
| 88.2 kHz | 128 | 6.3 | 7.4 | 6.3 | 56.2 | 57.9 | 56.2 |
| 88.2 kHz | 256 | 6.6 | 7.6 | 7.2 | 57.5 | 58.8 | 61.2 |
| 88.2 kHz | 512 | 7.3 | 6.7 | 6.6 | 54.3 | 50.8 | 60.5 |
| 88.2 kHz | 1024 | 8.2 | 7.8 | 6.7 | 68.2 | 57.5 | 60.5 |
| 96 kHz | 32 | 7.8 | 8.4 | 8.0 | 74.2 | 67.1 | 61.0 |
| 96 kHz | 64 | 6.8 | 9.4 | 8.1 | 64.0 | 63.4 | 66.5 |
| 96 kHz | 128 | 6.8 | 8.0 | 9.6 | 65.4 | 62.1 | 59.0 |
| 96 kHz | 256 | 7.8 | 7.8 | 7.8 | 62.2 | 72.1 | 60.8 |
| 96 kHz | 512 | 7.1 | 6.9 | 8.5 | 63.1 | 62.0 | 55.0 |
| 96 kHz | 1024 | 7.5 | 7.5 | 9.6 | 66.9 | 63.7 | 61.2 |

Findings (C build):
- Cost is independent of block size, and automation or HOLD + FEEDBACK 10 do not raise it (differences are within run-to-run noise).
- Roughly 3–4 % of one core per instance at 44.1/48 kHz, 7–9 % at 88.2/96 kHz; 8 instances ≈ 30 % / 55–70 % of one core.
- v1.0.2 costs the same as v1.0.1 (`docs/measurements/cpu_c_build.md`).
- The worst single-block times in `cpu_grid_rc1.csv` (up to 50× a block's duration) come from OS preemption on a shared, non-real-time VM. They are **not** evidence about dropouts in Live.

## 3. In Live — BLOCKED

CPU meter readings at 44.1/48/88.2/96 kHz × buffer 64/128/256/512/1024 with 1 and 8 instances, during automation and with HOLD + feedback, plus the PDC readout, are checklist items L-13 and L-14. gen~ generates and compiles its own code, Max adds scheduling and Live adds device overhead, so absolute numbers will differ from this table.
