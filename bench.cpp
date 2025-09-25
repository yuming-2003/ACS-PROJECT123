
#include <iostream>
#include <iomanip>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <filesystem>
#include <cmath>
#include <limits>
#include <cstdlib>
#include <cstring>
#include "kernels.hpp"

using clk = std::chrono::high_resolution_clock;
using ns  = std::chrono::nanoseconds;



struct Cmd {
    std::string kernel = "saxpy"; // saxpy,dot,mul,stencil3
    std::string dtype  = "f32";   // f32,f64
    size_t N = 1<<20;
    size_t reps = 3;
    size_t warmup = 1;
    size_t stride = 1;
    size_t align_bytes = 64;      // alignment for aligned allocation
    size_t misalign = 0;          // additional byte offset to induce misalignment
    bool   flush_to_zero = false; // set FTZ/DAZ (x86 only via MXCSR), best-effort
    unsigned seed = 12345;
    std::string csv_path = "results/default_results.csv";
};

static inline void set_ftz_daz(bool enable) {
#if defined(__x86_64__) || defined(__i386__)
    if (!enable) return;
    #include <xmmintrin.h>
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
    _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
#else
    (void)enable;
#endif
}

static void* aligned_alloc_bytes(size_t bytes, size_t align, size_t misalign_bytes) {
#if defined(_MSC_VER)
    void* p = _aligned_malloc(bytes + align + misalign_bytes, align);
    if (!p) throw std::bad_alloc();
    return (void*)((uintptr_t)p + misalign_bytes);
#else
    void* base = nullptr;
    if (posix_memalign(&base, align, bytes + align + misalign_bytes)) throw std::bad_alloc();
    return (void*)((uintptr_t)base + misalign_bytes);
#endif
}

template<class T>
struct Buffers {
    T* x; T* y; T* z; // z for mul/stencil
    void* base; // for freeing if needed
};

template<class T>
Buffers<T> make_buffers(size_t N, size_t align, size_t misalign) {
    size_t bytes = sizeof(T) * N * 2 + sizeof(T) * N; // x,y,z
    void* raw = nullptr;
#if defined(_MSC_VER)
    raw = _aligned_malloc(bytes + align + misalign, align);
    if (!raw) throw std::bad_alloc();
    char* p = reinterpret_cast<char*>(raw) + misalign;
#else
    if (posix_memalign(&raw, align, bytes + align + misalign)) throw std::bad_alloc();
    char* p = reinterpret_cast<char*>(raw) + misalign;
#endif
    T* x = reinterpret_cast<T*>(p);
    T* y = x + N;
    T* z = y + N;
    return Buffers<T>{x,y,z,raw};
}

template<class T>
void init_data(Buffers<T>& B, size_t N, unsigned seed) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> dist(1.0, 2.0); // avoid zeros/denormals
    for (size_t i=0;i<N;i++) {
        B.x[i] = static_cast<T>(dist(rng));
        B.y[i] = static_cast<T>(dist(rng));
        B.z[i] = T(0);
    }
}

struct Stats {
    double time_ms;
    double gflops;
    double cpe; // cycles per element (approx, using steady_clock frequency if available via rdtsc? we use cpu MHz guess)
    // For portability, cpe is computed using std::chrono and an optional --cpu_ghz env.
};

static double env_cpu_ghz() {
    const char* v = std::getenv("CPU_GHZ");
    if (!v) return 0.0;
    return std::atof(v);
}

template<class F>
Stats time_kernel(size_t reps, size_t N, double flops_per_elem, F&& f) {
    // warmups inside caller
    double best_ms = 1e300;
    for (size_t r=0; r<reps; ++r) {
        auto t0 = clk::now();
        f();
        auto t1 = clk::now();
        double ms = std::chrono::duration<double, std::milli>(t1-t0).count();
        best_ms = std::min(best_ms, ms);
    }
    double gflops = (N * flops_per_elem) / (best_ms * 1e-3) / 1e9;
    double ghz = env_cpu_ghz();
    double cpe = 0.0;
    if (ghz > 0) {
        double cycles = best_ms * 1e-3 * ghz * 1e9;
        cpe = cycles / double(N);
    } else {
        cpe = std::numeric_limits<double>::quiet_NaN();
    }
    return Stats{best_ms, gflops, cpe};
}

static void ensure_dir(const std::string& path) {
    std::filesystem::create_directories(std::filesystem::path(path).parent_path());
}

static void write_csv_header_if_new(const std::string& path) {
    if (std::filesystem::exists(path)) return;
    ensure_dir(path);
    std::ofstream f(path);
    f << "timestamp,kernel,dtype,N,stride,misalign,variant,time_ms,gflops,cpe\n";
}

