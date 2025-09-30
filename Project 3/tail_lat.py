import json, pathlib, sys

# Allow passing JSON file as arg
if len(sys.argv) < 2:
    print("Usage: python3 tail_lat.py <fio_json>")
    sys.exit(1)

p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text())

print("| QD | p50 (µs) | p95 (µs) | p99 (µs) | p99.9 (µs) | Avg (µs) |")
print("|---:|---:|---:|---:|---:|---:|")

for j in sorted(d["jobs"], key=lambda x:int(x["job options"]["iodepth"])):
    qd = int(j["job options"]["iodepth"])
    cl = j["read"]["clat_ns"]
    pct = cl.get("percentile", {})

    # Find keys by numeric closeness (fio sometimes formats them differently)
    def find_percentile(target):
        for k, v in pct.items():
            if abs(float(k) - target) < 1e-6:
                return v / 1000.0  # ns → µs
        return None

    p50  = find_percentile(50.0)
    p95  = find_percentile(95.0)
    p99  = find_percentile(99.0)
    p999 = find_percentile(99.9)
    avg  = cl["mean"] / 1000.0

    print(f"| {qd} | {p50:.1f} | {p95:.1f} | {p99:.1f} | {p999:.1f} | {avg:.1f} |")
