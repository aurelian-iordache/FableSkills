#!/usr/bin/env python3
"""mine_incidents.py -- mine a git repo's history for candidate chronicle entries.

Scans git history and emits a Markdown "candidate incidents" report on stdout:

  1. REVERTS        -- every revert commit, paired with the commit it reverts.
  2. FIX CHAINS     -- files touched by 2+ commits whose subject starts with a
                       fix-like keyword (fix/bugfix/hotfix/repair/correct) --
                       a fix-of-a-fix smell worth investigating.
  3. HIGH-CHURN     -- files with the most commits overall; churn correlates
                       with trouble spots (heuristic, not proof).

Each finding is a CANDIDATE only: a human (or model) must read the commits and
write a real chronicle entry (symptom -> root cause -> evidence -> status).

Usage:
    python mine_incidents.py [--repo PATH] [--since DATE] [--top N] [--min-chain N]

    --repo PATH     path to the git repo (default: current directory)
    --since DATE    limit history, e.g. "2 years ago" or 2024-01-01 (default: all)
    --top N         how many high-churn files to list (default: 15)
    --min-chain N   minimum fix-commits on one file to report a chain (default: 2)

Requires: Python 3.7+, git on PATH. No third-party packages. Read-only:
runs only `git log` / `git show`; never mutates the repo.
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict

FIX_SUBJECT_RE = re.compile(r"^(fix|bugfix|hotfix|repair|correct)\b", re.IGNORECASE)
REVERTS_SHA_RE = re.compile(r"This reverts commit ([0-9a-f]{7,40})", re.IGNORECASE)
FIELD_SEP = "\x1f"   # unit separator: safe against | or ; in subjects
REC_SEP = "\x1e"     # record separator between commits


def run_git(repo, args):
    """Run a read-only git command; return stdout as text ('' on failure)."""
    cmd = ["git", "-C", repo] + args
    try:
        out = subprocess.run(
            cmd, capture_output=True, timeout=300
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write("error running %s: %s\n" % (" ".join(cmd), exc))
        return ""
    if out.returncode != 0:
        sys.stderr.write(out.stderr.decode("utf-8", "replace"))
        return ""
    return out.stdout.decode("utf-8", "replace")


def load_commits(repo, since):
    """Return list of dicts: sha, date, author, subject, body, files."""
    # REC_SEP leads each record (git prints --name-only file lists AFTER the
    # formatted message, so a trailing separator would split in the wrong
    # place). The trailing FIELD_SEP fences the body off from the file list.
    fmt = REC_SEP + FIELD_SEP.join(["%H", "%aI", "%an", "%s", "%b"]) + FIELD_SEP
    args = ["log", "--all", "--name-only", "--format=" + fmt]
    if since:
        args.append("--since=" + since)
    raw = run_git(repo, args)
    commits = []
    for chunk in raw.split(REC_SEP):
        if not chunk.strip():
            continue
        parts = chunk.split(FIELD_SEP)
        if len(parts) < 6:
            continue
        sha, ts, author, subject = parts[0].strip(), parts[1], parts[2], parts[3]
        body = parts[4].strip()
        files = [ln.strip() for ln in parts[5].split("\n") if ln.strip()]
        commits.append(
            {
                "sha": sha,
                "ts": ts,            # full ISO timestamp, used for ordering
                "date": ts[:10],     # YYYY-MM-DD, used for display
                "author": author,
                "subject": subject,
                "body": body,
                "files": files,
            }
        )
    commits.reverse()  # oldest first, so stable sorts break timestamp ties correctly
    return commits


def subject_of(repo, sha):
    s = run_git(repo, ["show", "--no-patch", "--format=%s", sha]).strip()
    return s or "(commit not found -- may be from a rebased/rewritten branch)"


def find_reverts(repo, commits):
    """Yield (revert_commit, reverted_sha, reverted_subject)."""
    out = []
    for c in commits:
        text = c["subject"] + "\n" + c["body"]
        if not re.search(r"\brevert", text, re.IGNORECASE):
            continue
        m = REVERTS_SHA_RE.search(text)
        reverted_sha = m.group(1) if m else None
        reverted_subject = subject_of(repo, reverted_sha) if reverted_sha else "(no 'This reverts commit' line found)"
        out.append((c, reverted_sha, reverted_subject))
    return out


def find_fix_chains(commits, min_chain):
    """Return {file: [fix commits oldest->newest]} for files with >= min_chain fixes."""
    per_file = defaultdict(list)
    for c in commits:
        if FIX_SUBJECT_RE.search(c["subject"]):
            for f in c["files"]:
                per_file[f].append(c)
    chains = {}
    for f, cs in per_file.items():
        if len(cs) >= min_chain:
            chains[f] = sorted(cs, key=lambda c: c["ts"])
    return chains


def churn(commits, top):
    counts = defaultdict(int)
    for c in commits:
        for f in c["files"]:
            counts[f] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:top]


def short(sha):
    return sha[:9]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".", help="path to git repo (default: cwd)")
    ap.add_argument("--since", default=None, help='e.g. "2 years ago" or 2024-01-01')
    ap.add_argument("--top", type=int, default=15, help="high-churn files to list")
    ap.add_argument("--min-chain", type=int, default=2, help="min fixes per file to flag a chain")
    args = ap.parse_args()

    if not run_git(args.repo, ["rev-parse", "--git-dir"]).strip():
        sys.stderr.write("error: %s is not a git repository\n" % args.repo)
        return 2

    commits = load_commits(args.repo, args.since)
    if not commits:
        sys.stderr.write("no commits found (check --since / repo path)\n")
        return 1

    w = sys.stdout.write
    w("# Candidate incidents report\n\n")
    w("Repo: `%s`  |  commits scanned: %d  |  since: %s\n\n"
      % (args.repo, len(commits), args.since or "beginning of history"))
    w("Every item below is a CANDIDATE chronicle entry. Read the commits, then "
      "write a real entry (symptom -> root cause -> evidence -> status) or "
      "discard with a reason.\n\n")

    # --- reverts ---
    reverts = find_reverts(args.repo, commits)
    w("## 1. Reverts (%d)\n\n" % len(reverts))
    if reverts:
        w("| revert commit | date | reverts | original subject |\n")
        w("|---|---|---|---|\n")
        for c, rsha, rsubj in reverts:
            w("| %s %s | %s | %s | %s |\n"
              % (short(c["sha"]), c["subject"].replace("|", "\\|")[:60],
                 c["date"], short(rsha) if rsha else "?",
                 rsubj.replace("|", "\\|")[:60]))
        w("\nFor each row run: `git show <revert> ; git show <original>` and "
          "read both messages together -- the revert says what broke, the "
          "original says what was attempted.\n")
    else:
        w("None found. (Squash-merge workflows can hide reverts; also grep PR titles.)\n")
    w("\n")

    # --- fix chains ---
    chains = find_fix_chains(commits, args.min_chain)
    w("## 2. Fix chains -- files with >= %d fix-commits (%d files)\n\n"
      % (args.min_chain, len(chains)))
    if chains:
        for f in sorted(chains, key=lambda f: -len(chains[f])):
            w("### `%s` -- %d fix commits\n\n" % (f, len(chains[f])))
            for c in chains[f]:
                w("- %s %s  %s\n" % (c["date"], short(c["sha"]),
                                     c["subject"].replace("|", "\\|")))
            w("\n")
        w("A chain of fixes on one file often means the first root-cause call "
          "was wrong. Read the chain oldest-first and ask: did the last fix "
          "actually close it?\n")
    else:
        w("None at this threshold. Try --min-chain 1 or a wider --since.\n")
    w("\n")

    # --- churn ---
    ranked = churn(commits, args.top)
    w("## 3. High-churn files (top %d)\n\n" % args.top)
    w("| commits | file |\n|---|---|\n")
    for f, n in ranked:
        w("| %d | `%s` |\n" % (n, f))
    w("\nChurn is a heuristic: config files and lockfiles churn innocently. "
      "Cross-reference with sections 1-2 before investigating.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