static void append_csv(const std::string& path, const std::string& kernel, const std::string& dtype,
                       size_t N, size_t stride, size_t misalign, const std::string& variant,
                       const Stats& S) {
    std::ofstream f(path, std::ios::app);
    auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    f << std::put_time(std::localtime(&now), "%F %T") << ","
      << kernel << "," << dtype << "," << N << "," << stride << "," << misalign << ","
      << variant << "," << std::fixed << std::setprecision(6) << S.time_ms << ","
      << S.gflops << "," << S.cpe << "\n";
}

static Cmd parse(int argc, char** argv) {
    Cmd c;
    for (int i=1;i<argc;i++) {
        std::string a = argv[i];
        auto next = [&](const char* flag){ if (i+1>=argc) { fprintf(stderr,"Missing value for %s\n",flag); std::exit(1);} return std::string(argv[++i]); };
        if (a=="--kernel") c.kernel = next("--kernel");
        else if (a=="--dtype") c.dtype = next("--dtype");
        else if (a=="--N") c.N = std::stoull(next("--N"));
        else if (a=="--reps") c.reps = std::stoull(next("--reps"));
        else if (a=="--warmup") c.warmup = std::stoull(next("--warmup"));
        else if (a=="--stride") c.stride = std::stoull(next("--stride"));
        else if (a=="--align") c.align_bytes = std::stoull(next("--align"));
        else if (a=="--misalign") c.misalign = std::stoull(next("--misalign"));
        else if (a=="--csv") c.csv_path = next("--csv");
        else if (a=="--seed") c.seed = std::stoul(next("--seed"));
        else if (a=="--ftz") c.flush_to_zero = true;
        else {
            fprintf(stderr, "Unknown arg: %s\n", a.c_str());
            std::exit(1);
        }
    }
    return c;
}

template<class T>
int run_typed(const Cmd& c, const std::string& variant) {
    set_ftz_daz(c.flush_to_zero);
    auto B = make_buffers<T>(c.N * c.stride + 8, c.align_bytes, c.misalign); // room for stride
    init_data(B, c.N * c.stride + 8, c.seed);
    T a = T(1.111), b = T(2.222), cc = T(0.333);

    // warmup
    for (size_t w=0; w<c.warmup; ++w) {
        if (c.kernel=="saxpy")      kernel_saxpy<T>(c.N, a, B.x, B.y, c.stride);
        else if (c.kernel=="dot") {
            volatile T sink = B.y[0];  // keep y in use
                if (c.kernel == "dot") {
                    // capture the dot result and use it
                    sink += kernel_dot<T>(c.N, B.x, B.y, c.stride);
                }
            (void)sink;
        }
        else if (c.kernel=="mul")   kernel_mul<T>(c.N, B.x, B.y, B.z, c.stride);
        else if (c.kernel=="stencil3") kernel_stencil3<T>(c.N, a,b,cc, B.x, B.y, c.stride);
    }

    double flops_elem = 0.0;
    if (c.kernel=="saxpy") flops_elem = flops_per_elem_saxpy();
    else if (c.kernel=="dot") flops_elem = flops_per_elem_dot();
    else if (c.kernel=="mul") flops_elem = flops_per_elem_mul();
    else if (c.kernel=="stencil3") flops_elem = flops_per_elem_stencil3();
    else { fprintf(stderr,"Unknown kernel\n"); return 1; }

    Stats S = time_kernel(c.reps, c.N, flops_elem, [&](){
        if (c.kernel=="saxpy")      kernel_saxpy<T>(c.N, a, B.x, B.y, c.stride);
        else if (c.kernel=="dot")   (void)kernel_dot<T>(c.N, B.x, B.y, c.stride);
        else if (c.kernel=="mul")   kernel_mul<T>(c.N, B.x, B.y, B.z, c.stride);
        else if (c.kernel=="stencil3") kernel_stencil3<T>(c.N, a,b,cc, B.x, B.y, c.stride);
    });

    write_csv_header_if_new(c.csv_path);
    append_csv(c.csv_path, c.kernel, (sizeof(T)==4?"f32":"f64"), c.N, c.stride, c.misalign, variant, S);
    // minimal correctness check so compilers don't DCE the loops
    volatile T sink = B.y[0] + (sizeof(T)==4? T(0.5f):T(0.5));
    (void)sink;
#if defined(_MSC_VER)
    _aligned_free(B.base);
#else
    free(B.base);
#endif
    return 0;
}

int main(int argc, char** argv) {
    Cmd c = parse(argc, argv);

    // Detect variant by compilation flag hack: if -fno-tree-vectorize used, we name it "scalar"
#if defined(__clang__) || defined(__GNUC__)
    #if defined(__OPTIMIZE__)
        // We can't detect -fno-tree-vectorize reliably at runtime; rely on binary name.
    #endif
#endif
    std::string exe = std::filesystem::path(argv[0]).filename().string();
    std::string variant = (exe.find("scalar")!=std::string::npos) ? "scalar" : "simd";

    if (c.dtype=="f32") return run_typed<float>(c, variant);
    else                return run_typed<double>(c, variant);
}
