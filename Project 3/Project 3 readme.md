# SSD Performance Profiling — Project Report (ECSE 4320/6320)

> **Author:** Yuming Tseng  
> **Machine:** AMD Ryzen 7 5800X 8 core processor

---

## 1) Introduction
Modern SSDs (especially NVMe) can deliver massive IOPS and GB/s when requests are issued concurrently. Like 
memory, storage exhibits a classic throughput–latency trade-off governed by queuing theory: increasing queue 
depth improves utilization and throughput up to a saturation knee, after which latency rises sharply with little 
additional throughput.
## 2) Experimental Setup
Using the flexible I/O tester from Ubuntu, several experiments were conducted to explore SSD performance.

## 3) Results

### 3.1 Zero-queue baselines

- To isolate the Queue-Depth latency, each workload was configured with iodepth=1, forcing one outstanding I/O at a time. Page cache effects were bypassed using direct=1, and I/O block sizes were aligned to the underlying sector size (4 KiB for random access, 128 KiB for sequential). This ensures that reported latencies reflect true device service times without batching or caching artifacts.

- Below is the tabular and graph representation of the results derived from the experiment:

| Workload           | Avg Latency (µs) | 99th % Latency (µs) | Bandwidth (MB/s) | IOPS   |
|--------------------|------------------|---------------------|------------------|--------|
| 4K RandRead (QD=1) | 57.64            | 152.58              | 55.99            | 14,334 |
| 4K RandWrite (QD=1)| 106.02           | 411.65              | 33.32            | 8,531  |
| 128K SeqRead (QD=1)| 180.30           | 395.26              | 642.93           | 5,143  |
| 128K SeqWrite (QD=1)| 124.91          | 248.83              | 902.97           | 7,224  |

<p float="left">
  <img src="https://github.com/user-attachments/assets/1773b93b-44f1-4e46-a87a-a85685ae004a" width="400"/>
  <img src="https://github.com/user-attachments/assets/fceabe9b-2ca5-4565-b66f-67093ef0fe0c" width="400"/>
</p>

- As expected, small-block random I/O delivers far higher IOPS but lower bandwidth, while large-block sequential transfers saturate bandwidth with fewer operations per second. Latency is lowest for 4 KiB random reads (~58 µs average) but grows substantially for writes, reflecting write-path overhead. Sequential operations show higher average latency per request but make up that cost over much larger transfers, yielding far higher throughput.

### 3.2 Block-size & pattern sweep

To evaluate the effect of block size and access pattern, I constructed two fio sweep configurations: one for sequential reads and one for random reads. Each configuration defined explicit block sizes from 4 KiB to 256 KiB, executed sequentially with stonewall to isolate results per block size. I set the queue depth to iodepth=1 to capture the true per-request latency and used direct=1 to bypass the page cache. Runs were conducted on the same backing file with 30-second durations per block size to ensure stable averages. Graphs and Tables below represent bandwidth and latency metrics extracted directly from fio’s JSON output.

<p float="left">
<img width="800" height="500" alt="sweep_bandwidth" src="https://github.com/user-attachments/assets/a24a5d14-0163-42a5-9e74-ac29af12b789" />
<img width="800" height="500" alt="sweep_latency" src="https://github.com/user-attachments/assets/da92b5b0-02e8-4b61-9358-53c0c120a913" />
</p>

