---
name: failure-archaeology
description: Load when you need to know whether a bug, regression, or design battle has been fought before — before starting any non-trivial investigation (to check whether it was fought before; for the live diagnosis itself, use debugging-playbook), when a fix feels familiar, when someone proposes retrying an approach that "didn't work last time", when writing up a closed investigation or a revert, or when asked to "check the history", "why was this reverted", "have we seen this before", or "build/update the incident chronicle". Delivers the chronicle entry format (symptom → root cause → evidence → status), rules of evidence, a verified git-history mining toolkit, and a runnable miner script that surfaces candidate incidents from any repo.
---

# Failure Archaeology

## Purpose

Turn a repo's git history and issue artifacts into a **chronicle**: a durable record of
every significant investigation — symptom, root cause, evidence, status — plus every dead
end, so no one (human or model) re-fights a settled battle or retries a known-failed
approach without knowing why it failed. Also: the toolkit for excavating that record from
raw history when nobody wrote it down at the time.

## When to use / When NOT to use

Use this skill when:

- Starting any investigation that smells non-trivial — **check the chronicle first**.
- Closing an investigation, landing a revert, or abandoning an approach — **write the entry now**.
- Onboarding to an unfamiliar repo and needing its scar tissue fast (run the miner script).
- Someone proposes an approach and you suspect it was tried and rejected before.

Do NOT use this skill for:

| If instead you need... | Use sibling skill |
|---|---|
| Live triage of a current symptom (symptom→check tables) | `debugging-playbook` |
| Rules for what changes need what gating, and the non-negotiables list | `change-control` |
| Recording design decisions and invariants (not failures) | `architecture-contract` |
| Evidence standards for tests/benchmarks going forward | `validation-and-qa` |
| Running a structured campaign on a live hard problem | `campaign-design` |
| Instantiating this whole library for a specific repo | `skill-factory` |

Boundary rule: the chronicle records the **past** (what happened, what was concluded).
`debugging-playbook` consumes it for present triage; `change-control` consumes it for
future gating. One home per fact: the incident story lives HERE; siblings link to entry IDs.

## Core doctrine

### 1. The chronicle

One file per project, e.g. `docs/CHRONICLE.md` (location is a project choice; record it in
the instantiated skill). Entries are append-mostly: you may update `Status` and add
evidence, but never delete or rewrite history — supersede instead (see status vocabulary).

**Entry format** (copy this template verbatim):

```markdown
## FA-<NNN>: <one-line title, symptom-first>          <!-- FA = Failure Archaeology -->
- **Date opened / closed:** YYYY-MM-DD / YYYY-MM-DD
- **Symptom:** What was observed, by whom/what, under what conditions. Verbatim error
  text or measured numbers, not paraphrase.
- **Root cause:** The mechanism, one level deeper than the patch. "Off-by-one in X"
  is a patch description; "X assumed closed interval, caller passed half-open" is a cause.
  Write `UNKNOWN` if never established — that is valuable information.
- **Evidence:** Commits / issues / repro logs. See rules of evidence below. NO ENTRY
  WITHOUT AT LEAST ONE CITATION.
- **Status:** fixed | mitigated | wontfix | open | superseded (vocabulary below)
- **Fix / mitigation:** Commit(s) that resolved it, or the standing workaround.
- **Dead ends:** (optional but high-value) See dead-end format below.
- **Feeds:** (optional) Links: triage row added to debugging playbook? Non-negotiable
  added to change control? e.g. "→ debugging-playbook row 'stale reads after deploy'".
```

**Status vocabulary** — exactly these five, no synonyms:

| Status | Meaning | Required extras |
|---|---|---|
| `fixed` | Root cause removed; a test or check guards the regression | Fix commit; guard (test name/CI check) if one exists |
| `mitigated` | Symptom suppressed, cause still present | The standing workaround AND what would remove the cause |
| `wontfix` | Deliberately not fixing | The rationale and who decided (commit/issue where decided) |
| `open` | Unresolved; investigation parked or ongoing | Last known state; what would unblock it |
| `superseded` | Overtaken by events (component deleted, redesigned) | Link to the entry/ADR/commit that supersedes it |

