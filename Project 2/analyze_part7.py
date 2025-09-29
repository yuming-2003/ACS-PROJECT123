import pandas as pd
import matplotlib.pyplot as plt

# Load CSV (same format as part6)
df = pd.read_csv("part6_data.csv")

# Strip prefixes if present
for col in df.columns:
    df[col] = df[col].astype(str).str.replace(r"^[a-zA-Z_]+=*", "", regex=True)

num_cols = ["ws_KiB","stride","pattern","repeats","cycles","bytes"]
for col in num_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Metrics
GHz = 3.0  # adjust if you know
df["time_s"] = df["cycles"] / (GHz * 1e9)
df["throughput_GiBps"] = df["bytes"] / df["time_s"] / (1024**3)
df["ns_per_byte"] = (df["time_s"] / df["bytes"]) * 1e9

# Group by stride for error bars
grouped = df.groupby("stride").agg(
    mean_tp=("throughput_GiBps","mean"),
    std_tp=("throughput_GiBps","std"),
    mean_lat=("ns_per_byte","mean"),
    std_lat=("ns_per_byte","std")
)

# Plot throughput vs stride
plt.errorbar(grouped.index, grouped["mean_tp"], 
             yerr=grouped["std_tp"], marker="o", capsize=4)
plt.xscale("log")
plt.xlabel("Stride (elements, log scale)")
plt.ylabel("Throughput (GiB/s)")
plt.title("TLB impact: Throughput vs stride (large footprint)")
plt.savefig("part7_throughput_vs_stride.png", dpi=200)
plt.clf()

# Plot latency vs stride
plt.errorbar(grouped.index, grouped["mean_lat"], 
             yerr=grouped["std_lat"], marker="x", capsize=4)
plt.xscale("log")
plt.xlabel("Stride (elements, log scale)")
plt.ylabel("Latency (ns per byte)")
plt.title("TLB impact: Latency vs stride (large footprint)")
plt.savefig("part7_latency_vs_stride.png", dpi=200)

print("✅ Saved plots: part7_throughput_vs_stride.png and part7_latency_vs_stride.png")