| file               | bs   |     iops |   bw_MBps |   lat_avg_us |   lat_99_us |
|--------------------|------|----------|-----------|--------------|-------------|
| seq_bs_sweep.json  | 4k   | 10474.6  |   40.9162 |      85.63   |     168.96  |
| seq_bs_sweep.json  | 8k   | 11109.3  |   86.7911 |      80.3648 |     171.008 |
| seq_bs_sweep.json  | 16k  | 10745.2  |  167.894  |      83.0821 |     177.152 |
| seq_bs_sweep.json  | 32k  |  9528.55 |  297.767  |      94.1994 |     209.92  |
| seq_bs_sweep.json  | 64k  |  7415.15 |  463.447  |     123.217  |     337.92  |
| seq_bs_sweep.json  | 128k |  4457.55 |  557.194  |     210.561  |     552.96  |
| seq_bs_sweep.json  | 256k |  2241.43 |  560.356  |     427.373  |     643.072 |
| rand_bs_sweep.json | 4k   |  6383.12 |   24.9341 |     146.287  |     244.736 |
| rand_bs_sweep.json | 8k   |  5941.27 |   46.4162 |     157.322  |     276.48  |
| rand_bs_sweep.json | 16k  |  5196.53 |   81.1957 |     181.101  |     296.96  |
| rand_bs_sweep.json | 32k  |  4294.12 |  134.191  |     219.813  |     374.784 |
| rand_bs_sweep.json | 64k  |  3530.92 |  220.682  |     270.006  |     423.936 |
| rand_bs_sweep.json | 128k |  2575.11 |  321.889  |     372.725  |     544.768 |
| rand_bs_sweep.json | 256k |  1935.4  |  483.851  |     497.652  |     667.648 | 

- Bandwidth scaling: Sequential access benefits strongly from prefetching and large transfers, with throughput rising sharply and saturating at ~550 MB/s around 128–256 KiB. Random access shows a similar trend but with a lower plateau (~480 MB/s), reflecting the absence of spatial locality and reduced controller prefetch efficiency.

- IOPS vs bandwidth regime: At small block sizes, performance is IOPS-dominated: random 4 KiB delivers ~6.3K IOPS but only ~25 MB/s. As block size grows, each I/O transfers more data, shifting the bottleneck from IOPS to bandwidth. The crossover point occurs between 32–64 KiB, after which bandwidth plateaus while IOPS decline proportionally.

- Latency scaling: Latency increases monotonically with block size since each request moves more data. Sequential latencies remain lower than random at all sizes due to effective queue coalescing and controller prefetch. Random latencies show higher overhead and steeper growth.

- Controller and prefetch limits: The plateau at large block sizes indicates that the device/controller has reached its throughput ceiling, and additional block size increases no longer improve bandwidth. Prefetchers and caching help sequential patterns but are ineffective for random access, explaining the performance gap.

### 3.3 Read/Write mix sweep

- For this section, I kept the experiment consistent by having a fixed pattern (random), block size (4 KiB), queue depth (32), threads (1), direct=1, and the same 8 GiB file. Then, I ran 100%R, 100%W, 70/30, 50/50, followed by results captured to a single JSON and plotted so throughput and latency come from the same runs.

<p float="left">
  <img src="https://github.com/user-attachments/assets/5da5c320-db5a-4672-bb9d-5e12d09f23e8" width="400"/>
  <img src="https://github.com/user-attachments/assets/8a162ed9-0ea9-4a94-b339-5c88e9b961f3" width="400"/>
</p>

- R100 → W100: Throughput drops ~20% (399.8→320.9 MiB/s) while latency rises ~25% (308.5→384.8 µs). This is expected, as random writes require program/erase work, metadata updates, and garbage collection, widening the p99 tail (561→692 µs).

- Mixed workloads aren’t linear. Even a modest 30% write share lifts tail latency disproportionately (p99 ≈733 µs), since background garbage collection and write amplification consume resources that would otherwise serve reads.

- Read latency exceeds write latency in mixes. At 70/30 and 50/50, the controller appears to prioritize draining writes to prevent buffer overflow, causing reads to queue and inflate in latency (e.g., 390 µs vs 331–348 µs).

- Write buffering effects. Short bursts can show inflated write performance because data lands in fast DRAM or SLC caches. The 30s steady-state runs show the true cost once buffers drain.

- Flushes/barriers. Devices that enforce flushes or FUA writes incur extra latency for durability guarantees. While not directly measured here, these mechanisms are a known contributor to higher write latencies.

