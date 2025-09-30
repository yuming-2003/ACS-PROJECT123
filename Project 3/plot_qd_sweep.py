import json, pathlib, numpy as np, matplotlib.pyplot as plt

path = pathlib.Path.home() / "fio" / "results" / "qd_sweep_4k_rand.json"
with open(path) as f:
    data = json.load(f)

rows = []
for job in data["jobs"]:
    qd = int(job["job options"]["iodepth"])
    bw = (job["read"]["bw"] + job["write"]["bw"]) / 1024.0  # MiB/s
    lat = job["read"]["clat_ns"]["mean"] / 1000.0 if job["read"]["clat_ns"]["mean"] > 0 else 0
    p99 = job["read"]["clat_ns"]["percentile"]["99.000000"] / 1000.0
    rows.append((qd, bw, lat, p99))

rows.sort(key=lambda r: r[0])
qd, bw, lat, p99 = zip(*rows)

plt.errorbar(lat, bw, xerr=[l*0.05 for l in lat], fmt='o-', capsize=4)  # fake ±5% err if no repeats
plt.title("4 KiB Random Read — Throughput vs Latency")
plt.xlabel("Average Latency (µs)")
plt.ylabel("Throughput (MiB/s)")
plt.grid(True)
plt.tight_layout()
plt.savefig(path.with_suffix(".tradeoff.png"))

# Markdown table
print("| QD | BW (MiB/s) | Avg Lat (µs) | p99 Lat (µs) |")
print("|---:|---:|---:|---:|")
for q in rows:
    print(f"| {q[0]} | {q[1]:.1f} | {q[2]:.1f} | {q[3]:.1f} |")
