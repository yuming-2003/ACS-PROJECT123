
# SIMD Advantage Profiling — Project Report (ECSE 4320/6320)

> **Author:** Yuming Tseng  
> **Machine:** Apple silicon (Apple M‑series) on macOS  
> **Repo:** simd-profiling (bench + kernels in `src/`)

---

## 1) Introduction
Modern CPUs expose SIMD (Single Instruction, Multiple Data) units that act on vectors of data per instruction. This project measures the advantage of SIMD vs a scalar baseline across multiple kernels and data sizes, and explains when and why vectorization helps or doesn’t, with evidence from compiler reports and a roofline interpretation.

---

## 2) Experimental Setup

### Hardware & Software
- **CPU:** Apple M1
- **Caches:** L1D: ___ KB/core, L2: ___ MB cluster, LLC/unified: ___ MB (fill exact)  
- **Memory bandwidth (sustained):** 100GB/s 
- OS / Compiler:** macOS + `clang++`  

### Builds (how scalar vs auto‑vectorized were produced)
- **Scalar‑only baseline** (disables auto‑vectorization):  
  ```bash
  clang++ -std=c++17 -O3 -march=native -fno-vectorize -fno-slp-vectorize src/bench.cpp -o bench_scalar
  ```
- **Auto‑vectorized (SIMD) build**:  
  ```bash
  clang++ -std=c++17 -O3 -march=native -Rpass=loop-vectorize src/bench.cpp -o bench_simd
  ```
  - Evidence from compile output (examples):  
    ```text
    src/kernels.hpp:25:5: remark: vectorized loop (vectorization width: 4, interleaved count: 4)
    src/kernels.hpp:60:5: remark: vectorized loop (vectorization width: 2, interleaved count: 4)
    ```
  - The compiler confirmed auto-vectorization of the kernels.

### Kernel set chosen
- **SAXPY**
- **Stencil**  
- **Mul**

### Inputs / N sweep to span caches
For each kernel and precision (f32, f64), we swept `N` so the total working set crosses L1 → L2 → LLC → DRAM.

f32 (4 B/elem) 3 arrays (saxpy/mul):
- L1D 128 KB → N ≈ 10,922
- SLC 8 MB → N ≈ 699,050
- L2 16 MB → N ≈ 1,398,101
2 arrays (stencil):
- L1D 128 KB → N ≈ 16,384
- SLC 8 MB → N ≈ 1,048,576
- L2 16 MB → N ≈ 2,097,152

f64 (8 B/elem) 3 arrays (saxpy/mul):
- L1D 128 KB → N ≈ 5,461
- SLC 8 MB → N ≈ 349,525
- L2 16 MB → N ≈ 699,050
2 arrays (stencil):
- L1D 128 KB → N ≈ 8,192
- SLC 8 MB → N ≈ 524,288
- L2 16 MB → N ≈ 1,048,576
  