**Dead-end format** — the single highest-value record type, because dead ends are
invisible in shipped code:

```markdown
- **Dead end:** We tried <X>. It failed because <Y — mechanism, with evidence citation>.
  Do not retry unless <Z — the specific condition that would invalidate Y>.
```

The `unless Z` clause is mandatory. A dead end without an unblock condition becomes
superstition ("we don't do that here"); with one, it is an executable decision rule.
Illustrative example: "We tried caching parse results in-process. Failed because worker
processes are recycled every ~50 requests, so hit rate was <2% (repro log in issue #88).
Do not retry unless worker lifetime exceeds ~10k requests or the cache moves out-of-process."

### 2. Rules of evidence

An entry cites artifacts, **never memory**. Memory is how battles get re-fought.

1. **Admissible citations:** commit SHAs (full or ≥9 chars), issue/PR numbers with tracker
   name, repro logs checked into the repo or attached to an issue, CI run URLs.
   "I remember" and "someone said" are inadmissible — if that's all you have, either
   excavate the artifact with the toolkit below, or mark the claim `(uncorroborated)`
   and set status `open`.
2. **Symptom evidence and cause evidence are different obligations.** The symptom cite
   proves it happened (error log, failing CI run). The cause cite proves the mechanism
   (the diff of the fix, a repro script, a bisect result). An entry can have the first
   without the second — then root cause stays `UNKNOWN`.
3. **Numbers over adjectives.** "Slow" is not evidence; "p99 went 40ms → 900ms in run
   <URL>" is. If the original numbers are lost, say so.
4. **A revert is first-class evidence.** The revert commit proves the attempt failed in
   practice; cite both the revert and the original (see interviewing history, below).
5. **Uncertainty is recorded, not smoothed over.** "Probably", "we believe", `UNKNOWN`
   are all legal in entries. A confident wrong entry is worse than an honest gap.

### 3. GIT-HISTORY MINING toolkit

All commands below are real, verified `git` syntax (git 2.52; all long-stable). Run them
from the repo root. `<MAIN-BRANCH>` is your default branch (`main`, `master`, ...).

**Find reverts** — every revert marks a battle somebody lost:

```sh
git log --all -i --grep=revert --format="%h %ad %s" --date=short
```

`-i` makes the subject match case-insensitive; `--all` includes all branches. Note:
squash-merge workflows can bury reverts inside squashed PRs — also search PR titles in
your forge (`gh pr list --search "revert" --state merged` if using GitHub).

**Find fix-of-a-fix chains** — repeated fixes to one file mean the first root-cause call
was wrong, or the area is structurally fragile:

```sh
# fix-flavored commits touching one suspicious file (path applies to old name too if renamed):
git log --oneline -i --grep=fix -- <PATH>
# repo-wide, automated: use scripts/mine_incidents.py (section below)
```

Read chains oldest-first and ask: did the last fix actually close it, or did the thread
just go cold?

**Pickaxe: find when a string appeared or disappeared** (`-S`) vs **when matching lines
changed** (`-G`):

```sh
git log -S"retry_count" --oneline          # commits where the COUNT of occurrences changed
git log -G"TTL\s*=\s*[0-9]+" --oneline     # commits whose diff has a line matching the regex
```

Critical distinction, verified: `-S` finds only commits that add or remove occurrences —
a commit changing `TTL = 30` to `TTL = 300` is invisible to `-S"TTL"` (count unchanged)
but found by `-G"TTL = [0-9]+"`. Use `-S` for "when was this introduced/deleted",
`-G` for "show me every edit to this kind of line". Add `-p` to either to see the diffs,
and `--all` to search unmerged branches.

**Trace a file through renames:**

```sh
git log --follow --oneline -- <CURRENT-PATH>
```

Caveat (verified): `--follow` only walks newest→oldest, so `--reverse --follow` gives
wrong results. To find a file's true first commit: `git log --follow --oneline -- <PATH> | tail -1`.

**Find abandoned branches** — parked experiments and failed campaigns:

```sh
git branch -a --no-merged <MAIN-BRANCH>                  # branches never merged
git log --all --since="6 months ago" --oneline           # recent activity anywhere
# last activity date per unmerged branch:
for b in $(git branch -a --no-merged <MAIN-BRANCH> --format='%(refname:short)'); do
  git log -1 --format="%ad  $b  %s" --date=short "$b"
done
```

An unmerged branch named `experiment/*` or `spike/*` with no chronicle entry is an
undocumented dead end — excavate it or interview its author while they're still reachable.

**See through refactors with blame:**

```sh
git blame -w -C -- <PATH>          # -w: ignore whitespace; -C: detect code moved within/between files
git blame -w -C -C -C -- <PATH>    # more -C = more aggressive cross-file copy detection (slower)
git blame -L 40,60 -w -C -- <PATH> # only lines 40-60
```

Plain `git blame` shows the last formatter run or file-move; `-w -C` digs to the commit
that actually wrote the logic. When blame lands on a "refactor:" commit anyway, blame the
file at the parent of that commit: `git blame -w -C <SHA>^ -- <OLD-PATH>`.

**High-churn files** — trouble-spot heuristic (config files and lockfiles churn innocently):

```sh
git log --format= --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -20
```

### 4. How to interview history

A revert found by the toolkit is a witness. Interrogate it — always read the **pair**:

1. `git show --no-patch <REVERT-SHA>` — a well-formed revert message contains
   `This reverts commit <ORIGINAL-SHA>.` plus (if the author was disciplined) *why*.
   The revert message tells you **what broke in practice**.
2. `git show <ORIGINAL-SHA>` — the original message tells you **what was being attempted
   and why it seemed right**. The diff shows the mechanism.
3. Cross-examine: search the tracker for the revert's date ±3 days and any incident/issue
   ID in either message. `git log --oneline --since=<DATE> --until=<DATE+7days>` shows
   what landed immediately after — often the "real" fix.
4. Verdict: the pair yields a complete dead-end record — X = original's intent,
   Y = revert's reason, Z = whatever condition the revert message implies. If the revert
   message is empty ("Revert 'foo'" and nothing else), Y is `UNKNOWN`; write the entry
   anyway with status `open` and flag it for author interview.

The same pattern applies to fix chains: read fix N and fix N+1 together; the second
message usually names what the first got wrong (that sentence is your root-cause evidence).

### 5. Maintenance cadence — when entries get written

Entries decay from "5-minute write-up" to "half-day excavation" within weeks. Write them
at these trigger points, not "later":

| Trigger | Obligation | Latency budget |
|---|---|---|
| Investigation closes (cause found or search abandoned) | Full entry | Same day |
| A revert lands | Entry (or update) citing revert + original pair | With the revert PR |
| An approach is abandoned mid-flight (branch parked, spike ends) | Dead-end record, `unless Z` filled in | Before switching tasks |
| A `mitigated` workaround becomes load-bearing (>1 month old) | Re-review entry; escalate or re-status | Monthly sweep |
| Onboarding to a repo with no chronicle | Run miner script, triage output into seed entries | First week |
| Quarterly | Sweep `open` entries: still true? superseded? | Quarterly |

Candidate practice (judgment call, not proven): make "chronicle entry written or
explicitly waived" a PR-template checkbox for any PR containing a revert or a
`fix:`-of-a-`fix:` — cheap to add, and it moves the write to the moment of maximum context.

### 6. Feeding the siblings

The chronicle is upstream of two consumers; every closed entry should be checked against both:

- **→ `debugging-playbook` triage rows.** If the symptom could plausibly recur, distill
  the entry into a row: symptom pattern → discriminating check → likely cause → entry ID.
  The playbook row is the cache; the chronicle entry is the source of truth. Never put
  the full story in the playbook.
- **→ `change-control` non-negotiables.** If the root cause was "a class of change that
  must never happen casually" (e.g. "changing serialization defaults broke rolling
  deploys"), propose a non-negotiable citing the entry ID as the incident-behind-the-rule.
  Change-control rules without a chronicle citation are folklore; with one, they are
  auditable and can be retired when `Z` changes.

### 7. The miner script

`scripts/mine_incidents.py` (ships with this skill) scans any repo read-only and emits a
Markdown candidate-incidents report: reverts paired with their originals, files with ≥2
fix-commits (chains), and high-churn files. Python 3.7+, git on PATH, no third-party
packages.

```sh
python3 scripts/mine_incidents.py --repo <PATH-TO-REPO> [--since "2 years ago"] [--top 15] [--min-chain 2]
```

On Windows without a `python3` alias, use `py` in place of `python3` (applies to every
miner invocation in this skill).

Its output is **candidates only** — every item still needs the interview step (section 4)
and rules of evidence (section 2) before it becomes a chronicle entry. Known limits:
subject-keyword matching misses fixes not labeled `fix`/`hotfix`/etc.; squash merges can
hide reverts; churn counts include innocent files.

### 8. Failure modes of the method itself

- **Chronicle-as-blame.** Entries name mechanisms, not people. Author names appear only
  as "who to interview", never as "who caused it" — or people stop writing entries.
- **Entry inflation.** Not every bug deserves an entry. Threshold heuristic: >2 hours of
  investigation, OR a revert, OR a dead end someone might retry, OR a recurrence.
- **Stale dead ends blocking progress.** Dead ends with a good `unless Z` self-expire;
  audit any dead end older than a year whose Z can no longer be evaluated.
- **Chronicle nobody reads.** If entries don't feed playbook rows and non-negotiables
  (section 6), the chronicle is a diary. The `Feeds:` field exists to force the question.

## Worked example

**Illustrative example — all names, SHAs, and numbers fictional.**

Project "Quillhaven" (a document-indexing service). New maintainer runs the miner:

```sh
python3 scripts/mine_incidents.py --repo ~/src/quillhaven --since "2 years ago"
```

Report shows: 1 revert (`9f3ab21c4 Revert "perf: mmap the token dictionary"`), a 3-commit
fix chain on `indexer/segment_merge.py`, and `segment_merge.py` also #1 in churn (41 commits).

Interview the revert pair:

```sh
git show --no-patch 9f3ab21c4
#   This reverts commit 4c11d0e9a.
#   mmap'd dict caused SIGBUS on NFS-mounted data dirs (INC-207).
git show 4c11d0e9a --stat
#   perf: mmap the token dictionary -- cuts index-open p50 from 130ms to 9ms
```

Both messages cite what's needed. Resulting entry:

```markdown
## FA-014: SIGBUS crashes on index open (NFS deployments)
- **Date opened / closed:** 2025-11-03 / 2025-11-05
- **Symptom:** indexer workers crash with SIGBUS opening indexes on NFS-mounted
  data dirs; ~90 crashes/hr fleet-wide during INC-207.
- **Root cause:** token dictionary was mmap'd (4c11d0e9a); NFS servers may truncate
  files under the reader, and mmap turns that into SIGBUS rather than a read error.
- **Evidence:** revert 9f3ab21c4; original 4c11d0e9a; incident INC-207.
- **Status:** fixed (by revert; perf win forfeited)
- **Fix / mitigation:** revert 9f3ab21c4.
- **Dead ends:** We tried mmap-ing the token dictionary. It failed because NFS
  truncation under a live mapping raises SIGBUS (INC-207 crash logs). Do not retry
  unless NFS deployments are dropped from the support matrix, or dictionaries move
  to immutable content-addressed files that are never truncated in place.
- **Feeds:** → debugging-playbook row "SIGBUS in indexer" ; → change-control
  non-negotiable "no mmap on files that can be replaced in place (FA-014)".
```

Total cost: ~20 minutes. The next engineer who "discovers" the mmap optimization finds
FA-014 in one grep — and also finds the exact conditions under which it becomes viable again.

## Instantiate for your project

Produce `.claude/skills/<PROJECT>-failure-archaeology/SKILL.md` in the target repo.
Executable by a Sonnet-class model without human help:

1. **Mine.** From the repo root, run (read-only):
   ```sh
   python3 <PATH-TO-THIS-SKILL>/scripts/mine_incidents.py --repo . --since "3 years ago" > <SCRATCH-DIR>/candidates.md
   git branch -a --no-merged <MAIN-BRANCH>
   git log --all -i --grep=revert --format="%h %ad %s" --date=short
   ```
   (`<SCRATCH-DIR>` = any writable temp directory.)
   Also list existing artifacts: `ls docs/ *.md`, search for prior art
   (`grep -rilE "post.?mortem|incident|known issue" docs/ README* 2>/dev/null`), and
   check the tracker for labels like `regression`, `incident`, `wontfix`.
2. **Choose the chronicle home.** If a postmortem/known-issues doc already exists, the
   chronicle extends it (do not create a competing file). Otherwise create
   `docs/CHRONICLE.md` with the entry template from Core doctrine §1 at the top.
3. **Seed entries from evidence only.** For each revert and fix chain in the miner
   output: run the interview procedure (Core doctrine §4), then write an entry.
   **Evidence gate: do not write an entry — and especially not a root cause or dead
   end — that you cannot cite to a commit, issue, or log you actually opened.** If the
   artifacts don't establish the cause, write the entry with `Root cause: UNKNOWN` and
   status `open`. Expect 3–10 seed entries in a mature repo; zero is a finding too
   (say so in the instantiated skill).
4. **Fill the project skill from this skeleton:**
   ```markdown
   ---
   name: <PROJECT>-failure-archaeology
   description: <triggers, naming this project's components and recurring symptom words>
   ---
   # <PROJECT> Failure Archaeology
   ## Chronicle location and status vocabulary   <!-- link file; restate the 5 statuses -->
   ## How to search it                            <!-- grep patterns, entry ID scheme -->
   ## Seed entries summary                        <!-- table: ID | title | status -->
   ## Project-specific mining notes               <!-- e.g. "history rewritten at <SHA>,
                                                       pre-2024 SHAs are dead", squash-merge
                                                       policy, tracker URL conventions -->
   ## Cadence owners                              <!-- who/what runs the monthly + quarterly sweeps -->
   ## Provenance                                  <!-- date, method: "seeded from miner run <DATE>,
                                                       N candidates triaged, M entries written" -->
   ```
5. **Wire the consumers.** For each seed entry, decide: playbook row? (add it via
   `debugging-playbook`'s instantiation) non-negotiable? (propose via `change-control`).
   Record the decision in the entry's `Feeds:` field, including explicit "feeds: none".
6. **Verify.** Check that every entry ID is unique, every entry has ≥1 citation, every
   dead end has an `unless Z`, and every status is one of the five vocabulary words.
   A reviewer (or second model pass) should spot-check 2 entries by re-opening their
   cited commits.

## Provenance and maintenance

- Authored 2026-07-06 against no specific project. All git commands verified against
  git 2.52.0 on a purpose-built test repo containing reverts, fix chains, a rename, and
  an unmerged branch; `mine_incidents.py` was run against that repo and its output
  inspected (reverts paired correctly, chains ordered oldest-first, churn ranked).
- Volatile parts and re-verification one-liners:
  - git flag behavior (`-S`/`-G`, `--follow`, `blame -C`): `git log --help` and
    `git blame --help` in the target environment.
  - `--no-merged` / `--format` on `git branch`: `git branch --help`.
  - `gh pr list --search` syntax: `gh pr list --help` (gh CLI evolves faster than git).
  - Miner script: rerun `python3 scripts/mine_incidents.py --repo <ANY-GIT-REPO>` (`py` on Windows) and
    confirm sections 1–3 render; it uses only `git log`/`git show`/`git rev-parse`.
- The entry format, status vocabulary, and cadence table are method content (stable);
  the PR-checkbox idea is labeled candidate practice and should be validated per project.
- Instantiated copies must add their own provenance: date, miner-run date, candidate
  count vs. entries written, and which entries are seeded-from-history vs. witnessed live.
