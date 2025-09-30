import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

results_dir = Path.home() / "fio" / "results"
json_files = list(results_dir.glob("*.json"))

baseline_rows = []
sweep_rows = []

for jf in json_files:
    with open(jf) as f:
        data = json.load(f)

        # iterate through ALL jobs in the file (4k, 8k, ... 256k)
        for job in data["jobs"]:
            stats = job["read"] if job["read"]["io_bytes"] > 0 else job["write"]

            row = {
                "file": jf.name,
                "jobname": job["jobname"],   # rand_4k, rand_8k, etc.
                "iops": stats["iops"],
                "bw_MBps": stats["bw_bytes"] / (1024*1024),
                "lat_avg_us": stats["clat_ns"]["mean"] / 1000,
                "lat_99_us": stats["clat_ns"]["percentile"].get("99.000000", 0) / 1000,
                "bs": job.get("job options", {}).get("bs", None)
            }

            if "_qd1" in jf.name:
                baseline_rows.append(row)
            elif "_sweep" in jf.name:
                sweep_rows.append(row)

def save_table(df, name):
    """Save dataframe to both CSV and Markdown (if possible)."""
    df.to_csv(f"{name}.csv", index=False)
    try:
        df.to_markdown(f"{name}.md", index=False)
    except ImportError:
        print(f"[!] Skipping Markdown export for {name} (install `tabulate` to enable)")

# === Baselines ===
if baseline_rows:
    df_base = pd.DataFrame(baseline_rows)
    print("\n=== Zero-Queue Baselines ===")
    print(df_base[["file","iops","bw_MBps","lat_avg_us","lat_99_us"]])
    save_table(df_base, "baseline_table")

    plt.figure(figsize=(8,5))
    plt.bar(df_base["file"], df_base["bw_MBps"])
    plt.ylabel("Bandwidth (MB/s)")
    plt.title("Baseline Workload Bandwidth")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig("baseline_bandwidth.png")

    plt.figure(figsize=(8,5))
    plt.bar(df_base["file"], df_base["iops"])
    plt.ylabel("IOPS")
    plt.title("Baseline Workload IOPS")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig("baseline_iops.png")

# === Sweeps ===
if sweep_rows:
    df_sweep = pd.DataFrame(sweep_rows)

    def parse_bs(x):
        if x is None:
            return None
        if x.endswith("k"):
            return int(x[:-1]) * 1024
        elif x.endswith("M"):
            return int(x[:-1]) * 1024 * 1024
        else:
            return int(x)
    df_sweep["bs_bytes"] = df_sweep["bs"].apply(parse_bs)

    print("\n=== Pattern & Granularity Sweep ===")
    print(df_sweep[["file","bs","iops","bw_MBps","lat_avg_us","lat_99_us"]])
    save_table(df_sweep, "sweep_table")

    # Bandwidth vs block size
    plt.figure(figsize=(8,5))
    for f, g in df_sweep.groupby("file"):
        plt.plot(g["bs_bytes"], g["bw_MBps"], marker="o", label=f)
    plt.xscale("log", base=2)
    plt.xlabel("Block Size (bytes)")
    plt.ylabel("Bandwidth (MB/s)")
    plt.title("Bandwidth vs Block Size Sweep")
    plt.legend()
    plt.tight_layout()
    plt.savefig("sweep_bandwidth.png")

    # Latency vs block size
    plt.figure(figsize=(8,5))
    for f, g in df_sweep.groupby("file"):
        plt.plot(g["bs_bytes"], g["lat_avg_us"], marker="o", label=f)
    plt.xscale("log", base=2)
    plt.yscale("log")
    plt.xlabel("Block Size (bytes)")
    plt.ylabel("Average Latency (µs)")
    plt.title("Latency vs Block Size Sweep")
    plt.legend()
    plt.tight_layout()
    plt.savefig("sweep_latency.png")

print("\nSaved plots and tables (CSV always, Markdown if available).")
