import json, sys, pathlib
import matplotlib.pyplot as plt

path = pathlib.Path.home() / "fio" / "results" / "rwmix_4k_rand_qd32.json"
if len(sys.argv) > 1:
    path = pathlib.Path(sys.argv[1])

with open(path) as f:
    data = json.load(f)

# Order the mixes as requested
order = ["R100", "W100", "R70W30", "R50W50"]

rows = []
for job in data["jobs"]:
    name = job["jobname"]
    if name not in order:
        continue
    # Throughput (MiB/s)
    # fio reports 'bw' in KiB/s
    if "read" in job and job["read"]["io_bytes"] > 0:
        rbw_mib = job["read"]["bw"] / 1024.0
        r_iops  = job["read"]["iops"]
        r_latus = (job["read"]["clat_ns"]["mean"] / 1000.0) if job["read"]["clat_ns"]["mean"] > 0 else 0.0
        r_p99us = (job["read"]["clat_ns"]["percentile"]["99.000000"] / 1000.0) if job["read"]["clat_ns"]["percentile"] else 0.0
    else:
        rbw_mib = r_iops = r_latus = r_p99us = 0.0

    if "write" in job and job["write"]["io_bytes"] > 0:
        wbw_mib = job["write"]["bw"] / 1024.0
        w_iops  = job["write"]["iops"]
        w_latus = (job["write"]["clat_ns"]["mean"] / 1000.0) if job["write"]["clat_ns"]["mean"] > 0 else 0.0
        w_p99us = (job["write"]["clat_ns"]["percentile"]["99.000000"] / 1000.0) if job["write"]["clat_ns"]["percentile"] else 0.0
    else:
        wbw_mib = w_iops = w_latus = w_p99us = 0.0

    total_bw_mib = rbw_mib + wbw_mib
    # For latency, show read and write separately; also compute weighted mean by IO count
    total_ios = 0
    if "read" in job: total_ios += job["read"]["total_ios"]
    if "write" in job: total_ios += job["write"]["total_ios"]
    if total_ios > 0:
        r_weight = (job["read"]["total_ios"] if "read" in job else 0)/total_ios
        w_weight = (job["write"]["total_ios"] if "write" in job else 0)/total_ios
        lat_avg_us = r_weight * r_latus + w_weight * w_latus
        lat_p99_us = max(r_p99us, w_p99us)  # conservative
    else:
        lat_avg_us = lat_p99_us = 0.0

    rows.append({
        "name": name, "total_bw_mib": total_bw_mib,
        "r_bw_mib": rbw_mib, "w_bw_mib": wbw_mib,
        "lat_avg_us": lat_avg_us, "lat_p99_us": lat_p99_us,
        "r_lat_us": r_latus, "w_lat_us": w_latus
    })

# Reorder
rows = sorted(rows, key=lambda r: order.index(r["name"]))

labels = [r["name"] for r in rows]
bw = [r["total_bw_mib"] for r in rows]
lat = [r["lat_avg_us"] for r in rows]

# Plot 1: Throughput vs Mix (MiB/s)
plt.figure()
plt.title("4 KiB Random, QD=32 — Throughput vs Read/Write Mix")
plt.xlabel("Mix")
plt.ylabel("Throughput (MiB/s)")
plt.plot(labels, bw, marker="o")
plt.grid(True, which="both", axis="both")
plt.tight_layout()
plt.savefig(path.with_suffix(".throughput.png"))

# Plot 2: Avg Latency vs Mix (µs)
plt.figure()
plt.title("4 KiB Random, QD=32 — Average Latency vs Read/Write Mix")
plt.xlabel("Mix")
plt.ylabel("Average Latency (µs)")
plt.plot(labels, lat, marker="o")
plt.grid(True, which="both", axis="both")
plt.tight_layout()
plt.savefig(path.with_suffix(".latency.png"))

# Also print a Markdown table you can paste
print("| Mix | Total BW (MiB/s) | Avg Lat (µs) | p99 Lat (µs) | Read Lat (µs) | Write Lat (µs) |")
print("|---|---:|---:|---:|---:|---:|")
for r in rows:
    print(f"| {r['name']} | {r['total_bw_mib']:.1f} | {r['lat_avg_us']:.1f} | {r['lat_p99_us']:.1f} | {r['r_lat_us']:.1f} | {r['w_lat_us']:.1f} |")
