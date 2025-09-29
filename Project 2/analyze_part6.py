import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv("part6_data.csv")

# Strip "ws_KiB=..." etc. if present
for col in df.columns:
    df[col] = df[col].astype(str).str.replace(r"^[a-zA-Z_]+=*", "", regex=True)

num_cols = ["ws_KiB","stride","pattern","repeats","cycles","bytes"]
for col in num_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Compute metrics
GHz = 3.0  # adjust for your CPU
df["time_s"] = df["cycles"] / (GHz * 1e9)
df["throughput_GiBps"] = df["bytes"] / df["time_s"] / (1024**3)
df["ns_per_byte"] = (df["time_s"] / df["bytes"]) * 1e9

# --- Throughput vs footprint with error bars ---
plt.figure()
for pat in df["pattern"].unique():
    sub = df[df["pattern"] == pat]
    grouped = sub.groupby("ws_KiB").agg(
        mean_tp=("throughput_GiBps", "mean"),
        std_tp=("throughput_GiBps", "std")
    )
    plt.errorbar(grouped.index, grouped["mean_tp"],
                 yerr=grouped["std_tp"],
                 marker="o", capsize=4, label=f"pattern {pat}")

plt.xscale("log")
plt.xlabel("Working set size (KiB, log scale)")
plt.ylabel("Throughput (GiB/s)")
plt.title("Cache impact: Throughput vs footprint")
plt.legend()
plt.savefig("part6_throughput_vs_ws.png", dpi=200)

# --- Latency vs stride with error bars ---
plt.figure()
for pat in df["pattern"].unique():
    sub = df[df["pattern"] == pat]
    grouped = sub.groupby("stride").agg(
        mean_lat=("ns_per_byte", "mean"),
        std_lat=("ns_per_byte", "std")
    )
    plt.errorbar(grouped.index, grouped["mean_lat"],
                 yerr=grouped["std_lat"],
                 marker="x", capsize=4, label=f"pattern {pat}")

plt.xscale("log")
plt.xlabel("Stride (elements, log scale)")
plt.ylabel("Latency (ns per byte)")
plt.title("Cache impact: Latency vs stride")
plt.legend()
plt.savefig("part6_latency_vs_stride.png", dpi=200)

print("✅ Saved plots with error bars: part6_throughput_vs_ws.png and part6_latency_vs_stride.png")