- Bandwidth rebound in mixes. Mixed ratios slightly exceed pure-write throughput (331–333 MiB/s vs 321 MiB/s), suggesting some overlap between reads and writes, but tail latency remains governed by garbage collection.

### 3.4 Queue-depth/ parallelism sweep

- I fixed pattern (random), block size (4 KiB), and file size (8 GiB). Using direct=1 and norandommap=1, I swept queue depth across 6 points (QD = 1, 2, 4, 8, 16, 64). Each run lasted 30 s with a 5 s ramp. Results were collected in JSON and plotted as a single throughput vs. latency trade-off curve, with p99 latency extracted to highlight tail behavior.

<img width="640" height="480" alt="image" src="https://github.com/user-attachments/assets/bb829992-8ea5-4a62-bb4c-46ec23476eef" />

- From the experiment, we could see that the throughput scales nearly linearly from QD=1 through QD=8, rising from 30 MiB/s to ~221 MiB/s while latency stays in the ~120–137 µs range. The knee occurs between QD=8 and QD=16: throughput only improves by ~40% (221→312 MiB/s) while latency jumps ~43% (137→196 µs). Beyond this point, throughput gains diminish, reaching 681 MiB/s at QD=64—but average latency more than doubles to 546 µs, with p99 tail latency exceeding 1 ms.
- According to Little’s Law, where Throughput ≈ Concurrency ÷ Latency, this knee reflects the SSD reaching its internal channel/controller parallelism limit
  - Additional requests simply accumulate in the queue, inflating latency without proportional throughput benefit.
- The observed peak of 681 MiB/s is close to typical vendor-spec random read ratings (≈700 MiB/s), indicating we reached near-saturation. Overall, the curve shows strong scaling at small QD, clear saturation at QD≈16, and rapidly growing tail latency beyond the knee—highlighting the trade-off between throughput and responsiveness for latency-sensitive workloads.

### 3.5 Tail-Characterization

- Building on the queue-depth sweep, I measured detailed latency percentiles at QD = 8 (mid-load) and QD = 16 (near the knee) for 4 KiB random reads. Percentiles p50/p95/p99/p99.9 were extracted directly from the fio JSON.

| QD | p50 (µs) | p95 (µs) | p99 (µs) | p99.9 (µs) | Avg (µs) |
|---:|---:|---:|---:|---:|---:| 
| 8 | 138.2 | 183.3 | 259.1 | 448.5 | 141.1 | 
| 16 | 185.3 | 261.1 | 354.3 | 514.0 | 187.6 |

- At QD = 8, the distribution is tight: p50 is 138 µs and p99.9 only 3.2× higher at 449 µs, indicating predictable service with short queues.
- At QD = 16, the entire distribution shifts upward—p50 rises by ~34%, and p99.9 extends past 0.5 ms. This widening tail reflects queueing delays as the device nears saturation.
- By Little’s Law, additional concurrency past the knee translates mainly into waiting time rather than service capacity, which inflates the upper percentiles disproportionately.
- From an SLA perspective, if a workload requires p99 < 300 µs, QD = 8 would be safe, but QD = 16 risks violation despite ~40% higher throughput. This underscores the throughput–latency trade-off: higher queue depth improves bandwidth but degrades predictability, and tail latencies near the knee highlight limits for latency-sensitive applications.

### 4 Anomalies/Limitations

- Results were collected on WSL2 rather than bare-metal Linux, which may introduce virtualization overhead and prevent direct hardware counter measurement. In 3.3, mixed read/write ratios unexpectedly showed higher read latency than write latency, which likely reflects controller scheduling and buffer-drain prioritization. Additionally, shorter 30s runs may mask long-term steady-state write amplification, so sustained workloads could exhibit higher tail latency. These observations highlight the need to interpret results in the context of system/software limitations rather than as absolute device maxima.
