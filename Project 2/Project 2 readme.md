
# Cache& Memory Performance Profiling — Project Report (ECSE 4320/6320)

> **Author:** Yuming Tseng  
> **Machine:** AMD Ryzen 7 5800X 8 core processor

---

## 1) Introduction
Modern CPUs have a deep memory hierarchy (L1/L2/L3 caches + DRAM). Each level differs by orders of magnitude
in latency and bandwidth. Like storage, memory shows a throughput–latency trade-off: as concurrency
(outstanding memory requests) rises, bandwidth approaches a limit while average latency increases due to
queuing.

## 2) Experimental Setup
The project used a lightweight SAXPY kernel to systematically evaluate memory system behavior under controlled conditions. Experiments were organized into six parts: (1) zero-queue baselines to measure raw memory latency, (2) working-set size sweeps to expose cache capacity boundaries, (3) stride sweeps to study spatial locality and prefetching, (4) intensity sweeps to evaluate throughput vs latency and identify the “knee” of performance, (5) pattern & granularity sweeps to compare sequential, strided, and random access behaviors, and (6) cache- and TLB-miss impacts, where working set size, stride, and page locality were varied to correlate runtime with hierarchical penalties. Ubuntu/WSL2 was chosen as the environment because it provides GCC, mmap, and other POSIX system calls for fine-grained memory control, and supports Linux-native tools like perf (even though WSL2 limits hardware counters). These capabilities made Ubuntu the most practical platform for controlled, repeatable low-level memory experiments.

## 3) Results

### 3.1 Zero-queue baselines
- Method: To measure raw memory hierarchy performance, a zero-queue baseline methodology was utilized. In this mode, only a single thread issues unit-stride, read-only requests (threads=1, stride=1, read%=100). This ensures there is at most one outstanding access, avoiding overlap from hardware prefetching or memory-level parallelism. Since Intel MLC is not supported on AMD CPUs, a custom benchmark (microbench) was implemented to reproduce the same access patterns. This allowed measurements for bandwidth and latency trends for working-set size, stride, read/write ratio, and concurrency. While WSL2 obscured cache-level transitions, the results still illustrate the principles behind MLC experiments.
- The experiment began by utilizing the microbench framework to run streaming bandwidth sweeps across working-set sizes. This revealed where working sets fit in cache versus spill into DRAM.

### Zero-Queue Baselines (Ryzen 7 5800X @ 3.8 GHz)
*(threads=1, stride=1, read%=100; mean± )*

| Working-set size | Mean Time (s) | Mean BW (GiB/s) | Std BW | BW (B/s)     | Cycles/byte @ 3.8 GHz | Cycles/64 B @ 3.8 GHz |
|---:|---:|---:|---:|---:|---:|---:|
| 32 KB  | 0.0002663 | 0.5747 | 0.0358 | 6.17 × 10^8 | 6.16 | 394.1 |
| 256 KB | 0.0018443 | 0.6623 | 0.0186 | 7.11 × 10^8 | 5.34 | 342.0 |
| 2 MB   | 0.0148443 | 0.6583 | 0.0150 | 7.07 × 10^8 | 5.38 | 344.0 |
| 32 MB  | 0.2381927 | 0.6563 | 0.0045 | 7.05 × 10^8 | 5.39 | 345.1 |
| 64 MB  | 0.4837873 | 0.6460 | 0.0027 | 6.94 × 10^8 | 5.48 | 350.6 |
| 256 MB | 1.9243892 | 0.6495 | 0.0046 | 6.97 × 10^8 | 5.45 | 348.7 |
| 512 MB | 3.8720153 | 0.6457 | 0.0111 | 6.93 × 10^8 | 5.48 | 350.8 |

- The table above shows that bandwidth stabilizes at ~0.65 GiB/s for working sets beyond a few MB, indicating sustained DRAM throughput. Cache-resident regions (32–256 KB) are slightly more efficient. The flat profile confirms a proper zero-queue condition where there are no overlaps or queueing effects.

