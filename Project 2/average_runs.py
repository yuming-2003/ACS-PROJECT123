import pandas as pd
import glob

# Find all run CSVs
files = glob.glob("results/csv/microbench_results_run*.csv")
dfs = []

for f in files:
    df = pd.read_csv(f)
    # Clean columns (remove "time=" and "GiB/s=" strings)
    df['time'] = df['time'].astype(str).str.replace("time=","").astype(float)
    df['GiB/s'] = df['GiB/s'].astype(str).str.replace("GiB/s=","").astype(float)
    dfs.append(df)

# Concatenate all runs
data = pd.concat(dfs)

# Group by unique experiment parameters
grouped = data.groupby(
    ["N_bytes", "stride", "repeats", "read_pct", "threads"]
).agg(
    mean_time=("time","mean"),
    std_time=("time","std"),
    mean_bw=("GiB/s","mean"),
    std_bw=("GiB/s","std"),
    count=("time","count")
).reset_index()

# Save
out_path = "results/csv/microbench_results_avg.csv"
grouped.to_csv(out_path, index=False)
print(f"Averaged results saved to {out_path}")
