
# SIMD Advantage Profiling — Project Report (ECSE 4320/6320)

> **Author:** Yuming Tseng  
> **Machine:** Apple silicon (Apple M2 series) on macOS  
> **Repo:** simd-profiling (bench + kernels in `src/`)

---

## 1) Introduction
Modern CPUs expose SIMD (Single Instruction, Multiple Data) units that act on vectors of data per instruction. This project measures the advantage of SIMD vs a scalar baseline across multiple kernels and data sizes, and explains when and why vectorization helps or doesn’t, with evidence from compiler reports and a roofline interpretation.

---

## 2) Experimental Setup

### Hardware & Software
- **CPU:** Apple M1
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
- Warm‑up run (not timed) + **k=3 trials**, report **median**.  
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
- Shown below are 3 tables and the corresponding average speed-up graphs (Sample size=3 trials) documenting scalar and auto-vectorized versions for the three chosen kernels.
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

<img width="447" height="314" alt="Screenshot 2025-09-24 at 9 32 41 PM" src="https://github.com/user-attachments/assets/16a4ca2e-27dd-4248-a94f-7e507c6ef203" />


| Kernel | N       | Scalar Time (ms) | SIMD Time (ms) | Scalar GFLOP/s | SIMD GFLOP/s | Speedup |
|--------|---------|------------------|----------------|----------------|--------------|---------|
| saxpy  | 16384   | 0.015500         | 0.005125       | 2.11           | 6.39         | 3.02×   |
| saxpy  | 65536   | 0.062000         | 0.019750       | 2.11           | 6.64         | 3.14×   |
| saxpy  | 262144  | 0.157458         | 0.033166       | 3.33           | 15.81        | 4.75×   |
| saxpy  | 1048576 | 0.489083         | 0.128084       | 4.29           | 16.37        | 3.82×   |
| saxpy  | 4194304 | 1.541458         | 0.707791       | 5.44           | 11.85        | 2.18×   |
| saxpy  | 16777216| 5.531084         | 2.659334       | 6.07           | 12.62        | 2.08×   |
| saxpy  | 67108864| 23.746708        | 10.771334      | 5.65           | 12.46        | 2.20×   |

<img width="467" height="318" alt="Screenshot 2025-09-24 at 9 44 42 PM" src="https://github.com/user-attachments/assets/aa7e085a-1abb-4424-80c4-a58e5d5bbaf3" />


| Kernel   | N       | Scalar Time (ms) | SIMD Time (ms) | Scalar GFLOP/s | SIMD GFLOP/s | Speedup |
|----------|---------|------------------|----------------|----------------|--------------|---------|
| stencil3 | 16384   | 0.005917         | 0.001625       | 13.84          | 50.41        | 3.64×   |
| stencil3 | 65536   | 0.024709         | 0.006625       | 13.26          | 49.46        | 3.73×   |
| stencil3 | 262144  | 0.093625         | 0.025792       | 14.00          | 50.82        | 3.63×   |
| stencil3 | 1048576 | 0.388625         | 0.104250       | 13.49          | 50.29        | 3.73×   |
| stencil3 | 4194304 | 1.574458         | 0.428709       | 13.32          | 48.92        | 3.67×   |
| stencil3 | 16777216| 6.328125         | 1.773166       | 13.26          | 47.31        | 3.57×   |
| stencil3 | 67108864| 25.389333        | 7.156125       | 13.22          | 46.89        | 3.55×   |
<img width="474" height="315" alt="Screenshot 2025-09-24 at 9 40 56 PM" src="https://github.com/user-attachments/assets/1edd25c7-55b2-44a5-9fd7-f9075fba1daa" />

### 3.2 Locality Sweep

<img width="575" height="459" alt="Screenshot 2025-09-24 at 12 04 28 PM" src="https://github.com/user-attachments/assets/4da199e9-51b0-4fb2-8711-5e5dfb85b292" />


- For the chosen kernel of saxpy f32, cache levels were swept through by varying the number of elements N. Shown on the graph below, we could identify that L1 was the first region, where throughput is flat and SIMD GFLOP/s grows as arithmetic dominates. Then we reach L2/LLC (on M2 chip, LLC is shared with L2) in the middle region, where SIMD experiences peak performance, reaching around 17GFLOP/S. Finally, beyond N=10^6, throughput drops to ~12–13 GFLOP/s and flattens, because memory bandwidth is now the bottleneck.