- To measure per-level latencies, I used a modern MSYS2 + g++ compiler. Using this, I was able to implement a dependent pointer-chase microbenchmark: each load depends on the value of the previous load, which defeats prefetching and guarantees only one miss in flight. By varying working-set size, I targeted L1, L2, L3, and DRAM. The table below shows the per-level latencies.
  
| Level | Working-set size | Cycles / load | Latency (ns)  | Notes |
|-------|------------------|---------------|--------------|-------|
| L1    | 16 KB            | 3.94          | 1.04 ns      | Fits in 32 KB L1D |
| L2    | 256 KB           | 9.55          | 2.51 ns      | Fits in 512 KB L2 |
| L3    | 16 MB            | 133.9         | 35.2 ns      | Within 32 MB shared LLC |
| DRAM  | 256 MB           | 453.9         | 119.5 ns     | ≫ LLC, true DRAM latency |

### 3.2 Pattern & Granularity sweep

- The pattern–stride sweep shows how access type and stride size affect memory hierarchy performance. The three graphs below plot both latency and bandwidth of sequential reading, writing, and rmw

### Sequential Reads
At small strides (4–64 B), bandwidth was highest and latency lowest, since the hardware prefetcher efficiently streamed cache lines. Beyond one cache line (≥ 64 B), spatial locality was lost and prefetch fell off. Bandwidth dropped sharply and latency rose, flattening near DRAM access time at 4 KiB strides.
<img width="1580" height="980" alt="image" src="https://github.com/user-attachments/assets/62e91569-11af-4521-8f0f-ea823e9fcd59" />
## Sequential Writes
Writes consistently underperformed reads due to **Read-For-Ownership (RFO)**: each store requires a read + writeback. This doubled traffic and reduced effective GiB/s, especially once strides exceeded the line size.
<img width="1580" height="980" alt="image" src="https://github.com/user-attachments/assets/1f7e843c-983b-4224-8b07-265be08df877" />

## Read-Modify-Write (RMW)
RMW showed the poorest bandwidth. Each access triggers both read and write operations, compounding RFO overhead. Latency was slightly higher than write-only, consistent with doubled transactions.
<img width="1580" height="980" alt="image" src="https://github.com/user-attachments/assets/a8f2bc3a-a34f-4e40-be47-9367f4cc0aac" />

## This experiment demonstrated that:
- Prefetcher is effective at small strides, ineffective once stride ≥ line size.  
- Stride growth reduces spatial locality → lower bandwidth, higher latency. 




### 3.3 Read/Write mix sweep
- The graph below demonstrates the implementations of the four read and write ratios (100%R, 100%W, 70/30, 50/50). The read/write results show that bandwidth is highest at the extremes: ~0.64 GiB/s for 100% reads and 100% writes. As writes transition from 100% reads toward 50/50, bandwidth drops significantly to ~0.44 GiB/s. This is due to the higher cost of handling stores compared to loads, where writes trigger Read-For-Ownership (RFO) requests, generate coherence traffic, and are not as effectively prefetched as reads. At 70/30, performance partially recovers (~0.50 GiB/s) because reads dominate again. These results align with expectations, having 100% reads maximize prefetch efficiency, 100% writes benefit from store buffers and write-combining, but mixed ratios suffer from pipeline and coherence contention. Each experiment was conducted 3 times, with error bars plotted. Overall, the results were similar and had negligible differences.
<img width="640" height="480" alt="rw_mix" src="https://github.com/user-attachments/assets/3f1c26b2-213e-4d0a-8fc1-3d7654e17604" />
- The latency plots for the four read/write ratios are displayed below. Latency is lowest at the extremes, ~0.48–0.49 µs for 100% reads and 100% writes, and increases when reads and writes are mixed. The worst case occurs at 50/50 (0.72 µs), with 70/30 falling in between (0.62 µs). This reflects the same findings from the bandwidth graph.
<img width="1039" height="642" alt="image" src="https://github.com/user-attachments/assets/48685425-f5fe-4c2d-bb3f-c193e188f733" />

