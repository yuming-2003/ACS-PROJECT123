
import argparse, pandas as pd, matplotlib.pyplot as plt, os, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    df = pd.read_csv(args.csv, parse_dates=["timestamp"])

    os.makedirs("plots", exist_ok=True)

    # Speedup plots: simd vs scalar per kernel/dtype
    for (k,d), g in df.groupby(["kernel","dtype"]):
        piv = g.pivot_table(index="N", columns="variant", values="time_ms", aggfunc="median")
        if "scalar" in piv and "simd" in piv:
            speedup = piv["scalar"] / piv["simd"]
            plt.figure()
            plt.title(f"Speedup (scalar/simd) — {k} ({d})")
            plt.xlabel("N (elements)"); plt.ylabel("Speedup")
            plt.xscale("log")
            plt.plot(speedup.index, speedup.values, marker="o")
            plt.grid(True, which="both", linestyle=":")
            plt.savefig(f"plots/speedup_{k}_{d}.png", bbox_inches="tight")
            plt.close()

    # GFLOP/s vs N for each variant
    for (k,d,v), g in df.groupby(["kernel","dtype","variant"]):
        gg = g.groupby("N", as_index=True)["gflops"].median()
        plt.figure()
        plt.title(f"GFLOP/s vs N — {k} ({d}, {v})")
        plt.xlabel("N (elements)"); plt.ylabel("GFLOP/s")
        plt.xscale("log")
        plt.plot(gg.index, gg.values, marker="o")
        plt.grid(True, which="both", linestyle=":")
        plt.savefig(f"plots/gflops_{k}_{d}_{v}.png", bbox_inches="tight")
        plt.close()

    # CPE vs N if available
    sub = df.dropna(subset=["cpe"])
    if not sub.empty:
        for (k,d,v), g in sub.groupby(["kernel","dtype","variant"]):
            gg = g.groupby("N", as_index=True)["cpe"].median()
            plt.figure()
            plt.title(f"CPE vs N — {k} ({d}, {v})")
            plt.xlabel("N (elements)"); plt.ylabel("Cycles per element")
            plt.xscale("log")
            plt.plot(gg.index, gg.values, marker="o")
            plt.grid(True, which="both", linestyle=":")
            plt.savefig(f"plots/cpe_{k}_{d}_{v}.png", bbox_inches="tight")
            plt.close()

    print("Plots saved to plots/*.png")

if __name__ == "__main__":
    main()
