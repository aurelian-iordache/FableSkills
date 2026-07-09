---
name: docs-and-writing
description: Load when creating, updating, auditing, or reorganizing project documentation — READMEs, runbooks, reference docs, onboarding guides, wikis — or when the user says docs are "stale", "wrong", "duplicated", "scattered", or asks "where should this be documented?" or "write this up". Delivers the doc-of-record discipline (one home per fact), a doc taxonomy with per-type verification rules, rot-detection commands, runbook house style, and copy-paste templates for runbooks, ADR pointers, incident writeups, and READMEs.
---

# docs-and-writing — Maintaining Docs of Record

## Purpose

Keep a project's documentation TRUE, not merely present. This skill gives you: the
one-home-per-fact rule for deciding where information lives, per-doc-type verification
rules so every doc has a defined way to be proven correct, rot-detection commands to find
stale docs mechanically, and templates plus house style so new docs are consistent and
maintainable from day one.

## When to use / When NOT to use

Use when:
- Writing or restructuring any project doc (README, runbook, reference, onboarding guide).
- Auditing existing docs for staleness, duplication, or dead references.
- Deciding WHERE a new piece of knowledge should be recorded.
- Closing an investigation, making a decision, or finishing onboarding — the three
  moments when a doc must be written (see "Write-at-the-moment rule").

Do NOT use for:

| If instead you need... | Use sibling skill |
|---|---|
| Recording an architectural decision and its WHY (ADR content) | architecture-contract |
| Writing up a completed investigation (root cause, evidence) | failure-archaeology |
| Authoring domain-theory background (math, protocols, standards) | domain-reference |
| An environment-setup runbook's *content* and clean-room proof | build-and-env |
| A run/deploy runbook's *content* and safety rails | run-and-operate |
| Cataloging config options and flags | config-and-flags |
| Instantiating this whole skill library for a repo | skill-factory |

This skill owns the doc SYSTEM — where docs live, how they are styled, how they are kept
true. Sibling skills own the content of their specialty docs; this skill tells you where
that content's single home is and how to keep it from rotting.

## Core doctrine

### 1. DOC-OF-RECORD: one home per fact

**Definition:** A *doc of record* is the single authoritative location for a given fact.
Every fact has exactly one home. Every other place that needs the fact LINKS to the home;
it never restates it.

Why this is the load-bearing rule: duplicated facts drift independently. The copy that is
wrong is indistinguishable from the copy that is right, so readers trust neither and stop
reading docs at all. One home means one place to update and one place to verify.

Operating rules:

| Situation | Rule |
|---|---|
| You need a fact in two docs | State it in one; link from the other ("Port list: see `docs/reference/ports.md`"). |
| You find the same fact stated twice | Pick the home (the one closer to the source of truth), replace the other with a link, note the merge in the commit message. |
| Two docs disagree | Neither is trusted until re-verified. Verify against source/execution (see taxonomy below), fix the home, link-ify the other. |
| A fact is derivable from code/config | Prefer linking to the code (`see <CONFIG-FILE>`) over restating values that will drift. Restate only if readers cannot practically read the source, and add a re-verify command. |
| Deciding which doc is the home | The home is the doc whose verification rule can actually check the fact (a port number belongs in reference verified against config, not in a tutorial). |

Heuristic for granularity: a "fact" is anything that can independently become false — a
port number, a command, a threshold, a directory layout, a decision rationale.

### 2. Doc taxonomy — four types, four verification rules

Every doc must declare its type, because the type determines HOW it is verified. A doc
with no verification rule is an opinion, not a doc of record.

| Type | Answers | Verified by | Rots when | Typical location |
|---|---|---|---|---|
| **Runbook** (how-to, procedure) | "How do I do X?" | **Execution** — someone runs every step top-to-bottom and gets the stated outputs | Commands, flags, paths, or outputs change | `docs/runbooks/` |
| **Reference** (facts, catalogs) | "What is the value of X?" | **Against source** — each fact checked against the code/config/API it describes, ideally by a one-line command | The source changes | `docs/reference/` |
| **Explanation** (why-docs, design notes) | "Why is X this way?" | **Against decisions** — cross-checked with the ADR log (see architecture-contract); still true if the decision stands, superseded if a newer ADR replaced it | A new decision supersedes the old one | `docs/design/` or ADR log |
| **Onboarding** (guides, tutorials) | "How do I get productive?" | **By a newcomer** — the next new person follows it literally and logs every point where they got stuck | Anything upstream changes; rots fastest of all four | `docs/onboarding/` |

