
import argparse, pandas as pd, matplotlib.pyplot as plt, numpy as np

def ai_for_kernel(kernel):
    # Arithmetic intensity (FLOPs/byte) assuming streaming loads/stores of floats
    # Adjust if needed in your report; here we approximate bytes moved per element for unit-stride.
    # Bytes per element:
    # saxpy: read x,y (2T) + write y (T) = 3T bytes, FLOPs=2
    # dot: read x,y (2T), reduction write negligible amortized, FLOPs=2
    # mul: read x,y (2T) + write z (T), FLOPs=1
    # stencil3: read 3 neighbors (3T) + write y (T), FLOPs=5
    return {
        "saxpy":   lambda T: 2.0/(3*T),
        "dot":     lambda T: 2.0/(2*T),
        "mul":     lambda T: 1.0/(3*T),
        "stencil3":lambda T: 5.0/(4*T),
    }[kernel]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", required=True, choices=["saxpy","dot","mul","stencil3"])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--gbytes_per_s", type=float, required=True, help="Measured memory bandwidth (GB/s)")
    ap.add_argument("--gflops_peak", type=float, required=True, help="Estimated peak GFLOP/s for chosen dtype and ISA")
    ap.add_argument("--dtype", choices=["f32","f64"], default="f32")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df[(df.kernel==args.kernel) & (df.variant=="simd")]
    if df.empty:
        raise SystemExit("No matching rows")

    # Arithmetic intensity (FLOPs/byte) for dtype
    T = 4 if args.dtype=="f32" else 8
    ai = ai_for_kernel(args.kernel)(T)

    # Achieved GFLOP/s across sizes
    g = df.groupby("N", as_index=True)["gflops"].median()

    plt.figure()
    plt.title(f"Roofline — {args.kernel} ({args.dtype})")
    plt.xlabel("Arithmetic Intensity (FLOPs/byte)")
    plt.ylabel("GFLOP/s")
    # Roofline lines
    ai_vals = np.array([1e-3, 1e3])
    mem_bound = args.gbytes_per_s * ai_vals
    compute_bound = np.full_like(ai_vals, args.gflops_peak)
    plt.loglog(ai_vals, mem_bound, label=f"Memory BW = {args.gbytes_per_s} GB/s")
    plt.loglog(ai_vals, compute_bound, label=f"Peak = {args.gflops_peak} GFLOP/s")

    # Plot achieved points at the kernel AI (constant AI); vary GFLOP/s with N
    plt.scatter([ai]*len(g), g.values, label="Achieved", marker="o")
    plt.legend()
    plt.grid(True, which="both", linestyle=":")
    out = f"plots/roofline_{args.kernel}_{args.dtype}.png"
    plt.savefig(out, bbox_inches="tight")
    print(f"Saved {out}. Use this plus a note on whether your points fall on the memory or compute roof.")

if __name__ == "__main__":
    main()
