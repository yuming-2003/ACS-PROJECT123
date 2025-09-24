
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
- **Memory bandwidth (sustained):** ___ GB/s (from vendor or microbench)  
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

### 3.1 SAXPY
- **GFLOP/s vs N** (scalar & SIMD, f32 & f64)

### f32
<p float="left">
  <img src="https://github.com/user-attachments/assets/ede816fe-3a64-4258-ac46-231769f151da" width="400"/>
  <img src="https://github.com/user-attachments/assets/0374ba9a-bbfe-4e97-8b05-679b4c08e9ba" width="400"/>
</p>

- **Speedup vs N**

<p float="left">
  <img src="https://github.com/user-attachments/assets/618bde94-27ae-4e95-af7f-9b9c35f865e0" width="400"/>
</p>

### f64
<p float="left">
  <img src="https://github.com/user-attachments/assets/9f44b960-5c47-400f-af43-bbe62f0429c1" width="400"/>
  <img src="https://github.com/user-attachments/assets/35eae745-d5e1-4b38-9488-9ee481bc414d" width="400"/>
</p>

- **Speedup vs N**

<p float="left">

  <img src="https://github.com/user-attachments/assets/b8cbf2d7-7015-4d61-8254-257a4d974107" width="400"/>
</p>

**Summary table**
| Precision | Peak GFLOP/s (Scalar) | Peak GFLOP/s (SIMD) | Peak Speedup | DRAM GFLOP/s (Scalar) | DRAM GFLOP/s (SIMD) | DRAM Speedup |
|---|---:|---:|---:|---:|---:|---:|
| f32 | [[ ]] | [[ ]] | [[ ]] | [[ ]] | [[ ]] | [[ ]] |
| f64 | [[ ]] | [[ ]] | [[ ]] | [[ ]] | [[ ]] | [[ ]] |

**Notes:** cache transition near `N ≈ _____` (derived from cache sizes in §2).

### 3.2 Stencil
- **GFLOP/s vs N** — *insert*  
- **Speedup vs N** — *insert*

**Summary table**
| Precision | Peak GFLOP/s (Scalar) | Peak GFLOP/s (SIMD) | Peak Speedup | DRAM Speedup |
|---|---:|---:|---:|---:|
| f32 | [[ ]] | [[ ]] | [[ ]] | [[ ]] |
| f64 | [[ ]] | [[ ]] | [[ ]] | [[ ]] |

### 3.3 Mul
- **GFLOP/s vs N** — *insert*  
- **Speedup vs N** — *insert*

**Summary table**
| Precision | Peak GFLOP/s (Scalar) | Peak GFLOP/s (SIMD) | Peak Speedup | DRAM Speedup |
|---|---:|---:|---:|---:|
| f32 | [[ ]] | [[ ]] | [[ ]] | [[ ]] |
| f64 | [[ ]] | [[ ]] | [[ ]] | [[ ]] |

---

## 4) Alignment & Tail Handling
We compared aligned vs misaligned buffers and sizes with/without a vector tail.

**Build/Run knobs**
- Alignment bytes: `--align 32/64` vs `--misalign` (if supported by harness)
- Tail handling: full masked vector tail vs scalar epilogue

**Report**
- Throughput delta (GFLOP/s or GiB/s) for aligned vs misaligned.  
- Explain impact: prologue/epilogue cost, unaligned loads, masking overhead.

**Template table**
| Kernel | Precision | Align | Tail Mode | Peak GFLOP/s | Δ vs aligned (%) |
|---|---|---|---|---:|---:|
| saxpy | f32 | aligned | masked tail | [[ ]] | baseline |
| saxpy | f32 | misaligned | masked tail | [[ ]] | [[-xx%]] |
| saxpy | f32 | aligned | scalar tail | [[ ]] | [[-x%]] |
| ... | ... | ... | ... | ... | ... |

---

## 5) Stride / Gather Effects
Evaluate unit‑stride vs strided/gather‑like access (where meaningful for each kernel).

**What to show**
- Effective bandwidth drop with stride>1.  
- Prefetcher limits and cache‑line utilization.

**Template table**
| Kernel | Precision | Stride | GFLOP/s (Scalar) | GFLOP/s (SIMD) | Speedup | Comment |
|---|---|---:|---:|---:|---:|---|
| stencil | f64 | 1 | [[ ]] | [[ ]] | [[ ]] | baseline |
| stencil | f64 | 2 | [[ ]] | [[ ]] | [[ ]] | half line use |
| stencil | f64 | 4 | [[ ]] | [[ ]] | [[ ]] | poor prefetch |
| ... | ... | ... | ... | ... | ... | ... |

---

## 6) Data Type Comparison
Compare f32 vs f64 (optionally i32). Discuss lane width impact and arithmetic intensity.

**Template table**
| Kernel | Metric | f32 (scalar) | f32 (SIMD) | f64 (scalar) | f64 (SIMD) |
|---|---|---:|---:|---:|---:|
| saxpy | Peak GFLOP/s | [[ ]] | [[ ]] | [[ ]] | [[ ]] |
| saxpy | DRAM GFLOP/s | [[ ]] | [[ ]] | [[ ]] | [[ ]] |
| mul   | Peak GFLOP/s | [[ ]] | [[ ]] | [[ ]] | [[ ]] |

---

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
