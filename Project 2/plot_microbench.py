import os
import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "results/csv/microbench_results_avg.csv"  # averaged results
FIG_DIR = "figures"
os.makedirs(FIG_DIR, exist_ok=True)

# --- Load data ---
df = pd.read_csv(CSV_PATH)

# --- Clean up columns if they still have prefixes ---
def strip_prefix(series, prefix):
    return series.astype(str).str.replace(prefix, "", regex=False).astype(float)

if df['N_bytes'].astype(str).str.contains("N_bytes=").any():
    df['N_bytes'] = strip_prefix(df['N_bytes'], "N_bytes=")
else:
    df['N_bytes'] = pd.to_numeric(df['N_bytes'], errors="coerce")

if df['stride'].astype(str).str.contains("stride=").any():
    df['stride'] = strip_prefix(df['stride'], "stride=")
else:
    df['stride'] = pd.to_numeric(df['stride'], errors="coerce")

if df['read_pct'].astype(str).str.contains("read%=").any():
    df['read_pct'] = strip_prefix(df['read_pct'], "read%=")
else:
    df['read_pct'] = pd.to_numeric(df['read_pct'], errors="coerce")

if df['threads'].astype(str).str.contains("threads=").any():
    df['threads'] = strip_prefix(df['threads'], "threads=")
else:
    df['threads'] = pd.to_numeric(df['threads'], errors="coerce")

# Ensure mean/std columns are numeric
df['mean_bw'] = pd.to_numeric(df['mean_bw'], errors='coerce')
df['std_bw'] = pd.to_numeric(df['std_bw'], errors='coerce')

# ---- Plot 1: Working-set sweep ----
ws = df[(df['stride']==1)&(df['read_pct']==100)&(df['threads']==1)]
ws = ws.sort_values('N_bytes')
plt.figure()
plt.errorbar(ws['N_bytes']/1024, ws['mean_bw'], yerr=ws['std_bw'],
             marker='o', capsize=3)
plt.xscale('log', base=2)
plt.xlabel("Working Set Size (KB, log2)")
plt.ylabel("Bandwidth (GiB/s)")
plt.title("Working-set Sweep")
plt.grid(True, which="both")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "working_set_sweep.png"))

# ---- Plot 2: Stride sweep ----
stride = df[(df['N_bytes']==64*1024*1024)&(df['read_pct']==100)&(df['threads']==1)]
stride = stride.sort_values('stride')
plt.figure()
plt.errorbar(stride['stride'], stride['mean_bw'], yerr=stride['std_bw'],
             marker='o', capsize=3)
plt.xscale('log', base=2)
plt.xlabel("Stride (elements, log2)")
plt.ylabel("Bandwidth (GiB/s)")
plt.title("Stride Sweep (64MB)")
plt.grid(True, which="both")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "stride_sweep.png"))

# ---- Plot 3: Read/Write mix ----
rw = df[(df['N_bytes']==64*1024*1024)&(df['stride']==1)&(df['threads']==1)]
plt.figure()
plt.bar(rw['read_pct'], rw['mean_bw'], yerr=rw['std_bw'], capsize=3)
plt.xlabel("Read %")
plt.ylabel("Bandwidth (GiB/s)")
plt.title("Read/Write Mix (64MB, stride=1)")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "rw_mix.png"))

# ---- Plot 4: Intensity sweep ----
intens = df[(df['N_bytes']==256*1024*1024)&(df['stride']==1)&(df['read_pct']==100)]
intens = intens.sort_values('threads')
plt.figure()
plt.errorbar(intens['threads'], intens['mean_bw'], yerr=intens['std_bw'],
             marker='o', capsize=3)
plt.xlabel("Threads")
plt.ylabel("Bandwidth (GiB/s)")
plt.title("Intensity Sweep (256MB, 100% Read)")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "intensity_sweep.png"))

print("✅ Plots with error bars saved in figures/")
