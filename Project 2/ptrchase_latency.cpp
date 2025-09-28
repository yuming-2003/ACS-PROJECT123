#include <bits/stdc++.h>
#include <x86intrin.h>
using namespace std;

// Return TSC with ordering (serialize loads around it).
static inline uint64_t rdtsc_serialized() {
    unsigned aux;
    _mm_lfence();
    uint64_t t = __rdtscp(&aux);
    _mm_lfence();
    return t;
}

static vector<uint32_t> make_random_cycle(size_t N) {
    vector<uint32_t> idx(N);
    iota(idx.begin(), idx.end(), 0);
    // quality RNG matters less than permutation; mt19937_64 is fine
    mt19937_64 rng(123456789ULL);
    shuffle(idx.begin(), idx.end(), rng);
    vector<uint32_t> next(N);
    for (size_t i = 0; i + 1 < N; ++i) next[idx[i]] = idx[i+1];
    next[idx.back()] = idx[0];
    return next;
}

// Run a dependent chain over 'next' and return ns/load and cycles/load (median over trials).
struct Result { double cycles_per_load, ns_per_load; };
static Result measure_chain(vector<uint32_t>& next, size_t hops, int trials, double ghz) {
    vector<double> cyc;
    cyc.reserve(trials);
    volatile uint32_t cur = 0;

    // Warm-up to touch the list
    for (size_t i = 0; i < 100000; ++i) cur = next[cur];

    for (int t = 0; t < trials; ++t) {
        cur = (t & 1) ? 0 : cur; // small perturbation
        uint64_t t0 = rdtsc_serialized();
        for (size_t i = 0; i < hops; ++i) cur = next[cur];
        uint64_t t1 = rdtsc_serialized();
        double cycles = double(t1 - t0) / double(hops);
        cyc.push_back(cycles);
    }
    nth_element(cyc.begin(), cyc.begin() + cyc.size()/2, cyc.end());
    double med_cycles = cyc[cyc.size()/2];
    return { med_cycles, med_cycles / ghz }; // ns = cycles / GHz
}

int main(int argc, char** argv) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Defaults for 5800X (edit if needed)
    const double freq_GHz = 3.8;     // use your observed clock if you prefer
    const size_t sizes_bytes[] = { 16*1024ULL, 256*1024ULL, 16*1024*1024ULL, 256*1024*1024ULL };
    const size_t hops = 50'000'00ULL; // 5e7; reduce if it runs too long on DRAM
    const int trials = 9;

    cout << fixed << setprecision(2);
    cout << "freq_GHz=" << freq_GHz << "\n";
    cout << "bytes,entries,cycles/load,ns/load\n";

    for (size_t bytes : sizes_bytes) {
        size_t N = bytes / sizeof(uint32_t);
        auto next = make_random_cycle(N);
        auto r = measure_chain(next, hops, trials, freq_GHz);
        cout << bytes << "," << N << "," << r.cycles_per_load << "," << r.ns_per_load << "\n";
    }
    return 0;
}
