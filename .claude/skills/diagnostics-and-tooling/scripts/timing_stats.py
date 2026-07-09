#!/usr/bin/env python3
"""timing_stats.py -- run a command N times and report wall-clock stats.

DIAGNOSTIC TOOL SPEC
  Question it answers : "How long does this command take, as a distribution,
                         not a single anecdotal run?"
  How to run          : python3 timing_stats.py --runs 10 --warmup 2 -- <cmd> [args...]
  Interpretation      : Read median for "typical", p95 for "bad case".
                        - p95 >> median (e.g. >2x): the tail is unstable --
                          suspect caching, GC, contention; do NOT quote the mean.
                        - min << median: later runs are being slowed by
                          something the first run avoided (or vice versa).
                        - any nonzero exit codes reported: timings are suspect,
                          fix the command before trusting numbers.
  Known blind spots   : - Wall clock only. Includes process startup; it cannot
                          separate CPU from I/O from subprocess overhead.
                        - Sequential runs on a busy machine measure the machine
                          too (observer/environment effect). Note load in the
                          baseline record.
                        - p95 from <20 runs is an interpolated estimate, not a
                          real 95th percentile. For rigor, see the
                          proof-and-analysis skill.

Stdlib only. Portable across Windows / macOS / Linux. Python 3.8+.

Examples:
  python3 timing_stats.py --runs 10 --warmup 2 -- git status
  python3 timing_stats.py --runs 5 -- python3 my_batch_job.py --input data.csv
  python3 timing_stats.py --runs 10 --json -- <TEST-CMD>
"""

import argparse
import json
import statistics
import subprocess
import sys
import time


def percentile(sorted_vals, p):
    """Linear-interpolated percentile, p in [0,100]. sorted_vals non-empty."""
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    frac = k - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def run_once(cmd, quiet):
    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )
    elapsed = time.perf_counter() - start
    return elapsed, proc.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Time a command over N runs; report min/median/p95/max. "
                    "Everything after '--' is the command to run.")
    ap.add_argument("--runs", type=int, default=10,
                    help="measured runs (default 10)")
    ap.add_argument("--warmup", type=int, default=1,
                    help="warmup runs discarded from stats (default 1)")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON instead of a table")
    ap.add_argument("--show-output", action="store_true",
                    help="let the command's stdout/stderr through "
                         "(default: suppressed so timings aren't I/O-skewed)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="command to run (prefix with --)")
    args = ap.parse_args(argv)

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        ap.error("no command given; usage: timing_stats.py [opts] -- CMD ...")
    if args.runs < 1:
        ap.error("--runs must be >= 1")

    quiet = not args.show_output

    for i in range(args.warmup):
        elapsed, rc = run_once(cmd, quiet)
        if not args.json:
            print(f"warmup {i + 1}/{args.warmup}: {elapsed:.4f}s (exit {rc})",
                  file=sys.stderr)

    times, exit_codes = [], []
    for i in range(args.runs):
        elapsed, rc = run_once(cmd, quiet)
        times.append(elapsed)
        exit_codes.append(rc)
        if not args.json:
            print(f"run {i + 1}/{args.runs}: {elapsed:.4f}s (exit {rc})",
                  file=sys.stderr)

    s = sorted(times)
    stats = {
        "command": cmd,
        "runs": args.runs,
        "warmup_discarded": args.warmup,
        "min_s": round(s[0], 6),
        "median_s": round(statistics.median(s), 6),
        "p95_s": round(percentile(s, 95), 6),
        "max_s": round(s[-1], 6),
        "mean_s": round(statistics.fmean(s), 6),
        "stdev_s": round(statistics.stdev(s), 6) if len(s) > 1 else 0.0,
        "nonzero_exits": sum(1 for c in exit_codes if c != 0),
    }

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print()
        print(f"command : {' '.join(cmd)}")
        print(f"runs    : {stats['runs']} (after {stats['warmup_discarded']} warmup)")
        print(f"min     : {stats['min_s']:.4f}s")
        print(f"median  : {stats['median_s']:.4f}s")
        print(f"p95     : {stats['p95_s']:.4f}s")
        print(f"max     : {stats['max_s']:.4f}s")
        print(f"mean    : {stats['mean_s']:.4f}s   stdev: {stats['stdev_s']:.4f}s")
        if stats["nonzero_exits"]:
            print(f"WARNING : {stats['nonzero_exits']} run(s) exited nonzero -- "
                  f"timings are suspect")
        if stats["median_s"] > 0 and stats["p95_s"] > 2 * stats["median_s"]:
            print("NOTE    : p95 > 2x median -- unstable tail; investigate "
                  "before quoting a single number")

    # exit 3 if any measured run failed, so CI can catch it
    return 3 if stats["nonzero_exits"] else 0


if __name__ == "__main__":
    sys.exit(main())
