/* Pure-C CPU benchmark of a gen2c engine build (the translated gen~ code). NOT a measurement in Live.
   Build:  gcc -O2 -o bench tests/bench_engine.c -ldl
   Run:    ./bench build/engine.so                  (table: rates x block sizes x scenarios, 1 and 8 instances)
           ./bench build/engine.so quick            (48 kHz / 128 only, 1 instance; the v1.0.2-rc1 table)
   Each instance is a private copy of the shared object (independent state), processed sequentially on one
   thread: the 8-instance figure is the single-core worst case (Live spreads tracks across cores). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <dlfcn.h>
#include <unistd.h>

typedef void (*reset_t)(double);
typedef int (*setp_t)(const char*, double);
typedef void (*proc_t)(const double*, const double*, double*, int);
typedef struct { void* h; reset_t reset; setp_t setp; proc_t proc; } inst_t;

static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

static int load(inst_t* in, const char* so, int k){
  char path[256]; snprintf(path, sizeof path, "/tmp/echolivity_bench_%d_%d.so", (int)getpid(), k);
  FILE* a = fopen(so, "rb"); FILE* b = fopen(path, "wb"); if(!a || !b) return 0;
  char buf[65536]; size_t n; while((n = fread(buf, 1, sizeof buf, a)) > 0) fwrite(buf, 1, n, b);
  fclose(a); fclose(b);
  in->h = dlopen(path, RTLD_NOW | RTLD_LOCAL); unlink(path); if(!in->h) return 0;
  in->reset = (reset_t)dlsym(in->h, "reset"); in->setp = (setp_t)dlsym(in->h, "set_param");
  in->proc = (proc_t)dlsym(in->h, "process"); return in->reset && in->setp && in->proc;
}

/* scenario 0 = static, 1 = automation every block, 2 = HOLD + FEEDBACK 10 */
static void run(inst_t* I, int ninst, double sr, int B, int scen, double secs, double* pct, double* worst){
  for(int k = 0; k < ninst; k++){
    I[k].reset(sr);
    I[k].setp("p_time_ms", 380 + 37 * k); I[k].setp("p_feedback", scen == 2 ? 10 : 5);
    I[k].setp("p_intensity", 5); I[k].setp("p_frequency", 4); I[k].setp("p_out_mode", 3);
  }
  int n = (int)(sr * secs); double *x = malloc(sizeof(double) * n), *o = malloc(sizeof(double) * 8 * B);   /* rc4: up to 8 gen~ outputs (7 used) */
  srand(1); for(int i = 0; i < n; i++) x[i] = ((rand() / (double)RAND_MAX) - 0.5) * 0.2;
  double t0 = now(), wmax = 0; int blk = 0;
  for(int i = 0; i + B <= n; i += B, blk++){
    double tb = now();
    for(int k = 0; k < ninst; k++){
      if(scen == 1){
        I[k].setp("p_time_ms", 50 + (blk * 7 + k * 13) % 900); I[k].setp("p_feedback", (blk % 100) * 0.09);
        I[k].setp("p_intensity", (blk % 50) * 0.2); I[k].setp("p_balance", (blk % 40) * 0.25);
      }
      if(scen == 2 && i >= (int)sr) I[k].setp("p_hold", 1);
      I[k].proc(x + i, x + i, o, B);
    }
    double dt = now() - tb; if(dt > wmax) wmax = dt;
  }
  double tot = now() - t0;
  *pct = 100.0 * tot / secs; *worst = 100.0 * wmax / (B / sr);
  free(x); free(o);
}

int main(int argc, char** argv){
  if(argc < 2){ fprintf(stderr, "usage: %s engine.so [quick]\n", argv[0]); return 1; }
  inst_t I[8];
  for(int k = 0; k < 8; k++) if(!load(&I[k], argv[1], k)){ fprintf(stderr, "cannot load %s\n", argv[1]); return 1; }
  if(argc > 2 && !strcmp(argv[2], "quick")){
    double p, w; run(I, 1, 48000, 128, 0, 20, &p, &w);
    printf("48000 Hz, block 128, 1 instance: %.1f%% of one core\n", p); return 0;
  }
  double rates[] = {44100, 48000, 88200, 96000}; int blocks[] = {32, 64, 128, 256, 512, 1024};
  const char* sc[] = {"static", "automation", "HOLD+FB10"};
  printf("rate,block,instances,scenario,avg_pct_one_core,worst_block_pct_of_block_time\n");
  for(int r = 0; r < 4; r++) for(int bi = 0; bi < 6; bi++) for(int ni = 0; ni < 2; ni++) for(int s = 0; s < 3; s++){
    int ninst = ni ? 8 : 1; double p, w;
    run(I, ninst, rates[r], blocks[bi], s, ninst == 8 ? 4.0 : 6.0, &p, &w);
    printf("%.0f,%d,%d,%s,%.2f,%.1f\n", rates[r], blocks[bi], ninst, sc[s], p, w); fflush(stdout);
  }
  return 0;
}
