| Host rate | v1.0.1 (% of one core) | v1.0.2-rc1 (% of one core) | change |
|---|---|---|---|
| 44100 Hz | 3.3 | 3.3 | +0% |
| 48000 Hz | 3.1 | 3.5 | +13% |
| 88200 Hz | 6.0 | 6.9 | +15% |
| 96000 Hz | 6.7 | 6.7 | +0% |
| 192000 Hz | 13.6 | 12.0 | -12% |

C build (`tests/bench_engine.c`), stereo, TRUE STEREO mode, TIME 380 ms, FEEDBACK 5, modulation on, 128-sample blocks, best of 3 runs, Intel Xeon 2.1 GHz shared VM (2 vCPU). Differences of this size are measurement noise on a shared VM. **This is not a measurement inside Ableton Live.**