- SIMD compression: In this graph, SIMD gains compress to ~2×, because the bottleneck is memory bandwidth, meaning the vector units cannot operate faster than data can be streamed from DRAM. This is the expected behavior for a streaming, low-arithmetic-intensity kernel like SAXPY.
- Using the same data, CPE was also calculated by multiplying the runtime by CPU frequency (assumed as 3Ghz) and dividing by N. This is shown in the table below.

| N        | Scalar Time (ms) | SIMD Time (ms) | Scalar GFLOP/s | SIMD GFLOP/s | Speedup | Scalar CPE | SIMD CPE |
|----------|------------------|----------------|----------------|--------------|---------|------------|----------|
| 16,384   | 0.015500         | 0.005125       | 2.11           | 6.39         | 3.02×   | 2.84       | 0.94     |
| 65,536   | 0.062000         | 0.019750       | 2.11           | 6.64         | 3.14×   | 2.84       | 0.90     |
| 262,144  | 0.157458         | 0.033166       | 3.33           | 15.81        | 4.75×   | 1.80       | 0.38     |
| 1,048,576| 0.489083         | 0.128084       | 4.29           | 16.37        | 3.82×   | 1.40       | 0.37     |
| 4,194,304| 1.541458         | 0.707791       | 5.44           | 11.85        | 2.18×   | 1.10       | 0.51     |
| 16,777,216| 5.531084        | 2.659334       | 6.07           | 12.62        | 2.08×   | 0.99       | 0.48     |
| 67,108,864| 23.746708       | 10.771334      | 5.65           | 12.46        | 2.20×   | 1.06       | 0.48     |

### Observations
- **Scalar CPE** starts around **2.8 cycles/element** for small \(N\), and trends toward **~1 cycle/element** for large \(N\).  
- **SIMD CPE** is consistently **<1 cycle/element** (best around **0.37**), showing highly efficient throughput close to one element per cycle.  
- At large \(N\), the CPE values converge, indicating the kernel becomes **memory-bound** and SIMD speedup is limited by bandwidth rather than compute.  



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
- Interpretation: The compiler vectorized the `mul` and `saxpy` loops with a vector width of 4 for `f32` (corresponding to 128-bit SSE registers) and width of 2 for `f64` (since doubles take twice the space). The “interleaved count: 4” indicates loop unrolling to increase ILP (instruction-level parallelism). On x86-64 with AVX/AVX2, this matches the expected SIMD width: 4×32-bit floats or 2×64-bit doubles per vector register. The measured speedups (≈2–4×) are consistent with this hardware vector width, confirming SIMD execution.


### 3.7 Roofline Interpretation
- Using the Mul kernel, we determined that per element, there is 1 FLOP, and 3 bytes moved from loading a and b, plus a store.
- Therefore the arithmetic intensity:
- f32 = 1/(3*4) = 0.0833 flop/byte
- f64 = 1/(3*8) = 0.0417 flop/byte

- **Roofline Placement**
- Troof = min(Pmax, B * AI)
  - Where Pmax = peak FLOP rate for the precision used
  - B = measured sustained memory bandwidth (GB/s)
 
  - From Project 2, we determined that the bandwidth was B = 50GB/s and the CPU peaked at Pmax(32) = 800 GFLOPS/s and Pmax(64) = 400 GFLOPS/s. From this, we calculated the bandwidth of the kernel, deriving:
  - f32 roof = 50 * 0.0833 = 4.17 GFLOP/s
  - f64 roof = 50 * 0.0417 = 2.08 GFLOP/s
 
  - Since the calculated roofline values are much smaller than the Pmax values for f32 and f64, we can conclude that large-N performance is memory-bound and capped near those values.
- **Roofline conclusion**
- At small 𝑁, the kernels can be compute-bound and benefit from the greater f32 lane count, yielding large SIMD speedups.
At large N, both kernels become memory-bound at 𝐵×𝐴𝐼. SIMD width has little effect, and f32’s advantage reduces to its ~2× higher arithmetic intensity ceiling.

