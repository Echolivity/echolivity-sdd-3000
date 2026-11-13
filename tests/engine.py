"""ctypes wrapper around the C build of the gen~ codebox (see tools/gen2c.py)."""
import ctypes, os, subprocess, sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GEN = os.path.join(ROOT, "src", "gen", "echolivity_core.genexpr")
BUILD_DIR = os.path.join(ROOT, "build")
CSRC = os.path.join(BUILD_DIR, "engine.c")
SO = os.path.join(BUILD_DIR, "engine.so")
# v1.0.2: reference build of the previous release's DSP for A/B regression comparisons
REF_GEN = os.path.join(ROOT, "tests", "reference", "echolivity_core_v1.0.1.genexpr")
REF_SO = os.path.join(BUILD_DIR, "engine_v1.0.1.so")
# v1.0.2-rc4: reference build of the rc1/rc2/rc3 DSP (identical in all three) for the EXT-loop A/B test
REF3_GEN = os.path.join(ROOT, "tests", "reference", "echolivity_core_v1.0.2-rc3.genexpr")
REF3_SO = os.path.join(BUILD_DIR, "engine_v1.0.2-rc3.so")
# v1.0.2-rc5: reference build of the rc4 DSP for the LOOP COMP / CAL / triplet A/B test
REF4_GEN = os.path.join(ROOT, "tests", "reference", "echolivity_core_v1.0.2-rc4.genexpr")
REF4_SO = os.path.join(BUILD_DIR, "engine_v1.0.2-rc4.so")
# HW-1 (candidate branch): the shipping v1.0.2 DSP, as the reference for population comparisons
REF5_GEN = os.path.join(ROOT, "tests", "reference", "echolivity_core_v1.0.2.genexpr")
REF5_SO = os.path.join(BUILD_DIR, "engine_v1.0.2.so")


def build():
    # v1.0.1: build/ is a generated directory and is not shipped; create it so the
    # documented test command works from a clean extraction.
    os.makedirs(BUILD_DIR, exist_ok=True)
    py = sys.executable or "python3"
    cc = os.environ.get("CC", "gcc")
    subprocess.check_call([py, os.path.join(ROOT, "tools", "make_gen.py")])
    subprocess.check_call([py, os.path.join(ROOT, "tools", "gen2c.py"), GEN, CSRC])
    subprocess.check_call([cc, "-O2", "-shared", "-fPIC", "-o", SO, CSRC, "-lm"])
    if os.path.exists(REF_GEN):
        ref_c = os.path.join(BUILD_DIR, "engine_v1.0.1.c")
        subprocess.check_call([py, os.path.join(ROOT, "tools", "gen2c.py"), REF_GEN, ref_c])
        subprocess.check_call([cc, "-O2", "-shared", "-fPIC", "-o", REF_SO, ref_c, "-lm"])
    if os.path.exists(REF3_GEN):
        ref_c = os.path.join(BUILD_DIR, "engine_v1.0.2-rc3.c")
        subprocess.check_call([py, os.path.join(ROOT, "tools", "gen2c.py"), REF3_GEN, ref_c])
        subprocess.check_call([cc, "-O2", "-shared", "-fPIC", "-o", REF3_SO, ref_c, "-lm"])
    if os.path.exists(REF4_GEN):
        ref_c = os.path.join(BUILD_DIR, "engine_v1.0.2-rc4.c")
        subprocess.check_call([py, os.path.join(ROOT, "tools", "gen2c.py"), REF4_GEN, ref_c])
        subprocess.check_call([cc, "-O2", "-shared", "-fPIC", "-o", REF4_SO, ref_c, "-lm"])
    if os.path.exists(REF5_GEN):
        ref_c = os.path.join(BUILD_DIR, "engine_v1.0.2.c")
        subprocess.check_call([py, os.path.join(ROOT, "tools", "gen2c.py"), REF5_GEN, ref_c])
        subprocess.check_call([cc, "-O2", "-shared", "-fPIC", "-o", REF5_SO, ref_c, "-lm"])