Consequences of the taxonomy:
- Do not mix types in one doc. A runbook that drifts into explaining architecture now has
  two verification rules and will satisfy neither. Link out instead ("Why we deploy
  blue/green: see ADR-0012").
- "Verified" means the type's rule was actually applied, and the doc's provenance line
  (next section) was updated. Reading a doc and nodding is not verification.
- Onboarding docs get a standing instruction at the top: *"If any step fails or confuses
  you, you have found a doc bug. File it / fix it before continuing."* Newcomer friction
  is the test suite for onboarding docs — capture it or lose it.

### 3. ROT DETECTION — provenance lines and mechanical audits

**Provenance line:** every doc of record carries, near the top:

```
Last verified: <YYYY-MM-DD> — <HOW>
Re-verify: <one-line command or one-sentence procedure>
```

Illustrative example:

```
Last verified: 2026-07-06 — ran all steps on a fresh checkout, all outputs matched
Re-verify: follow steps 1-9 end-to-end on a clean clone; step 9 must print "OK (42 tests)"
```

The `Re-verify` line is the contract: anyone (including a model) can re-earn the date
without archaeology. If you cannot write a one-line re-verification, the doc is too big
or too vague — split it.

**Finding rotten docs mechanically.** Run these during any docs audit (quarterly, or
before a release, or when a newcomer arrives). All commands are POSIX sh + git, run from
the repo root; adjust the docs path to your layout.

Six checks. Each: run the command (fenced so it copy-pastes cleanly from raw Markdown),
then apply the interpretation.

**1. Docs with no provenance line** — listed files have never been verified. Triage:
verify or delete.

```sh
grep -rL "Last verified:" docs --include="*.md"
```

**2. Date audit — oldest last-touched docs** — top of the list = longest untouched.
Untouched ≠ wrong, but it is where to look first.

```sh
git ls-files 'docs/*.md' 'docs/**/*.md' | while read -r f; do printf '%s  %s\n' "$(git log -1 --format=%cs -- "$f")" "$f"; done | sort
```

**3. Dead file paths referenced in docs** — every `DEAD:` line is a doc pointing at a
file that no longer exists. (Expect some false positives: URLs, illustrative names —
eyeball the list.)

```sh
grep -rEho '\b[A-Za-z0-9_./-]+\.(md|py|sh|cs|ts|yml|yaml|json|toml)\b' docs/ | sort -u | while read -r p; do [ -e "$p" ] || echo "DEAD: $p"; done
```

**4. Docs mentioning deleted files** — docs that reference paths git has ever deleted.
Noisy on old repos; scope with `--since=6.months`.

```sh
git log --diff-filter=D --name-only --format= | sort -u | while read -r p; do grep -rlF "$p" docs/ 2>/dev/null; done | sort -u
```

**5. Dead commands in runbooks** — extract each fenced command block and run it (or at
minimum `command -v` the binary and check `--help` for the flags used). A runbook whose
first command fails is worse than no runbook — readers stop trusting the rest.

**6. Stale provenance dates** — manually flag anything older than your rot budget
(heuristic: 90 days for runbooks/onboarding, 180 for reference, none for explanations —
decisions do not rot on a clock, they get superseded).

```sh
grep -rn "Last verified:" docs --include="*.md" | sort -t: -k3
```

Triage rule for anything flagged: **verify it, fix it, or delete it — in that order of
preference, but deletion beats leaving a wrong doc in place.** A missing doc makes people
ask; a wrong doc makes people fail silently.

### 4. House style for runbooks

| Rule | Wrong | Right |
|---|---|---|
| Imperative voice | "The developer should then build the project" | "Run `<BUILD-CMD>`." |
| Expected output after EVERY command | (command, then silence) | "Run `<TEST-CMD>`. Expect the final line `OK (N tests)` in under 2 minutes. If you see `FAILED`, stop and see Troubleshooting." |
| One action per step | "Build, then if that works deploy, unless it's Friday" | Split into steps 4, 5, 6; put the condition in its own decision step. |
| Define jargon at first use | "Drain the sidecar before cutover" | "Drain the *sidecar* (the per-host proxy process) — i.e., stop it accepting new connections — before cutover." Define once, at first use; after that use the term freely. |
| Tables over prose for enumerable facts | A paragraph listing five environment names and their URLs | A 5-row table: Environment / URL / Purpose. Anything you can enumerate (flags, ports, envs, error codes), tabulate. |
| Copy-pasteable commands | `run the build script with the prod flag` | A fenced code block containing the literal command, placeholders in `<ANGLE-CAPS>`. |
| Failure branches inline or linked | "This should work" | "If step 5 prints `EADDRINUSE`, another instance is running: see Troubleshooting T2." |
| No aspirational steps | "Eventually this will be automated" | Delete it, or move it to an issue tracker. Runbooks describe the present. |

Litmus test for a finished runbook: a reader who knows nothing but the prerequisites can
execute it with zero judgment calls. Every place they would have to guess is a doc bug.

### 5. The write-at-the-moment rule

Docs get written when the knowledge is fresh, by the person holding it, or the knowledge
is lost. Three mandatory trigger moments:

| Moment | What gets written | Where |
|---|---|---|
| **Investigation close** — root cause found, fix landed | Incident/investigation writeup (template below; method in failure-archaeology) | Investigation chronicle |
| **Decision time** — a design choice with alternatives just got made | ADR (method in architecture-contract), plus an ADR pointer from any doc the decision affects | ADR log |
| **Onboarding pain** — a newcomer got stuck, asked a question, or was told something not in the docs | The missing step / missing definition, added to the onboarding doc *by or with the newcomer that day* | Onboarding doc |

Enforcement heuristics (candidate practices — adopt what your team will actually sustain):
- Make the writeup part of the definition of done: an investigation is not closed, and a
  decision is not final, until its doc exists. Review checklists can carry this.
- "You asked, you write": whoever asked the question that revealed the gap drafts the
  fix — they are the only person who provably knows what was confusing.
- Budget 15 minutes, not an afternoon. A dated five-line writeup at the right moment
  beats a polished page written from memory three weeks later.

### 6. Anti-patterns

| Anti-pattern | What it looks like | Fix |
|---|---|---|
| **Aspirational docs** | Docs describing the intended future system ("the service will retry...") as if it were current | Docs of record describe the PRESENT. Future plans live in issues/ADRs marked Proposed. If it is not deployed, it is not in the runbook. |
| **Duplicated truths** | The port list in the README, the wiki, and a comment — three values, two of them wrong | One home + links (doctrine section 1). Run the docs audit to find duplicates: grep for the fact's distinctive token across docs. |
| **Docs as changelog dumps** | A doc that grows by appending "Update 2025-03: actually now..." forever; the truth is the diff of all paragraphs | Rewrite the doc to state only the current truth. History lives in git (`git log --follow -p -- <DOC>`), not in the prose. |
| **Wiki graveyards** | A second doc system (wiki, shared drive, chat pins) accumulating pages nobody verifies or deletes | One doc system of record, in the repo, versioned with the code so docs and code change in the same PR. If an external wiki must exist, it contains only links into the repo docs. |
| **Verification theater** | Bumping `Last verified:` dates without running the re-verify command | The date may only change in a commit whose message says what was run. Spot-check in review: "what did you run?" |
| **The 40-page onboarding doc** | Comprehensive, unmaintainable, unread | Onboarding doc covers day one to first merged change, nothing more; everything else is links to docs of record. |

## Worked example

*Illustrative example — all names and facts fictional.*

The **Tidepool** project (a fictional sensor-data pipeline) has a `README.md`, a wiki, and
tribal knowledge. A new engineer, Mika, joins and the deploy fails on their first day.
Applying this skill:

1. **Audit.** From the repo root:
   `grep -rL "Last verified:" docs --include="*.md"` → all 7 docs listed (none verified).
   The dead-path check flags `DEAD: scripts/deploy_v1.sh` referenced in `docs/deploy.md`
   — the script was replaced by `scripts/deploy.py` four months ago. Root cause of Mika's
   failed deploy found in doc form.
2. **Choose homes.** The broker port `9402` appears in `README.md`, the wiki, and
   `docs/deploy.md` — with the wiki saying `9042`. The home becomes
   `docs/reference/ports.md` (reference type, verifiable against `config/broker.toml`);
   README and deploy runbook are edited to link there; the wiki page is replaced with a
   single link into the repo.
3. **Rewrite the deploy doc as a proper runbook** (`docs/runbooks/deploy.md`), typed and
   provenanced:

   ```markdown
   # Runbook: Deploy Tidepool to staging
   Type: runbook
   Last verified: 2026-07-06 — Mika executed all steps on a fresh checkout
   Re-verify: run steps 1-6; step 6 must print "healthy: 3/3 pods"

   Prerequisites: staging kubeconfig (see docs/onboarding/access.md), Python 3.11+.

   1. Run `python scripts/deploy.py --env staging`.
      Expect: `Pushed image tidepool:<GIT-SHA>` within ~3 min.
      If you see `403 Forbidden`: your registry token expired — see Troubleshooting T1.
   2. ...
   ```

4. **Verify by type.** Mika (the newcomer) executes the runbook top-to-bottom — which is
   both the runbook's execution-verification AND the onboarding verification. Step 4's
   expected output was wrong (`2/2 pods`, actually `3/3`); fixed same day under the
   write-at-the-moment rule, provenance line dated in the same commit.
5. **Explanation split out.** Three paragraphs in the old deploy doc explained WHY staging
   uses blue/green. That is explanation-type content verified against decisions, so it
   moves to ADR-0007 (per architecture-contract); the runbook keeps one line:
   "Why blue/green: see ADR-0007."

Net result: 1 home per fact, 4 typed docs, every doc carrying a re-verify contract, and
the next newcomer inherits a runbook proven by execution eleven days ago instead of a
wiki page last touched by someone who left.

## Templates

Copy, fill, delete unused sections. Placeholders in `<ANGLE-CAPS>`.

### Runbook

```markdown
# Runbook: <TASK IN IMPERATIVE FORM, e.g. "Restore the staging database">
Type: runbook
Last verified: <YYYY-MM-DD> — <WHO/HOW: "ran end-to-end on fresh checkout">
Re-verify: <one line: what to run and what final output proves success>

**When to use:** <the situation that makes you reach for this runbook>
**Prerequisites:** <access, tools, state — each one checkable, with a check command>
**Time:** <rough duration> **Risk:** <what this can break; when NOT to run it>

## Steps
1. Run `<COMMAND>`.
   Expect: <literal expected output or observable state, with rough duration>.
   If instead <FAILURE SIGN>: <action or link to Troubleshooting Tn>.
2. <one action>...

## Troubleshooting
| ID | Symptom | Cause | Fix |
|---|---|---|---|
| T1 | <EXACT-ERROR-TEXT> | <CAUSE> | <ACTION> |
```

### ADR pointer

Full ADR discipline (format, statuses, supersession) is owned by **architecture-contract**
— do not restate ADR content in other docs. When any doc touches a decided question, drop
this one-liner instead of re-explaining:

```markdown
> **Decision:** <one-sentence statement of what was decided> — see <ADR-NNNN>
> (status: Accepted <YYYY-MM-DD>). Do not re-litigate here; propose changes as a new ADR.
```

### Incident / investigation writeup

Full method (evidence standards, chronicle structure) is owned by **failure-archaeology**.
Minimal at-the-moment capture form — write this the day the investigation closes:

```markdown
# <YYYY-MM-DD> — <one-line symptom, e.g. "Ingest stalls after ~6h uptime">
Status: <fixed | mitigated | wontfix | open | superseded — vocabulary owned by failure-archaeology> Severity: <impact in one line>
Symptom: <what was observed, verbatim errors/numbers>
Root cause: <what was actually wrong — or "unknown; best hypothesis: ...">
Evidence: <the commit/log/experiment that proves the root cause — links, not adjectives>
Fix: <COMMIT-OR-PR-LINK> Follow-ups: <ISSUE-LINKS or "none">
Trap for the future: <the one thing that cost the most time, so it is never paid again>
```

### README skeleton

The README is a routing page, not a doc of record for details — nearly every section is a
link to the fact's real home:

```markdown
# <PROJECT>
<Two sentences: what it is, who it is for.>
Last verified: <YYYY-MM-DD> — <HOW> | Re-verify: <one line>

## Quick start
<The 3-5 commands from zero to "it runs", each with expected output.
 Anything longer: link to docs/onboarding/.>

## Where things are
| Need | Go to |
|---|---|
| Set up a dev environment | docs/onboarding/setup.md |
| Run / deploy | docs/runbooks/ |
| Configuration reference | docs/reference/config.md |
| Why it is built this way | docs/adr/ |
| Past investigations | docs/investigations/ |

## Status & support
<CI badge / current state in one line; where to ask questions.>
```

## Instantiate for your project

Produce `<PROJECT>-docs-and-writing` (the project-specific version) by executing these
steps in the target repo. Evidence rule: every claim in the instantiated skill must come
from a command you ran or a file you read in THAT repo — no assumptions.

1. **Inventory what exists.** Run and record output of:
   - `git ls-files | grep -Ei '\.(md|rst|txt|adoc)$'` — every doc in the repo.
   - `git ls-files | grep -Eiv '\.(md|rst|txt|adoc)$' | grep -Ei 'readme|docs?/'` — doc-ish stragglers.
   - Ask the owner (or check links in the README) whether an external wiki/drive exists;
     list it explicitly as in-scope graveyard or out of scope.
2. **Type every doc.** Build the doc register table — one row per doc:
   `path | type (runbook/reference/explanation/onboarding/UNKNOWN) | home for which facts | last git touch | provenance line present?`
   Get last-touch dates with the date-audit command from doctrine section 3. Do not guess
   a type from the filename; open the doc. Anything mixing types gets flagged for split.
3. **Run the full rot audit** (all six checks in doctrine section 3, with the docs path
   and file-extension list adjusted to this repo's languages). Paste the actual findings
   — dead paths, unverified docs, date outliers — into the instantiated skill as the
   initial triage backlog. Do not write "docs are mostly fine"; write the list.
4. **Pick the homes.** For the 5-10 facts most likely to be duplicated (ports, env names,
   build/test commands, deploy targets, version requirements): grep each fact's
   distinctive token across all docs (`grep -rn "<TOKEN>" docs/ README.md`), record every
   occurrence, declare one home, and file the link-ification of the rest as tasks.
5. **Fill the skeleton** below. Blanks may only be filled with evidence gathered in steps
   1-4 ("do not write a register row for a doc you have not opened; do not declare a home
   without the grep showing the duplicates").

   ```markdown
   ---
   name: <PROJECT>-docs-and-writing
   description: Doc-of-record map and maintenance rules for <PROJECT>.
   ---
   # <PROJECT> — Docs of record
   Instantiated: <YYYY-MM-DD> from docs-and-writing v2026-07-06, by <WHO-OR-MODEL>.

   ## Doc register        <!-- from step 2; the authoritative doc map -->
   | Path | Type | Facts it is home for | Last verified | Re-verify |
   ## Homes for hot facts <!-- from step 4 -->
   | Fact | Home | Known duplicates to link-ify |
   ## Rot audit backlog   <!-- from step 3; dated findings -->
   ## Repo-specific style deltas  <!-- only where this repo deviates; else "none" -->
   ## Audit cadence       <!-- who runs the section-3 checks, how often -->
   ```
6. **Prove one runbook.** Pick a runbook whose execution is read-only or confined to a
   non-production environment (never a deploy/restore/cleanup runbook — if the most-used
   runbook is one of those, rehearse it only under run-and-operate's safety rails, or pick
   the next-most-used safe one; write the missing safe one if none exists). Execute it
   top-to-bottom, fix what breaks, and stamp its first honest provenance line.
   The instantiated skill is not done until at least one doc in the repo carries a
   provenance line earned by execution — that is the existence proof for the whole system.

## Provenance and maintenance

Authored 2026-07-06 against no specific project (portable discipline template).

Verified during authoring, in a throwaway git repo (git 2.x, Git Bash on Windows):
- `git log -1 --format=%cs -- <FILE>` prints the last commit date (YYYY-MM-DD) for a file.
- `git log --diff-filter=D --name-only --format=` lists ever-deleted paths.
- The dead-path grep loop and the `grep -rL "Last verified:"` check both ran and produced
  the expected hits/misses.

Volatile parts and re-verification:

| Part | Volatility | Re-verify with |
|---|---|---|
| git flags used above (`--format=%cs`, `--diff-filter`, `--follow`) | Low; stable for years | `git log --help` (search the flag name) |
| grep flags (`-rL`, `-rEho`, `-rlF`) | Low (GNU grep); BSD grep on macOS differs on some long options | `grep --help`; on macOS test `-L` and `-E` explicitly |
| Rot-budget day counts (90/180) | Heuristic, not verified — tune per project | Team judgment; record the chosen budget in the instantiated skill |
| Directory layout suggestions (`docs/runbooks/` etc.) | Convention, not requirement | Adopt the repo's existing layout in the instantiated copy |

Instantiated copies must add their own provenance: instantiation date, source-skill
version, who ran the audits, and per-doc `Last verified` lines earned by the rules in
doctrine section 2.
