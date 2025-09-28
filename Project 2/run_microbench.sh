
#!/usr/bin/env bash
set -euo pipefail

BIN="./bin/microbench"
OUT="results/csv/microbench_results.csv"
mkdir -p results/csv results/raw

if [ ! -x "$BIN" ]; then
  echo "ERROR: microbench binary not found. Run: make"
  exit 1
fi

echo "ts,N_bytes,stride,repeats,read_pct,threads,time,GiB/s" > "$OUT"

ts=$(date +"%Y-%m-%d %H:%M:%S")

# Working set sweep (32KB → 512MB)
for N in 32768 262144 2097152 33554432 268435456 536870912; do
  $BIN $N 1 5 100 1 | tee -a results/raw/microbench_out.txt | \
  awk -v ts="$ts" -F, '{print ts","$1","$2","$3","$4","$5","$6","$7}' >> "$OUT"
done

# Stride sweep at 64MB
for STR in 1 2 4 8 16 32 64 128 256 512 1024; do
  $BIN $((64*1024*1024)) $STR 5 100 1 | tee -a results/raw/microbench_out.txt | \
  awk -v ts="$ts" -F, '{print ts","$1","$2","$3","$4","$5","$6","$7}' >> "$OUT"
done

# Read/Write mix at 64MB, stride=1
for RW in 100 70 50 0; do
  $BIN $((64*1024*1024)) 1 5 $RW 1 | tee -a results/raw/microbench_out.txt | \
  awk -v ts="$ts" -F, '{print ts","$1","$2","$3","$4","$5","$6","$7}' >> "$OUT"
done

# Intensity sweep at 256MB, stride=1
for T in 1 2 4 8; do
  $BIN $((256*1024*1024)) 1 5 100 $T | tee -a results/raw/microbench_out.txt | \
  awk -v ts="$ts" -F, '{print ts","$1","$2","$3","$4","$5","$6","$7}' >> "$OUT"
done

echo "Results saved to $OUT"