class Engine:
    VEC = 64   # gen~ applies Param messages at signal-vector boundaries

    def __init__(self, sr=48000.0, so=None, **params):
        # private copy of the shared object -> fully isolated state per instance
        import tempfile, shutil
        lib = so or SO
        if not os.path.exists(lib):
            raise FileNotFoundError(f"{lib} not found - call engine.build() first "
                                    "(tests/run_tests.py does this automatically)")
        fd, path = tempfile.mkstemp(suffix=".so"); os.close(fd)
        shutil.copy(lib, path)
        self.lib = ctypes.CDLL(path)
        os.unlink(path)
        self.lib.set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]
        self.lib.get_param.argtypes = [ctypes.c_char_p]
        self.lib.get_param.restype = ctypes.c_double
        self.lib.reset.argtypes = [ctypes.c_double]
        self.lib.bounds_errors.restype = ctypes.c_long
        self.lib.process.argtypes = [ctypes.POINTER(ctypes.c_double)] * 3 + [ctypes.c_int]
        self.sr = float(sr)
        self.lib.reset(self.sr)
        # factory default state of the device
        self.set(**params)

    def set(self, **params):
        for k, v in params.items():
            name = k if k.startswith("p_") else "p_" + k
            if not self.lib.set_param(name.encode(), float(v)):
                raise KeyError(name)

    def get(self, k):
        name = k if k.startswith("p_") else "p_" + k
        return self.lib.get_param(name.encode())

    def run(self, inL, inR=None, automation=None, ret=None, loop_latency=None):
        """automation: list of (sample_index, {param: value}) applied at vector boundaries.
        v1.0.2-rc4: ret = (in3, in4) arrays feed the EXT-loop return inputs directly;
        loop_latency = N samples models a Live track routing outs 3/4 back into ins 3/4 with an
        N-sample delay (N >= one vector, as Live routes block by block)."""
        P = ctypes.POINTER(ctypes.c_double)
        inL = np.ascontiguousarray(inL, dtype=np.float64)
        inR = inL.copy() if inR is None else np.ascontiguousarray(inR, dtype=np.float64)
        n = len(inL)
        no = self.lib.num_outs()
        outs = np.zeros((no, n))
        four = ret is not None or loop_latency is not None
        if four:
            r3 = np.zeros(n) if ret is None else np.array(ret[0], dtype=np.float64)
            r4 = np.zeros(n) if ret is None else np.array(ret[1], dtype=np.float64)
            self.lib.process4.argtypes = [P] * 5 + [ctypes.c_int]
        auto = sorted(automation or [], key=lambda a: a[0])
        ai = 0
        pos = 0
        while pos < n:
            while ai < len(auto) and auto[ai][0] <= pos:
                self.set(**auto[ai][1]); ai += 1
            m = min(self.VEC, n - pos)
            o = np.zeros(no * m)
            if four:
                self.lib.process4(inL[pos:].ctypes.data_as(P), inR[pos:].ctypes.data_as(P),
                                  r3[pos:].ctypes.data_as(P), r4[pos:].ctypes.data_as(P),
                                  o.ctypes.data_as(P), m)
            else:
                self.lib.process(inL[pos:].ctypes.data_as(P), inR[pos:].ctypes.data_as(P),
                                 o.ctypes.data_as(P), m)
            outs[:, pos:pos + m] = o.reshape(no, m)
            if loop_latency is not None:
                a0, a1 = pos + loop_latency, min(pos + m + loop_latency, n)
                if a1 > a0:
                    r3[a0:a1] = outs[5, pos:pos + (a1 - a0)]
                    r4[a0:a1] = outs[6, pos:pos + (a1 - a0)]
            pos += m
        return outs

    def silence(self, seconds):
        return self.run(np.zeros(int(seconds * self.sr)))

    def bounds_errors(self):
        return self.lib.bounds_errors()

    def change_samplerate(self, sr):
        """Change the host rate WITHOUT resetting state (worst case: gen~ keeps its
        Histories/Data across a DSP restart). Test-harness only; not part of the DSP."""
        self.lib.set_samplerate.argtypes = [ctypes.c_double]
        self.lib.set_samplerate(float(sr))
        self.sr = float(sr)

    def set_raw(self, name, value):
        """Store a value without the harness' min/max clamp (models a message that
        bypasses Param clamping, e.g. NaN, whose gen~ handling is NOT VERIFIED)."""
        self.lib.set_param_raw.argtypes = [ctypes.c_char_p, ctypes.c_double]
        return self.lib.set_param_raw(name.encode(), float(value))