## 10) Conclusion
- SIMD provides substantial gains in compute‑bound phases; gains compress in bandwidth‑bound regimes.  
- Data type (lane width) and locality dominate observed performance.  
- Verified auto‑vectorization confirms true SIMD usage.  
- Roofline model accurately predicts plateaus and clarifies where optimization should target.

---

## Appendix

# Trial 1 Results
## Multiplication (mul)
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/4f8d6897-1a52-4ae8-b9bf-cc9ae04dad9d" /> | <img width="350" src="https://github.com/user-attachments/assets/d53fc502-adac-4e28-a4d4-8613a81ec740" /> | <img width="350" src="https://github.com/user-attachments/assets/d0b5e18d-4b04-4ca8-8454-0d7e7fa526e3" /> | <img width="350" src="https://github.com/user-attachments/assets/e1910290-1d44-4a86-a49a-bc67bc1be531" /> |

---
## SAXPY
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/f071618b-1da0-43e0-bfcf-de28bbb433d2" /> | <img width="350" src="https://github.com/user-attachments/assets/5abcc98c-98f7-4c82-8820-ec7f339aaa42" /> | <img width="350" src="https://github.com/user-attachments/assets/39fe2698-5226-48fc-8a75-b6f9aa4be852" /> | <img width="350" src="https://github.com/user-attachments/assets/922e088f-b96d-492c-9f5c-5bc9d670a82c" /> |

---
## Stencil3
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/f1552553-3614-4a8a-aaaa-b42be4af40e7" /> | <img width="350" src="https://github.com/user-attachments/assets/6df04bab-a315-4ed4-b572-e8a2424e5e63" /> | <img width="350" src="https://github.com/user-attachments/assets/c392a98e-76ac-43fb-a044-efa4fb7fd8ae" /> | <img width="350" src="https://github.com/user-attachments/assets/47abe00d-1957-4f01-8479-130c49a3824d" /> |

---
## Speedup Plots
| mul f32 | mul f64 | saxpy f32 | saxpy f64 | stencil3 f32 | stencil3 f64 |
|---------|---------|-----------|-----------|--------------|--------------|
| <img width="300" src="https://github.com/user-attachments/assets/4f8d6897-1a52-4ae8-b9bf-cc9ae04dad9d" /> | <img width="300" src="https://github.com/user-attachments/assets/a8fd2296-8f40-41c0-b215-425c83aee83f" /> | <img width="300" src="https://github.com/user-attachments/assets/36ac9a2e-4dd3-42d4-944e-beabb81ccd91" /> | <img width="300" src="https://github.com/user-attachments/assets/5ece1bf4-5609-4c97-8ccd-f8a6459bd0a0" /> | <img width="300" src="https://github.com/user-attachments/assets/0f070ea8-c1e5-4d16-ad6d-fae37e110929" /> | <img width="300" src="https://github.com/user-attachments/assets/de03adc2-cb31-4c93-a270-e673b7a9f3ec" /> |

# Trial 2 Results

## Multiplication (mul)
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/e4a77c66-c13f-473c-b267-7c353a397c9b" /> | <img width="350" src="https://github.com/user-attachments/assets/95db02e1-0434-47fa-abd3-0d59d83ce25b" /> | <img width="350" src="https://github.com/user-attachments/assets/b225040b-7beb-40bf-990f-5f879c0b4e3d" /> | <img width="350" src="https://github.com/user-attachments/assets/70c17809-5dde-4802-88a6-e84f43fe0db1" /> |

---
## SAXPY
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/0bc3ab37-e550-475c-b450-7cfaf1121c70" /> | <img width="350" src="https://github.com/user-attachments/assets/ab9bc511-4103-4b22-9854-796e6a13cbaf" /> | <img width="350" src="https://github.com/user-attachments/assets/4a9013b5-5de2-4b7c-99c4-cca55d88535a" /> | <img width="350" src="https://github.com/user-attachments/assets/473cb1da-b79c-42dd-8591-497096457fa2" /> |

