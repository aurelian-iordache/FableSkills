#!/usr/bin/env python3
"""compare_runs.py -- mechanically diff two run outputs (text or JSON).

DIAGNOSTIC TOOL SPEC
  Question it answers : "Did the output of run B differ from run A, and where?"
  How to run          : python3 compare_runs.py A.json B.json [options]
                        python3 compare_runs.py A.txt  B.txt  [options]
  Interpretation      : exit 0 = no differences (within tolerance)
                        exit 1 = differences found (report on stdout)
                        exit 2 = usage / parse error
  Known blind spots   : - JSON mode ignores key ORDER (by design; use --text to
                          force byte-level comparison if order matters).
                        - Float tolerance (--rel-tol/--abs-tol) can mask a real
                          small regression; set tolerances deliberately.
                        - Does not follow file references inside the outputs.

Stdlib only. Portable across Windows / macOS / Linux. Python 3.8+.

Examples:
  python3 compare_runs.py baseline.json current.json
  python3 compare_runs.py baseline.json current.json --rel-tol 1e-6
  python3 compare_runs.py a.log b.log --text --ignore-regex '^\\d{4}-\\d{2}-\\d{2}'
  python3 compare_runs.py a.json b.json --report json
"""

import argparse
import difflib
import json
import math
import re
import sys

MAX_VALUE_REPR = 80  # truncate long values in the report


def _short(v):
    s = repr(v)
    return s if len(s) <= MAX_VALUE_REPR else s[: MAX_VALUE_REPR - 3] + "..."


def diff_json(a, b, path="$", *, rel_tol=0.0, abs_tol=0.0, out=None):
    """Recursively diff two parsed-JSON values. Appends dicts to `out`.

    Each finding: {"path": ..., "kind": added|removed|changed|type, "a":..., "b":...}
    """
    if out is None:
        out = []
    ta, tb = type(a), type(b)
    # bool is a subclass of int in Python; treat them as distinct JSON types.
    num = (int, float)
    a_is_num = isinstance(a, num) and not isinstance(a, bool)
    b_is_num = isinstance(b, num) and not isinstance(b, bool)

    if a_is_num and b_is_num:
        if not math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol):
            out.append({"path": path, "kind": "changed", "a": a, "b": b})
        return out
    if ta is not tb:
        out.append({"path": path, "kind": "type",
                    "a": ta.__name__, "b": tb.__name__})
        return out
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            p = f"{path}.{k}"
            if k not in b:
                out.append({"path": p, "kind": "removed", "a": _short(a[k]), "b": None})
            elif k not in a:
                out.append({"path": p, "kind": "added", "a": None, "b": _short(b[k])})
            else:
                diff_json(a[k], b[k], p, rel_tol=rel_tol, abs_tol=abs_tol, out=out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append({"path": f"{path}.length", "kind": "changed",
                        "a": len(a), "b": len(b)})
        for i in range(min(len(a), len(b))):
            diff_json(a[i], b[i], f"{path}[{i}]",
                      rel_tol=rel_tol, abs_tol=abs_tol, out=out)
    else:
        if a != b:
            out.append({"path": path, "kind": "changed",
                        "a": _short(a), "b": _short(b)})
    return out


def diff_text(lines_a, lines_b, ignore_regexes, max_show):
    """Line diff. Returns (findings, n_diff_lines). Ignored lines are blanked."""
    pats = [re.compile(p) for p in ignore_regexes]

    def norm(lines):
        return ["<IGNORED>" if any(p.search(ln) for p in pats) else ln
                for ln in lines]

    na, nb = norm(lines_a), norm(lines_b)
    delta = [d for d in difflib.unified_diff(na, nb, "A", "B", lineterm="", n=0)]
    changed = [d for d in delta if d[:1] in "+-" and d[:3] not in ("+++", "---")]
    return delta[:max_show + 2], len(changed)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Diff two run outputs (JSON-aware by default when both "
                    "files parse as JSON; otherwise line diff).")
    ap.add_argument("file_a", help="baseline / reference output")
    ap.add_argument("file_b", help="candidate / current output")
    ap.add_argument("--text", action="store_true",
                    help="force line-diff mode even if inputs parse as JSON")
    ap.add_argument("--rel-tol", type=float, default=0.0,
                    help="relative tolerance for numeric JSON values (default 0)")
    ap.add_argument("--abs-tol", type=float, default=0.0,
                    help="absolute tolerance for numeric JSON values (default 0)")
    ap.add_argument("--ignore-regex", action="append", default=[],
                    metavar="RE", help="text mode: lines matching RE are "
                    "normalized before diffing (repeatable; e.g. timestamps)")
    ap.add_argument("--max-show", type=int, default=40,
                    help="max findings/diff lines to print (default 40)")
    ap.add_argument("--report", choices=["human", "json"], default="human",
                    help="report format (default human)")
    args = ap.parse_args(argv)

    try:
        with open(args.file_a, "r", encoding="utf-8", errors="replace") as f:
            raw_a = f.read()
        with open(args.file_b, "r", encoding="utf-8", errors="replace") as f:
            raw_b = f.read()
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    json_a = json_b = None
    if not args.text:
        try:
            json_a = json.loads(raw_a)
            json_b = json.loads(raw_b)
        except ValueError:
            json_a = json_b = None  # fall through to text mode

    if json_a is not None:
        findings = diff_json(json_a, json_b,
                             rel_tol=args.rel_tol, abs_tol=args.abs_tol)
        if args.report == "json":
            print(json.dumps({"mode": "json", "identical": not findings,
                              "n_differences": len(findings),
                              "differences": findings[:args.max_show]},
                             indent=2))
        else:
            if not findings:
                print(f"IDENTICAL (json mode, rel_tol={args.rel_tol}, "
                      f"abs_tol={args.abs_tol})")
            else:
                print(f"DIFFERENT (json mode): {len(findings)} difference(s)")
                for d in findings[:args.max_show]:
                    print(f"  [{d['kind']:>7}] {d['path']}: "
                          f"A={d['a']!r}  B={d['b']!r}")
                if len(findings) > args.max_show:
                    print(f"  ... {len(findings) - args.max_show} more "
                          f"(raise --max-show)")
        return 1 if findings else 0

    # text mode
    shown, n_changed = diff_text(raw_a.splitlines(), raw_b.splitlines(),
                                 args.ignore_regex, args.max_show)
    if args.report == "json":
        print(json.dumps({"mode": "text", "identical": n_changed == 0,
                          "n_changed_lines": n_changed,
                          "diff_head": shown}, indent=2))
    else:
        if n_changed == 0:
            print(f"IDENTICAL (text mode, "
                  f"{len(args.ignore_regex)} ignore pattern(s))")
        else:
            print(f"DIFFERENT (text mode): {n_changed} changed line(s)")
            for line in shown:
                print("  " + line)
    return 1 if n_changed else 0


if __name__ == "__main__":
    sys.exit(main())
