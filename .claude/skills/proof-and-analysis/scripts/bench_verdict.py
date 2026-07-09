#!/usr/bin/env python3
"""bench_verdict.py -- apply the overlap decision rule to two benchmark sample sets.

DIAGNOSTIC TOOL SPEC
  Question it answers : "Is variant B conclusively faster (or slower) than
                         variant A, or is the difference inside the noise?"
  How to run          : python3 bench_verdict.py baseline.txt candidate.txt
                        (each file: one timing per line, same unit, any unit)
  Interpretation      : exit 0 = CONCLUSIVE difference (verdict printed)
                        exit 1 = INCONCLUSIVE (intervals overlap) or samples
                                 identical -- do NOT claim a speedup
                        exit 2 = usage / parse error (e.g. too few runs)
  Known blind spots   : - This is a conservative HEURISTIC (interval overlap),
                          not a statistical hypothesis test. It can say
                          INCONCLUSIVE for a real small effect; collect more
                          runs or consult a proper test (e.g. Mann-Whitney U)
                          before betting on differences < ~10%.
                        - Garbage in, garbage out: it cannot detect that you
                          skipped warmup or ran the two variants under
                          different load. See diagnostics-and-tooling for
                          measurement mechanics.
                        - Assumes both files use the SAME unit; it never
                          converts.

Stdlib only. Portable across Windows / macOS / Linux. Python 3.8+.

Decision rule implemented (see proof-and-analysis SKILL.md, Recipe 3):
  1. Require at least --min-runs samples per variant (default 10).
  2. For each variant compute min, median, p95.
  3. If the intervals [min, p95] of the two variants OVERLAP -> INCONCLUSIVE.
  4. Otherwise the verdict is the ratio of medians, reported as
     "B is Nx faster/slower than A".

Examples:
  python3 bench_verdict.py old_ms.txt new_ms.txt
  python3 bench_verdict.py old.txt new.txt --unit ms --min-runs 15
  python3 bench_verdict.py old.txt new.txt --report json
"""

import argparse
import json
import math
import statistics
import sys


def percentile(sorted_vals, p):
    """Nearest-rank percentile (p in 0..100) of an ascending-sorted list."""
    if not sorted_vals:
        raise ValueError("empty sample")
    k = max(1, math.ceil(p / 100.0 * len(sorted_vals)))
    return sorted_vals[k - 1]


def load_samples(path):
    vals = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                v = float(line)
            except ValueError:
                raise ValueError(f"{path}:{i}: not a number: {line!r}")
            if v < 0:
                raise ValueError(f"{path}:{i}: negative timing: {v}")
            vals.append(v)
    return vals


def summarize(vals):
    s = sorted(vals)
    return {
        "n": len(s),
        "min": s[0],
        "median": statistics.median(s),
        "p95": percentile(s, 95),
        "max": s[-1],
        "spread_pct": (percentile(s, 95) - s[0]) / statistics.median(s) * 100
        if statistics.median(s) > 0 else float("inf"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Overlap decision rule for two benchmark sample files "
                    "(one timing per line; lower = faster).")
    ap.add_argument("baseline", help="samples for variant A (baseline)")
    ap.add_argument("candidate", help="samples for variant B (candidate)")
    ap.add_argument("--unit", default="", help="unit label for the report "
                    "(cosmetic only, e.g. ms)")
    ap.add_argument("--min-runs", type=int, default=10,
                    help="minimum samples required per variant (default 10)")
    ap.add_argument("--report", choices=["human", "json"], default="human")
    args = ap.parse_args(argv)

    try:
        a = load_samples(args.baseline)
        b = load_samples(args.candidate)
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    for name, vals in ((args.baseline, a), (args.candidate, b)):
        if len(vals) < args.min_runs:
            print(f"ERROR: {name} has {len(vals)} samples; "
                  f"need >= {args.min_runs}. Collect more runs.",
                  file=sys.stderr)
            return 2

    sa, sb = summarize(a), summarize(b)
    overlap = not (sa["p95"] < sb["min"] or sb["p95"] < sa["min"])

    if sb["median"] == 0 or sa["median"] == 0:
        ratio = None
    elif sb["median"] < sa["median"]:
        ratio = ("faster", sa["median"] / sb["median"])
    else:
        ratio = ("slower", sb["median"] / sa["median"])

    verdict = "INCONCLUSIVE" if overlap else "CONCLUSIVE"
    u = f" {args.unit}" if args.unit else ""

    if args.report == "json":
        print(json.dumps({
            "verdict": verdict,
            "overlap": overlap,
            "baseline": sa, "candidate": sb,
            "median_ratio": None if ratio is None else round(ratio[1], 3),
            "direction": None if ratio is None else ratio[0],
        }, indent=2))
    else:
        for name, s in (("A (baseline) ", sa), ("B (candidate)", sb)):
            print(f"{name}: n={s['n']}  min={s['min']:g}{u}  "
                  f"median={s['median']:g}{u}  p95={s['p95']:g}{u}  "
                  f"spread={s['spread_pct']:.1f}%")
        if overlap:
            print(f"VERDICT: INCONCLUSIVE -- the [min, p95] intervals overlap "
                  f"([{sa['min']:g}, {sa['p95']:g}] vs "
                  f"[{sb['min']:g}, {sb['p95']:g}]).")
            print("Do not claim a speedup. Collect more runs, reduce noise "
                  "(close other programs, pin machine state), or accept "
                  "'no demonstrated difference'.")
        else:
            print(f"VERDICT: CONCLUSIVE -- B is {ratio[1]:.2f}x {ratio[0]} "
                  f"than A (medians {sa['median']:g}{u} -> "
                  f"{sb['median']:g}{u}; intervals do not overlap).")
    return 1 if overlap else 0


if __name__ == "__main__":
    sys.exit(main())
