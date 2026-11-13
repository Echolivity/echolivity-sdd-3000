/* Audit F: per-block CPU distribution, production vs candidate, INTERLEAVED (A,B,A,B,...) in the same
   process so VM load drift hits both equally. Same engine setup as tests/bench_engine.c (static scenario,
   modulation on, TRUE STEREO). For each config: p50 / p95 / p99 / p99.9 / max block time in % of the
   block period, and the average % of one core. Pure C build of the gen~ code; NOT a Live measurement.
   usage: bench_pct prod.so cand.so > csv */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <dlfcn.h>
#include <unistd.h>
typedef void (*reset_t)(double); typedef int (*setp_t)(const char*, double); typedef void (*proc_t)(const double*, const double*, double*, int);
typedef struct { void* h; reset_t reset; setp_t setp; proc_t proc; } inst_t;
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static int load(inst_t* in, const char* so, int k){
  char path[256]; snprintf(path, sizeof path, "/tmp/echolivity_pct_%d_%d.so", (int)getpid(), k);
  FILE* a = fopen(so, "rb"); FILE* b = fopen(path, "wb"); if(!a || !b) return 0;
  char buf[65536]; size_t n; while((n = fread(buf, 1, sizeof buf, a)) > 0) fwrite(buf, 1, n, b); fclose(a); fclose(b);
  in->h = dlopen(path, RTLD_NOW | RTLD_LOCAL); unlink(path); if(!in->h) return 0;
  in->reset = (reset_t)dlsym(in->h, "reset"); in->setp = (setp_t)dlsym(in->h, "set_param"); in->proc = (proc_t)dlsym(in->h, "process");
  return in->reset && in->setp && in->proc; }
static int cmp(const void* a, const void* b){ double x = *(const double*)a, y = *(const double*)b; return x < y ? -1 : x > y; }
int main(int argc, char** argv){
  if(argc < 3) return 1;
  inst_t P[8], C[8];
  for(int k = 0; k < 8; k++) if(!load(&P[k], argv[1], k) || !load(&C[k], argv[2], 100 + k)) return 2;
  double rates[] = {44100, 48000, 96000}; int blocks[] = {64, 128, 512}; int insts[] = {1, 8};
  double secs = 20.0;
  printf("engine,rate,block,instances,avg_pct_core,p50,p95,p99,p999,max\n");
  for(int r = 0; r < 3; r++) for(int bi = 0; bi < 3; bi++) for(int ii = 0; ii < 2; ii++){
    double sr = rates[r]; int B = blocks[bi], ni = insts[ii];
    inst_t* E[2] = {P, C};
    for(int e = 0; e < 2; e++) for(int k = 0; k < ni; k++){
      E[e][k].reset(sr); E[e][k].setp("p_time_ms", 380 + 37 * k); E[e][k].setp("p_feedback", 5);
      E[e][k].setp("p_intensity", 5); E[e][k].setp("p_frequency", 4); E[e][k].setp("p_out_mode", 3); }
    int n = (int)(sr * secs), nb = n / B;
    double *x = malloc(sizeof(double) * n), *o = malloc(sizeof(double) * 8 * B), *t[2];
    t[0] = malloc(sizeof(double) * nb); t[1] = malloc(sizeof(double) * nb);
    srand(1); for(int i = 0; i < n; i++) x[i] = ((rand() / (double)RAND_MAX) - 0.5) * 0.2;
    double tot[2] = {0, 0};
    for(int b = 0; b < nb; b++) for(int e0 = 0; e0 < 2; e0++){
      int e = (b & 1) ? 1 - e0 : e0;               /* alternate order every block */
      double tb = now();
      for(int k = 0; k < ni; k++) E[e][k].proc(x + b * B, x + b * B, o, B);
      double dt = now() - tb; t[e][b] = 100.0 * dt / (B / sr); tot[e] += dt; }
    for(int e = 0; e < 2; e++){
      qsort(t[e], nb, sizeof(double), cmp);
      printf("%s,%.0f,%d,%d,%.2f,%.1f,%.1f,%.1f,%.1f,%.1f\n", e ? "candidate_D" : "production", sr, B, ni, 100.0 * tot[e] / secs,
             t[e][nb / 2], t[e][(int)(nb * 0.95)], t[e][(int)(nb * 0.99)], t[e][(int)(nb * 0.999)], t[e][nb - 1]); fflush(stdout); }
    free(x); free(o); free(t[0]); free(t[1]);
  }
  return 0; }