---
## Stencil3
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/36c96c9d-cac3-4cb2-bfe5-0b7a93122691" /> | <img width="350" src="https://github.com/user-attachments/assets/391d0c39-5cd8-4828-a588-2988ac3c5c50" /> | <img width="350" src="https://github.com/user-attachments/assets/74310386-739a-487b-a8b0-f0d6651802e6" /> | <img width="350" src="https://github.com/user-attachments/assets/e118c1ca-eb1d-4e13-840e-ed2975b67eaf" /> |

---
## Speedup Plots
| mul f32 | mul f64 | saxpy f32 | saxpy f64 | stencil3 f32 | stencil3 f64 |
|---------|---------|-----------|-----------|--------------|--------------|
| <img width="300" src="https://github.com/user-attachments/assets/3bf58671-9817-444f-8d80-b2d63ba26eb3" /> | <img width="300" src="https://github.com/user-attachments/assets/e3773bb9-e3e0-42c6-b29b-385d24e2a225" /> | <img width="300" src="https://github.com/user-attachments/assets/94da9eb9-be3a-42be-92b8-2bfea1e9ef8e" /> | <img width="300" src="https://github.com/user-attachments/assets/860fe171-e52e-4d87-a73a-5a55d8149e17" /> | <img width="300" src="https://github.com/user-attachments/assets/8de11b76-37b1-463b-807e-b7e5d891c90e" /> | <img width="300" src="https://github.com/user-attachments/assets/e0c4aca9-72eb-4e4e-8a41-9fb295d72af1" /> |

# Trial 3 Results

## Multiplication (mul)
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/6e4a2fa8-c030-4a99-8b05-9d95e2d0ccaa" /> | <img width="350" src="https://github.com/user-attachments/assets/09727a36-32d1-4036-8a01-81881b6964e4" /> | <img width="350" src="https://github.com/user-attachments/assets/f74fd907-3ca0-4e1b-9736-f3deaadd3852" /> | <img width="350" src="https://github.com/user-attachments/assets/985a56d2-4f73-4951-91e7-4d61a506e3f1" /> |

---
## SAXPY
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/35c18ef9-b15c-4df4-a8d6-619ee51bbf18" /> | <img width="350" src="https://github.com/user-attachments/assets/eb639ba8-a417-43a8-8a09-31112203d7c3" /> | <img width="350" src="https://github.com/user-attachments/assets/217c7538-5bfa-41cb-8136-114dac75df47" /> | <img width="350" src="https://github.com/user-attachments/assets/953a9613-be25-426d-954b-0139161e866e" /> |

---
## Stencil3
| f32 Scalar | f32 SIMD | f64 Scalar | f64 SIMD |
|------------|----------|------------|----------|
| <img width="350" src="https://github.com/user-attachments/assets/b58c8354-76de-409c-9012-f6767a32ac8c" /> | <img width="350" src="https://github.com/user-attachments/assets/ba35a6fd-b7be-42b4-8fdd-4055546e9629" /> | <img width="350" src="https://github.com/user-attachments/assets/accba571-a07a-4698-9d99-26507a83f6b8" /> | <img width="350" src="https://github.com/user-attachments/assets/24f44be5-21a8-4b3a-87a1-b50f428a18b8" /> |

---
## Speedup Plots
| mul f32 | mul f64 | saxpy f32 | saxpy f64 | stencil3 f32 | stencil3 f64 |
|---------|---------|-----------|-----------|--------------|--------------|
| <img width="300" src="https://github.com/user-attachments/assets/663b5aee-e1a3-4edb-8c68-9c627446c3f1" /> | <img width="300" src="https://github.com/user-attachments/assets/66394dee-2e0b-447b-828b-0f7bfa6f5384" /> | <img width="300" src="https://github.com/user-attachments/assets/da39a771-dccb-4558-ab31-e947a4323ec1" /> | <img width="300" src="https://github.com/user-attachments/assets/9926851f-0907-45d5-87e2-b6ef91f8dcec" /> | <img width="300" src="https://github.com/user-attachments/assets/a4d99c71-9ef7-4d27-8899-719821304853" /> | <img width="300" src="https://github.com/user-attachments/assets/89f1dbc3-baa8-49c6-b941-bf020e18c441" /> |

