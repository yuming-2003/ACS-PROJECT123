#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>

static inline uint64_t rdtsc() {
    unsigned hi, lo;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

void run_saxpy(float *x, float *y, size_t N, size_t stride, int pattern) {
    size_t *idx = NULL;
    if (pattern == 2) { // random
        idx = (size_t*)malloc(N * sizeof(size_t));
        for (size_t i = 0; i < N; i++) idx[i] = i;
        for (size_t i = N - 1; i > 0; i--) {
            size_t j = (size_t)(rand() % (i + 1));
            size_t t = idx[i]; idx[i] = idx[j]; idx[j] = t;
        }
    }
    const float a = 1.1f;
    for (size_t i = 0; i < N; i++) {
        size_t k = (pattern == 0) ? i :
                   (pattern == 1) ? (i * stride) % N :
                   idx[i];
        y[k] = a * x[k] + y[k];
    }
    if (idx) free(idx);
}

int main(int argc, char **argv) {
    if (argc < 6) {
        fprintf(stderr,"usage: %s ws_KiB stride pattern repeats dummy\n", argv[0]);
        return 1;
    }
    size_t ws_kib = strtoull(argv[1], 0, 10);
    size_t stride  = strtoull(argv[2], 0, 10);
    int pattern    = atoi(argv[3]);
    int repeats    = atoi(argv[4]);

    size_t bytes = ws_kib * 1024ULL;
    float *x = (float*)mmap(NULL, bytes, PROT_READ|PROT_WRITE,
                            MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    float *y = (float*)mmap(NULL, bytes, PROT_READ|PROT_WRITE,
                            MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    if (x == MAP_FAILED || y == MAP_FAILED) { perror("mmap"); return 2; }
    size_t N = bytes / sizeof(float);

    for (size_t i = 0; i < N; i++) { x[i] = 1.f; y[i] = 2.f; }

    run_saxpy(x, y, N, stride, pattern); // warmup

    uint64_t t0 = rdtsc();
    for (int r = 0; r < repeats; r++) run_saxpy(x, y, N, stride, pattern);
    uint64_t t1 = rdtsc();

    double bytes_moved = (double)N * 12.0 * repeats; // 12B per element (x+y read, y write)
    printf("ws_KiB=%zu,stride=%zu,pattern=%d,repeats=%d,cycles=%llu,bytes=%.0f\n",
           ws_kib, stride, pattern, repeats,
           (unsigned long long)(t1 - t0), bytes_moved);
    return 0;
}