Actual `N` used (fill): `
SAXPY / MUL (3 arrays):
- f32: N = [1k, 2k, 4k, 8k, 12k, 24k, 48k, 96k, 192k, 384k, 700k, 1.4M, 2.8M, 5.6M]
(~L1 at 10.9k; ~SLC at 699k; ~L2 at 1.40M)

- f64: N = [512, 1k, 2k, 4k, 5.5k, 11k, 22k, 44k, 88k, 176k, 350k, 700k, 1.4M, 2.8M]
(~L1 at 5.5k; ~SLC at 350k; ~L2 at 700k)

STENCIL (2 arrays):
- f32: N = [2k, 4k, 8k, 16k, 32k, 64k, 128k, 256k, 512k, 1.05M, 2.1M, 4.2M]
(~L1 at 16.4k; ~SLC at 1.05M; ~L2 at 2.10M)

- f64: N = [1k, 2k, 4k, 8k, 16k, 32k, 64k, 128k, 256k, 524k, 1.05M, 2.1M]
(~L1 at 8.2k; ~SLC at 524k; ~L2 at 1.05M)

### Measurement protocol
- Warm‑up run (not timed) + **k≥5 trials**, report **median**.  
- High‑res steady‑state timer in `bench.cpp`.  
- Pinned build, same flags across runs.  

### Metrics

- **Runtime** (ms)  
- **GFLOP/s** = ops / time / 1e9  
- **Speedup** = `scalar_time / simd_time`  
- **CPE** (cycles per element) for locality sweep

---

## 3) Results (Scalar vs SIMD)

### 3.1 Baseline (scalar) vs auto-vectorized
- Shown below are 3 tables documenting scalar and auto-vectorized versions for the three chosen kernels.
- speedup = scalar time / simd time
- GFLOP/s = N/(scalar or SIMD time in seconds)
  
| Kernel | N       | Scalar Time (ms) | SIMD Time (ms) | Scalar GFLOP/s | SIMD GFLOP/s | Speedup |
|--------|---------|------------------|----------------|----------------|--------------|---------|
| mul    | 16384   | 0.005875         | 0.001083       | 2.79           | 15.13        | 5.42×   |
| mul    | 65536   | 0.020500         | 0.008208       | 3.20           | 7.98         | 2.50×   |
| mul    | 262144  | 0.082209         | 0.029708       | 3.19           | 8.82         | 2.77×   |
| mul    | 1048576 | 0.309041         | 0.133291       | 3.39           | 7.87         | 2.32×   |
| mul    | 4194304 | 1.266917         | 0.714333       | 3.31           | 5.87         | 1.77×   |
| mul    | 16777216| 5.131083         | 2.787125       | 3.27           | 6.02         | 1.84×   |
| mul    | 67108864| 20.339000        | 11.169167      | 3.30           | 6.01         | 1.82×   |


| Kernel | N       | Scalar Time (ms) | SIMD Time (ms) | Scalar GFLOP/s | SIMD GFLOP/s | Speedup |
|--------|---------|------------------|----------------|----------------|--------------|---------|
| saxpy  | 16384   | 0.015500         | 0.005125       | 2.11           | 6.39         | 3.02×   |
| saxpy  | 65536   | 0.062000         | 0.019750       | 2.11           | 6.64         | 3.14×   |
| saxpy  | 262144  | 0.157458         | 0.033166       | 3.33           | 15.81        | 4.75×   |
| saxpy  | 1048576 | 0.489083         | 0.128084       | 4.29           | 16.37        | 3.82×   |
| saxpy  | 4194304 | 1.541458         | 0.707791       | 5.44           | 11.85        | 2.18×   |
| saxpy  | 16777216| 5.531084         | 2.659334       | 6.07           | 12.62        | 2.08×   |
| saxpy  | 67108864| 23.746708        | 10.771334      | 5.65           | 12.46        | 2.20×   |


| Kernel   | N       | Scalar Time (ms) | SIMD Time (ms) | Scalar GFLOP/s | SIMD GFLOP/s | Speedup |
|----------|---------|------------------|----------------|----------------|--------------|---------|
| stencil3 | 16384   | 0.005917         | 0.001625       | 13.84          | 50.41        | 3.64×   |
| stencil3 | 65536   | 0.024709         | 0.006625       | 13.26          | 49.46        | 3.73×   |
| stencil3 | 262144  | 0.093625         | 0.025792       | 14.00          | 50.82        | 3.63×   |
| stencil3 | 1048576 | 0.388625         | 0.104250       | 13.49          | 50.29        | 3.73×   |
| stencil3 | 4194304 | 1.574458         | 0.428709       | 13.32          | 48.92        | 3.67×   |
| stencil3 | 16777216| 6.328125         | 1.773166       | 13.26          | 47.31        | 3.57×   |
| stencil3 | 67108864| 25.389333        | 7.156125       | 13.22          | 46.89        | 3.55×   |

### 3.2 Locality Sweep

<img width="575" height="459" alt="Screenshot 2025-09-24 at 12 04 28 PM" src="https://github.com/user-attachments/assets/4da199e9-51b0-4fb2-8711-5e5dfb85b292" />


- For the chosen kernel of saxpy f32, cache levels were swept through by varying the number of elements N. Shown on the graph below, we could identify that L1 was the first region, where throughput is flat and SIMD GFLOP/s grows as arithmetic dominates. Then we reach L2/LLC (on M2 chip, LLC is shared with L2) in the middle region, where SIMD experiences peak performance, reaching around 17GFLOP/S. Finally, beyond N=10^6, throughput drops to ~12–13 GFLOP/s and flattens, because memory bandwidth is now the bottleneck.

- SIMD compression: In this graph, SIMD gains compress to ~2×, because the bottleneck is memory bandwidth, meaning the vector units cannot operate faster than data can be streamed from DRAM. This is the expected behavior for a streaming, low-arithmetic-intensity kernel like SAXPY.

### 3.3 Alignment & tail handling

| Case              | N       | misalign | SIMD Time (ms) | SIMD GFLOP/s | Δ vs aligned,no-tail |
|-------------------|---------|----------|----------------|--------------|----------------------|
| Aligned, no tail  | 1,048,576 | 0      | 0.113584       | 18.463       | —                    |
| Tail only         | 1,050,000 | 0      | 0.118666       | 17.697       | −4.1%                |
| Misaligned only   | 1,048,576 | 4      | 0.123750       | 16.947       | −8.2%                |
| Misaligned + tail | 1,050,000 | 4      | 0.125375       | 16.750       | −9.3%                |

| Case              | N       | misalign | SIMD Time (ms) | SIMD GFLOP/s | Δ vs aligned,no-tail |
|-------------------|---------|----------|----------------|--------------|----------------------|
| Aligned, no tail  | 1,048,576 | 0      | 0.224208       | 9.354        | —                    |
| Tail only         | 1,050,000 | 0      | 0.228208       | 9.202        | −1.6%                |
| Misaligned only   | 1,048,576 | 4      | 0.243875       | 8.599        | −8.1%                |
| Misaligned + tail | 1,050,000 | 4      | 0.247625       | 8.481        | −9.3%                |

- The two tables shown above demonstrate the effects of aligned/misaligned/tail/no tail for the SAXPY kernel. According to the tables, misalignment produced the largest penalty (≈8–9% lower GFLOP/s in both f32 and f64), consistent with extra cycles/split cache-line accesses for unaligned loads. A non-multiple-of-vector-width size introduced a small tail overhead (≈1–4%), due to masked vector instructions or a scalar epilogue. The worst case (misaligned + tail) compounded to ≈9% loss. Overall, alignment dominates the throughput gap, while tail handling is a smaller fixed cost that diminishes with larger N.
### Why Alignment & Tails Impact Performance

- **Prologue (alignment peel).**  
  If the input pointer isn’t suitably aligned for the chosen vector width, the compiler emits a few scalar iterations to reach an aligned address. That prologue is overhead that doesn’t scale with *N* and shows up more at small/medium sizes.

- **Unaligned loads/stores.**  
  Even on architectures that support unaligned accesses, crossing cache-line boundaries can require **two memory transactions** instead of one, and the hardware may insert extra cycles for address alignment fixes.  
  **Net effect:** lower effective bandwidth → ~8–9% drop in your data.

- **Epilogue (tail).**  
  When N Mod Vector_width != 0,
  The compiler handles the remainder via masked vector ops or scalar epilogue. Either way, it’s a small fixed cost; hence a ~1–4% drop, which gets smaller as *N* grows.

### 3.4 Stride / gather effects
| Stride | Time (ms) | GFLOP/s | Effective GiB/s |
|-------:|----------:|--------:|----------------:|
| 1      | 2.7758    | 6.0442  | 67.55           |
| 2      | 7.5295    | 2.2282  | 24.90           |
| 4      | 16.5299   | 1.0150  | 11.34           |
| 8      | 601.9534  | 0.0279  | 0.31            |

<img width="1282" height="780" alt="image" src="https://github.com/user-attachments/assets/c4c620d9-2512-4669-b780-45315013d51f" />

- In experimenting with the effects of stride and gather-like patterns, a fixed N=16,777,216 was used on a mul f32 kernel. The stride was then varied from 1, 2, 4, and 8, as shown in the table above. In calculating bandwidth and SIMD efficiency, the effective GiB/s was computed using (3×N×4 bytes)​÷(time*2^30). 
- Using both the graph and the table, we could identify that unit-stride hits ~67.5 GiB/s and ~6.0 GFLOP/s, which is close to the sustained streaming bandwidth on this machine for this kernel. We then approach a moderate stride where the bandwidth drops to 24.9 GiB/s and 11.34 respectively. This stage indicates that the SIMD lanes are underfed. Finally, we approach a large stride of 8, where the effective GiB/s drops significantly to 0.31 GiB/s. This stage indicates that SIMD is basically idle, with latency dominated.
- During this experimentation, we could visualize the limits of the prefetcher and the cache line. Prefetchers are tuned for gentle and contiguous strides, so as the strides increase, the prefetchers fail to predict future addresses and stop pulling data early. The core would experience more miss latency and fewer hits in private caches. For cache-line utilization, every 64-B line provides 16 f32 values you actually use during unit stride. With stride=4 or 8, you fetch whole lines but only touch 1 out of every 4 or 8 elements, meaning most of each line is wasted bandwidth.

### 3.5 Data type comparison

### f32
<p float="left">
  <img src="https://github.com/user-attachments/assets/8abf7d46-3a7c-45a9-bb27-485ee9ec88b0" width="400"/>
  <img src="https://github.com/user-attachments/assets/5b7d7977-6592-4e7c-9f28-67436296bdb1" width="400"/>
  <img src="https://github.com/user-attachments/assets/d9b11d42-ba33-459e-b5bd-9ad4047111c1" width="400"/>
  <img src="https://github.com/user-attachments/assets/bec96b43-a224-4096-9e28-9a5573908a3b" width="400"/>
</p>

- **Speedup vs N**

<p float="left">
  <img src="https://github.com/user-attachments/assets/885401c9-39c5-4ea2-9efc-cd9b565f1e1a" width="400"/>
  <img src="https://github.com/user-attachments/assets/d5b913a9-29d8-4666-b35d-1208b2981ffe" width="400"/>
</p>

- Shown above are the scalar, SIMD, and speedup graphs for the multiplication kernel in f32 and f64. Modern SIMD units operate on a fixed register width. This translates into twice as many lanes for f32 compared to f64. As a result, the theoretical compute-bound speedup for f32 is roughly 2× higher than f64 on the same ISA. This effect is visible at small input sizes where the working set fits into cache: f32 achieves peak speedups of ~4–5×, while f64 never exceeds ~1.3×.

## Arithmetic intensity  
Elementwise multiplication is a memory-bound kernel since each operation requires two loads and one store, but only performs a single floating-point multiply. The arithmetic intensity (AI) can be estimated as:  

- AI_{f32} = 1/(3*4B) = 0.083 flops/byte
- AI_{f64} = 1/(3*8B) = 0.042 flops/byte

Because f32 has twice the AI of f64, its attainable GFLOP/s ceiling under a fixed memory bandwidth is approximately 2× higher.  

## Observed scaling  
For small \(N\), f32 speedup approaches the vector-lane advantage, demonstrating a compute-bound regime where SIMD width matters. As \(N\) grows, both kernels transition into the bandwidth-bound regime, and speedup collapses toward ~1×. This effect is more severe for f64 because its lower AI means it saturates memory bandwidth at a lower flop rate. In other words, f64 gains little from SIMD because the memory system becomes the bottleneck almost immediately.  

### 3.6 Vectorization verification
- **Auto‑vectorized (SIMD) build**:  
  ```bash
  clang++ -std=c++17 -O3 -march=native -Rpass=loop-vectorize src/bench.cpp -o bench_simd
  ```
  - Evidence from compile output (examples):  
    ```text
    src/kernels.hpp:25:5: remark: vectorized loop (vectorization width: 4, interleaved count: 4)
    src/kernels.hpp:60:5: remark: vectorized loop (vectorization width: 2, interleaved count: 4)
    ```
  - The compiler confirmed auto-vectorization of the kernels.


## 7) Locality (Working‑Set) Sweep
Pick one kernel (e.g., SAXPY f64). Compute **CPE** and **GFLOP/s** while sweeping N across caches.

- **CPE** = cycles / element (use `cpu_frequency × time / N`, or hardware counters if available).  
- Annotate L1/L2/LLC/DRAM transitions on the plot (based on §2 cache sizes).  
- Discuss where SIMD gains **compress** as DRAM limits bandwidth.

**Insert**: GFLOP/s (or GiB/s) and CPE plots with vertical lines at cache thresholds.

---

## 8) Vectorization Verification
Provide succinct evidence (not full dumps).

**Compiler report snippets**
```text
src/kernels.hpp:25:5: remark: vectorized loop (vectorization width: 4, interleaved count: 4)
src/kernels.hpp:60:5: remark: vectorized loop (vectorization width: 2, interleaved count: 4)
```
**(Optional) Disassembly**: show one vector op for one kernel.

---

## 9) Roofline Interpretation
For at least one kernel:
1. **Arithmetic intensity (AI)** = FLOPs / bytes moved.  
   - Example (SAXPY): FLOPs/elem = 2, bytes/elem ≈ 24 (R A + R Y + W Y with write‑allocate) → **AI ≈ 0.083 FLOP/byte**.
2. **Measured bandwidth** from large‑N runs: GiB/s = bytes_moved / time.  
3. **Predicted peak GFLOP/s** (memory‑bound) ≈ AI × bandwidth.  
4. **Compare** predicted vs achieved GFLOP/s; state whether compute‑ or memory‑bound.  
5. Briefly relate vector width (lanes) and AVX/FMA behavior to observed speedup.

**Template**
| Kernel | Precision | AI (F/B) | Meas. BW (GiB/s) | Pred. Roof (GF/s) | Achieved (GF/s) | Bound? |
|---|---|---:|---:|---:|---:|---|
| saxpy | f64 | 0.083 | [[ ]] | [[AI×BW]] | [[ ]] | memory |
| mul   | f32 | [[ ]] | [[ ]] | [[ ]] | [[ ]] | compute/mixed |

---

## 10) Conclusion
- SIMD provides substantial gains in compute‑bound phases; gains compress in bandwidth‑bound regimes.  
- Data type (lane width) and locality dominate observed performance.  
- Verified auto‑vectorization confirms true SIMD usage.  
- Roofline model accurately predicts plateaus and clarifies where optimization should target (e.g., improving locality vs math throughput).

---

## Appendix
- Full CSVs (scalar/SIMD).  
- Exact compile commands and environment.  
- Extra plots (alignment, stride, tails).

---

### Drop‑in image placeholders
Embed your PNGs like:
```markdown
![SAXPY f64 GFLOP/s](figs/saxpy_f64_gflops.png)
![SAXPY f64 Speedup](figs/saxpy_f64_speedup.png)
```
