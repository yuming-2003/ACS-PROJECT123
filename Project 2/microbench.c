
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <string.h>
#include <omp.h>

#define ALIGN 64

static void* xaligned_alloc(size_t alignment, size_t size) {
    void* p = NULL;
    if (posix_memalign(&p, alignment, size)) return NULL;
    return p;
}

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

int main(int argc, char** argv) {
    if (argc < 6) {
        fprintf(stderr, "Usage: %s <N_bytes> <stride_elems> <repeats> <rw_mix_percent_read> <threads>\n", argv[0]);
        return 1;
    }

    size_t N_bytes   = strtoull(argv[1], NULL, 10);
    size_t stride    = strtoull(argv[2], NULL, 10);
    size_t repeats   = strtoull(argv[3], NULL, 10);
    int read_percent = atoi(argv[4]);  // 0..100
    int nthreads     = atoi(argv[5]);

    size_t N = N_bytes / sizeof(float);
    float *x = (float*)xaligned_alloc(ALIGN, N * sizeof(float));
    float *y = (float*)xaligned_alloc(ALIGN, N * sizeof(float));
    if (!x || !y) { fprintf(stderr, "alloc failed\n"); return 1; }

    for (size_t i=0; i<N; i++) { x[i] = 1.0f; y[i] = 2.0f; }

    omp_set_num_threads(nthreads);

    double t0 = now_sec();
    #pragma omp parallel
    {
        unsigned int seed = 1234 + omp_get_thread_num();
        for (size_t r=0; r<repeats; r++) {
            #pragma omp for schedule(static)
            for (size_t i=0; i<N; i+=stride) {
                int roll = rand_r(&seed) % 100;
                if (roll < read_percent) {
                    float tmp = x[i]; // read
                    (void)tmp;
                } else {
                    y[i] += 1.0f;     // write
                }
            }
        }
    }
    double t1 = now_sec();

    double secs = t1 - t0;
    double bytes_accessed = (double)(N/stride) * repeats * sizeof(float);
    double gib = bytes_accessed / (1024.0*1024.0*1024.0);
    double gibps = gib / secs;

    printf("N_bytes=%zu,stride=%zu,repeats=%zu,read%%=%d,threads=%d,time=%.6f,GiB/s=%.3f\n",
           N_bytes, stride, repeats, read_percent, nthreads, secs, gibps);

    free(x); free(y);
    return 0;
}