### 3.4 Intensity sweep
- The curve shows nearly linear scaling, doubling threads almost doubles throughput, while latency per run falls proportionally. Error bars are tiny (≤0.02 GiB/s), so a 10x multiplier was used to visualize them. By using only 8 threads, the graph wasn't able to clearly see the "knee" of the graph. 
<img width="957" height="649" alt="image" src="https://github.com/user-attachments/assets/907d6cca-ecc5-4cb0-a67d-46432f708bb9" />
- In resolving this issue, I varied request intensity by sweeping threads = {1,2,4,8,12,16} at fixed access pattern (64 MiB working-set, unit stride, 1000 repeats, 100% reads) as shown below.
<img width="1040" height="729" alt="image" src="https://github.com/user-attachments/assets/8d0d167e-0d90-45cf-b3e9-c649b60a1762" />

- Scaling region (1→8 threads). Throughput ≈ doubles when threads double, while latency halves—near-linear scaling.
- Transition (8→12). Throughput gain drops from +2.30 GiB/s (4→8) to +2.12 GiB/s (8→12) and latency improvements shrink (−11.80 s → −3.95 s). We are nearing saturation.
- Over-subscription (12→16). Adding threads reduces throughput (6.95 → 5.93 GiB/s) and increases latency (8.99 → 10.55 s). That is contention/queuing behavior beyond the service capacity. Hence, the knee could be identified at thread 12, the last point with a meaningful throughput increase before diminishing returns and then decline.


## % of Theoretical Peak Bandwidth & Diminishing Returns

Measured peak: 6.948 GiB/s ≈ 7.46 GB/s.

- For dual-channel DDR4-3200:
  Measured peak is 6.948 GiB/s ≈ 7.46 GB/s (1 GiB = 1.0737 GB).
  Theoretical peak = 51.2 GB/s → 7.46/51.2→14.6% of peak.
- This gap is expected: practical memory bandwidth is limited by cache effects, controller scheduling, row buffer conflicts, and coherence overheads. The knee reflects saturation: concurrency inflates queueing delay but no longer boosts service rate.

## Logical Tie-in to Little’s Law
Little’s Law:  
Concurrency = Throughput * Latency
- **Below the knee (≤ 8–12 threads):** Increasing concurrency raises throughput faster than it inflates latency.  
- **At the knee (12 threads):** Memory subsystem hits saturation, extra concurrency bloats latency but throughput plateaus.  
- **Beyond the knee (16 threads):** Added concurrency only increases latency; throughput actually drops due to contention.




### 3.5 Working-set size sweep

<img width="1380" height="980" alt="image" src="https://github.com/user-attachments/assets/453fd16f-66b8-4298-9f45-2e42cbec485b" />
<img width="1779" height="980" alt="image" src="https://github.com/user-attachments/assets/e3de5f3c-efd8-422f-8fc7-08dfb4735ead" />
- From the Bandwidth and latency transition graphs, they are both flat across 32 KB–512 MB, indicating a DRAM-bound, latency-limited access pattern with ~one line in flight. This means that both latency and bandwidth are governed by main-memory service time rather than cache capacity. The transitions were marked by the vertical lines, provided by the CPU statistics.

### 3.6 Cache-miss impacts

### Part 6. Cache-Miss Impact

**Methodology.**  
Because WSL2’s kernel does not expose hardware performance counters, I could not directly measure cache- or TLB-miss rates with perf. Instead, I relied on cycle-accurate runtime and throughput measurements as a proxy. The observed knees in throughput and rising latency align with expected cache capacity and stride effects, providing indirect but consistent evidence of cache/TLB miss impact. On native Linux with perf, these results would be confirmed by correlating runtime directly with measured miss rates.

I implemented a lightweight SAXPY kernel and swept the working set size (32 KiB – 256 MiB), stride (1–256 elements), and access pattern (sequential, strided, random). 
- *Pattern 0 = sequential*
- *Pattern 1 = strided*
- *Pattern 2 = random*

**Results.**

<img width="1280" height="960" alt="part6_throughput_vs_ws" src="https://github.com/user-attachments/assets/a0b74d5c-451d-4c3b-b85a-d795dc4660d8" />

