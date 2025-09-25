#!/usr/bin/env bash
set -euo pipefail

# Suggested: fix CPU frequency governor and disable SMT for consistency (Linux specific)
# sudo cpupower frequency-set -g performance || true
# echo off | sudo tee /sys/devices/system/cpu/smt/control || true

mkdir -p results
CSV=results/default_results.csv
rm -f "$CSV"

# Optionally export your CPU GHz for CPE (cycles/element) estimation
# export CPU_GHZ=3.50

# Sizes (adjust to cross L1/L2/LLC/DRAM). You can override via env SIZES="..."
SIZES=${SIZES:-"16384 65536 262144 1048576 4194304 16777216 67108864"}

# Kernels and types
KERNELS=${KERNELS:-"saxpy mul stencil3"}
DTYPES=${DTYPES:-"f32 f64"}

# Build
make -j

# 1) Baseline vs auto-vectorized across sizes (unit stride, aligned)
for k in $KERNELS; do
  for t in $DTYPES; do
    for N in $SIZES; do
      ./bench_scalar --kernel $k --dtype $t --N $N --reps 5 --warmup 2 --csv "$CSV"
      ./bench_simd   --kernel $k --dtype $t --N $N --reps 5 --warmup 2 --csv "$CSV"
    done
  done
done

# 2) Alignment & tail handling (misalign by 4 bytes)
for mis in 0 4; do
  for t in $DTYPES; do
    for N in 1048576 1050000; do # multiple of wide vector vs tail case
      ./bench_simd --kernel saxpy --dtype $t --N $N --misalign $mis --csv "$CSV"
    done
  done
done

# 3) Stride effects (1,2,4,8)
for s in 1 2 4 8; do
  ./bench_simd --kernel mul --dtype f32 --N 16777216 --stride $s --csv "$CSV"
done

echo "Done. Results in $CSV"