Figure 1 (Throughput vs. Working Set) shows clear *knees* as the footprint exceeds successive cache levels. Sequential accesses (pattern 0) achieve very high throughput (~25 GiB/s) while the working set fits in cache, then drop sharply at ~32 KiB, ~512 KiB, and ~4 MiB, corresponding to L1, L2, and LLC capacity limits. Strided accesses (pattern 1) perform consistently worse, as large strides reduce spatial locality and limit the effectiveness of the hardware prefetcher. Random accesses (pattern 2) are worst, staying near ~1 GiB/s regardless of footprint, since each access effectively behaves as a miss beyond the L1 cache.

<img width="1280" height="960" alt="image" src="https://github.com/user-attachments/assets/d1b1740f-4004-4e0c-9c70-8486d7fd6157" />

Figure 2 (Latency vs. Stride) highlights how access pattern further controls performance. Sequential accesses maintain a flat, low latency. Strided accesses show steadily rising latency with increasing stride length, as fewer useful bytes are extracted per cache line. Random accesses maintain the highest latency (~2.7–2.8 ns/byte), reflecting the cost of frequent cache misses with no prefetch benefit.

**Correlation and AMAT.**  
Although explicit cache-miss counters were unavailable, the runtime trends align with the **Average Memory Access Time (AMAT)** model:

*AMAT = hit time + local miss rate X miss penalty*

As the working set grows, miss rates at each level increase, introducing the penalty of the next level. This explains the observed throughput plateaus and latency increases. Sequential accesses benefit from low miss rates and prefetching, while strided and random accesses raise the effective miss rate, pushing AMAT upward. Thus, performance is strongly correlated with cache-miss behavior, even when measured indirectly.

### 3.7 TLB-miss impact

**Methodology.**  
To study TLB effects, I reused the SAXPY kernel but fixed the working set size at 512 MiB to ensure the active page set far exceeded DTLB reach. I then varied stride in element units relative to a 4 KiB page: 1024 (one float per page, worst locality), 512, 256, and 128 (increasing reuse within each page). Each run was repeated three times, and the mean ± stdev was plotted. Because WSL2 does not expose hardware TLB miss counters, I used throughput and latency as proxies for TLB behavior. On native Linux, these results would normally be confirmed with `dTLB-load-misses` and page-walk counters. Huge pages could not be tested in WSL2, but they would expand reach and reduce the observed slowdowns.

**Results.**


<img width="1280" height="960" alt="part7_throughput_vs_stride" src="https://github.com/user-attachments/assets/8b9c6c90-fdd3-4507-8457-c554e3855a27" />

Figure above (Throughput vs. Stride) shows the highest throughput when stride = 128 (multiple elements per page) and a downward slope as stride increases to 1024 (one element per page). This trend is consistent with increasing TLB pressure: fewer elements are accessed per page, more unique pages are touched, and the TLB must service more lookups.

<img width="1280" height="960" alt="part7_latency_vs_stride" src="https://github.com/user-attachments/assets/2d182be9-aec3-4d67-ac70-00be35be453f" />
Figure above (Latency vs. Stride) mirrors this trend. Latency is lowest with stride = 128 and grows slightly as stride approaches 1024. Although the error bars are large due to WSL2 noise, the mean values reveal the expected pattern: poorer page locality corresponds to higher access latency.

**Discussion of DTLB Reach.**  
The effective reach of the DTLB can be estimated as:
\[
\text{Reach} \approx (\# \text{entries}) \times (\text{page size})
\]
For example, with 64 DTLB entries and 4 KiB pages, reach is ~256 KiB. With a 512 MiB footprint, the active page set greatly exceeds this reach, ensuring frequent TLB misses and costly page walks at large strides. Huge pages (e.g., 2 MiB) would expand reach by 512× and significantly reduce this overhead.

**Conclusion.**  
Even without direct counters, throughput and latency trends demonstrate the impact of TLB misses. Poor locality (stride = 1024) reduces throughput and raises latency, while better page reuse (stride = 128) alleviates TLB pressure. This behavior is consistent with the limited reach of the DTLB and the performance penalties of page walks.




