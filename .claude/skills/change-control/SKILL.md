---
name: change-control
description: >-
  Load this skill when you must decide how risky a change is and what gate it must pass:
  classifying a diff (mechanical vs behavioral vs contract-breaking vs irreversible), setting
  up branch protection / review rules for a new repo, writing or updating a project's
  NON-NEGOTIABLES list, handling an emergency hotfix without bypassing review culture, or
  diagnosing a review process that has become rubber-stamping or bureaucratic gate inflation.
  Trigger phrasings: "does this need review?", "can I just push this?", "what checks should be
  required?", "we keep reverting things", "add a rule so this never happens again",
  "emergency deploy", "our reviews are useless". Delivers a change-classification taxonomy
  with gates per class, a non-negotiables registry format, per-class reviewer checklists, a
  break-glass protocol, and repo-mining commands to discover a project's implicit change control.
---

# Change Control: Classifying, Gating, and Reviewing Changes

## Purpose

This skill lets you (a) classify any proposed change by its blast radius and reversibility,
(b) apply the right gate — no more, no less — before it merges or ships, (c) capture a
project's hard-won rules as NON-NEGOTIABLES with the incident that created each one, and
(d) keep the whole system honest: emergencies don't destroy the gate, and the gate doesn't
grow until people route around it.

## When to use / When NOT to use

Use when: deciding what review/checks a change needs; designing branch protection and PR
rules for a new repo; writing down a "never again" rule after an incident; running a
post-emergency review; auditing why reverts keep happening.

Do NOT use when the real question is a sibling's:

| If instead you need... | Use sibling skill |
|---|---|
| What counts as evidence that a change works; acceptance thresholds; golden tests | `validation-and-qa` |
| WHY the architecture is shaped this way; recording design decisions (ADRs) | `architecture-contract` |
| Mining history for past investigations and root causes (not gates) | `failure-archaeology` |
| Running a multi-phase risky effort with promotion gates between phases | `campaign-design` (its promotion protocol routes each promotion through THIS skill's gates) |
| Reproducing the build/environment so CI checks can exist at all | `build-and-env` |
| Deploy/run mechanics and operational safety rails | `run-and-operate` |
| Flag definitions, defaults, guards/kill-switches, the flag catalog | `config-and-flags` (it defines the flag; this skill gates the flip) |
| Executing a gated schema change as an EF Core migration | `dotnet-ef-discipline` |
| SQL Server index/statistics changes and their before/after measurement | `sql-server-operations` |
| Judging whether a C# diff is over-built (craft quality, not gate class) | `csharp-code-discipline` |
| Classifying an ASP.NET Core API diff by its wire-level breaking-change taxonomy (which maps onto these classes) | `aspnet-api-discipline` |
| Bootstrapping this skill for a specific repo | `skill-factory`, then §Instantiate below |

## Core doctrine

### Definitions (used throughout)

- **Gate**: a condition that must be satisfied before a change merges or ships (review
  approval, passing check, sign-off, waiting period).
- **Blast radius**: the set of things that can break if the change is wrong (one module, all
  callers, external consumers, stored data).
- **Contract**: any interface someone outside the diff relies on — public API, wire format,
  DB schema, config file format, CLI flags, event payloads, file layouts.
- **Irreversible change**: one you cannot undo by reverting the commit — data migrations that
  drop/rewrite data, deleting external resources, publishing artifacts/versions, sending
  external communications, rotating credentials.
- **Non-negotiable**: a project rule that no individual may waive alone, each backed by a
  recorded rationale and (where one exists) the incident that created it.

### 1. Change-classification taxonomy

Classify EVERY change into exactly one primary class — the highest class that applies.
When in doubt between two classes, take the higher one (heuristic: misclassifying down is
the expensive error; misclassifying up costs one extra review).

| Class | Definition | Litmus test | Examples |
|---|---|---|---|
| **M — Mechanical** | No behavior change intended or possible | A correct tool could have made it; output byte-identical or provably equivalent | Formatting, renames within private scope, comment/doc edits, dead-code deletion (verified unreferenced), dependency lockfile refresh with no version change |
| **B — Behavioral** | Runtime behavior changes, but every affected caller is inside this repo | You can enumerate all call sites with a repo-wide search | Bug fixes, new features behind existing interfaces, performance changes, internal refactors that alter behavior (ordering, timing, logging) |
| **C — Contract-breaking** | Some consumer OUTSIDE the diff's control must react | Someone who never sees this PR can be broken by it | API signature/response changes, DB schema changes, config format changes, CLI flag removal, event/message shape changes, error-code changes |
| **X — Irreversible** | `git revert` does not restore the previous state of the world | Ask: "if this is wrong, what command undoes it?" If the answer involves backups, apologies, or 'we can't' → X | Destructive data migrations, deleting prod resources, publishing a package version, external announcements, key rotation, GDPR-style data deletion |

Orthogonal flag, combinable with any class: **E — Emergency** (production is down or
actively degrading; see §4). E modifies the *sequencing* of gates, never their existence.

Classification rules of thumb (heuristics, not proofs):
- A "mechanical" change that touches >30 files or is hand-made (not tool-made) is B until
  proven M — hand-mechanical edits are where typos hide.
- Schema-*additive* changes (new nullable column, new optional field) are B, not C, ONLY if
  the project has a written compatibility policy saying consumers ignore unknown fields.
  No written policy → treat as C.
- Any change whose rollback plan is "run another migration" is X, because the rollback
  itself can fail.

### 2. Gating requirements per class

These are the DEFAULT gates. §Instantiate shows how to tighten/loosen them per project with
evidence. Never loosen below class M's row.

| Gate | M | B | C | X |
|---|---|---|---|---|
| CI: build + full test suite green | required | required | required | required |
| Human review approvals | 1 (may be post-merge for tool-generated diffs if project policy allows) | 1 | 2, incl. an owner of the consumed contract (CODEOWNERS) | 2, incl. project owner/lead |
| Evidence of behavior (see `validation-and-qa` for what counts) | none beyond CI | test that fails without the change, or recorded manual verification | above, PLUS consumer-side compatibility evidence (contract tests, staging consumer run) | above, PLUS rehearsal of the operation on a copy (e.g. migration run against a prod-data snapshot) |
| Written rollback plan in the PR | no | no | yes ("revert + redeploy" is acceptable if true) | yes — and it cannot be "revert"; must name the recovery mechanism (backup restore, tombstone period, dual-write window) |
| Announce/coordinate before merge | no | no | yes — notify consumers, deprecation window per project policy | yes — scheduled window, named operator, second person present ("two-person rule") |
| Waiting period after approval | no | no | project-defined (default: none) | default 24h between approval and execution, so review adrenaline cools off |

Notes:
- Gates attach to the CLASS, not to the author's seniority. Principal engineers' X-changes
  get the same gate — that is most of the gate's value.
- "2 approvals" means two humans who each did the per-class checklist in §5, not two clicks.

### 3. Non-negotiables: capturing rules with rationale and incident

A non-negotiable without a recorded WHY becomes folklore, then gets deleted by the next
refactorer as "obsolete process". Every rule entry MUST carry rationale and, where one
exists, the incident. Rules without an incident are labeled `preventive` and get reviewed
annually for deletion; rules with incidents are effectively permanent until the underlying
system is gone.

Store as `docs/NON-NEGOTIABLES.md` (or the project's docs-of-record location — see
`docs-and-writing`), one entry per rule, in this exact template:

```markdown
## NN-<NUMBER>: <imperative one-line rule>

- **Rule**: <precise, testable statement. "Never run <DESTRUCTIVE-MIGRATION-CMD> against
  <PROD-DB> without a same-day verified backup restore test." Not "be careful with migrations.">
- **Class trigger**: <which change class(es) this applies to: M/B/C/X>
- **Rationale**: <the mechanism of harm, 1-3 lines: what goes wrong and why the naive
  approach fails>
- **Incident**: <date, one-line description, and a durable pointer: commit SHA, incident
  doc, issue #. If none: "None — preventive; review by <DATE>.">
- **Enforcement**: <automated check if one exists (CI job name, lint rule, hook), else
  "reviewer checklist only" — which is a flag to go automate it>
- **Waiver path**: <who can waive, and where waivers are logged. "No waiver" is valid.>
```

Illustrative example (fictional project "Orrery"):

```markdown
## NN-4: Never change the `ledger_events` table in the same PR as code that reads it

- **Rule**: Schema migrations touching `ledger_events` ship alone, deploy fully, and bake
  24h before any dependent code change merges.
- **Class trigger**: C, X
- **Rationale**: Rolling deploys mean old code and new schema coexist; a combined PR makes
  the revert of either half break the other.
- **Incident**: 2025-11-03 — combined PR #812 reverted during deploy, old code wrote rows
  the new consumer couldn't parse; 6h reconciliation. See incident doc INC-2025-041.
- **Enforcement**: CI job `schema-isolation-check` fails any PR mixing `migrations/` and
  `src/ledger/` paths.
- **Waiver path**: No waiver.
```

Lifecycle: rules are added via the post-incident review (see `failure-archaeology` for
mining the history), and every rule addition is itself a class-B change to the project's
process — reviewed, not decreed.

### 4. Emergencies: break-glass without destroying the gate

Principle: **an emergency reorders gates in time; it never deletes them.** Skipped-then-paid
is acceptable; skipped-and-forgotten is how the gate dies.

Break-glass protocol:

1. **Declare** — the person invoking emergency mode says so explicitly in the PR/commit:
   `EMERGENCY: <one-line reason>` in the PR title or commit subject. Silent bypass is the
   cardinal sin, not the bypass itself.
2. **Minimum viable gate still applies** — even in an emergency: (a) a second human watches
   the change go out (call them, wake them; two-person rule), and (b) the change is the
   smallest diff that stops the bleeding — no drive-by fixes.
3. **Never break glass on class X** — if the "emergency fix" is irreversible, it is not a
   fix, it is a second incident. Mitigate reversibly first (feature flag off, rollback,
   traffic drain — see `run-and-operate`), then do the X-change through the normal gate.
4. **Debt comes due in 2 business days** — every emergency merge gets a retroactive full
   review as if it were pre-merge: the per-class checklist in §5, run honestly, with a
   tracked issue. Findings either amend the fix or explicitly accept it.
5. **Log it** — append to `docs/EMERGENCY-LOG.md`: date, PR/SHA, who, why, which gates were
   deferred, retro-review issue link.
6. **Audit the log quarterly** — >1 break-glass/month sustained means either the gate is
   too slow for legitimate work (fix the gate) or "emergency" has become the fast lane
   (fix the culture). Either finding is actionable; ignoring the log is not.

### 5. Review discipline: what reviewers MUST check per class

A review is the checklist for the change's class, executed. "LGTM" with no evidence of the
checklist is a rubber stamp (§6). Reviewers state the class they reviewed against — this
catches misclassification, which is the most common gating failure.

**Every class:**
- [ ] Confirm the stated class is right. The #1 reviewer job. If you'd class it higher, say
  so before reading further.
- [ ] Diff contains only what the description says (no smuggled changes).
- [ ] No NON-NEGOTIABLE is triggered — scan the registry's `Class trigger` column.

**M — Mechanical (target: minutes):**
- [ ] Verify the mechanical claim, don't eyeball it: re-run the tool
  (`<FORMATTER-CMD>`, codemod) or diff generated output before/after. For hand-made
  "mechanical" diffs, spot-check 10 random hunks; one behavioral hunk reclassifies to B.

**B — Behavioral:**
- [ ] The evidence exists and you looked at it: a test that fails without the change, or a
  recorded before/after observation (standards per `validation-and-qa`).
- [ ] Enumerate affected call sites (repo-wide search) and confirm the diff or tests cover
  the surprising ones.
- [ ] Failure behavior: what happens when the new code path errors? (The happy path is what
  the author already tested.)

**C — Contract-breaking (all of B, plus):**
- [ ] Name the consumers. Not "clients" — list them or link the registry. Unknown consumers
  → the change is blocked on finding out, not on hoping.
- [ ] Compatibility evidence: contract test, staging run of a real consumer, or documented
  versioning (old and new contract served in parallel).
- [ ] Deprecation/announcement done per project policy, with dates.
- [ ] Rollback plan is written and is actually possible after consumers start using the new
  contract.

**X — Irreversible (all of C where applicable, plus):**
- [ ] Rehearsal evidence: the operation was executed against a realistic copy
  (prod-snapshot DB, staging tenant) and the result verified — link to it.
- [ ] Recovery mechanism named and TESTED (a backup you never restored is a hope, not a
  plan).
- [ ] Scope fence: the exact objects affected are enumerated (row counts, resource IDs)
  and the command is constrained to them (WHERE clause reviewed, `--dry-run` output
  attached where the tool supports it).
- [ ] Timing: scheduled window, named operator, second person present.

### 6. Failure modes of change-control systems themselves

The system needs the same skepticism it applies to changes. Symptoms → diagnosis → fix:

| Failure mode | Symptoms | Fix |
|---|---|---|
| **Rubber-stamping** | Approvals within minutes on B/C changes; zero review comments over weeks; reverts of "approved" changes (`git log -i --grep="revert"` on recent history) | Require reviewers to state the class + one checklist finding ("checked call sites, all covered") in the approval. Track revert rate of reviewed changes as the metric — approval count measures nothing. |
| **Gate inflation** | Gates added after every incident, none ever removed; M-changes waiting days; process doc grows monotonically | Every new gate names the class it applies to and the incident justifying it (same template as NN entries). Annual gate audit: each gate must cite a change it caught or a `preventive` renewal — else it's deleted. Never let an X-incident add gates to M-changes. |
| **Routing-around** | Direct pushes to `<MAIN-BRANCH>`, "docs" PRs containing code, changes split into many "trivial" PRs, emergency label on non-emergencies, work migrating to un-gated repos/scripts | Treat as a signal about the GATE first, not the people: measure gate latency for M-class; if honest M-changes take >1 day, that's the leak's cause. Then close the technical bypasses (branch protection on, `enforce_admins` on). |
| **Misclassification drift** | Everything is labeled M/B; C-changes discovered via consumer breakage | Reviewer's first checklist item (§5) + a monthly sample: pull 10 merged PRs, re-classify cold, compare. >2 downgrades → recalibrate with examples in the project skill. |
| **Zombie non-negotiables** | Rules nobody can explain; rules referencing dead systems; "we've always done that" | The template's Incident field exists for this. Rule with no rationale on file → candidate for deletion via normal review, and the deletion PR must state "searched history, found no incident" (see `failure-archaeology` for how). |
| **Emergency-lane capture** | Break-glass frequency creeping up; retro-reviews never happen | §4 steps 5–6: the log makes it visible; the 2-day debt makes it costly enough to self-limit. |

## Worked example

**Illustrative example — all names and facts fictional.**

Project "Orrery", a billing service. Change: PR #931 "Speed up invoice rollup" — replaces a
per-row loop with one SQL aggregate, and renames the internal helper `sumRows` to
`aggregateInvoice`.

1. **Classify.** Rename of a private helper is M; the SQL rewrite changes runtime behavior
   (ordering of rounding operations!) with all callers in-repo → B. Highest class wins: **B**.
   The author had labeled it "refactor (mechanical)" — the reviewer's first checklist item
   catches this: floating-point rounding order can change totals by a cent. Reclassified B.
2. **Check non-negotiables.** Registry scan: NN-2 "Any change to rounding or totals math
   requires golden-invoice comparison" (Class trigger: B, C; Incident: 2024-07 penny-drift
   INC-2024-019). Triggered.
3. **Gate for B + NN-2.** CI green; 1 review; evidence = the golden-invoice suite
   (`<TEST-CMD> --suite golden-invoices`) run against 10,000 archived invoices: 3
   mismatches of $0.01 found. Not a rubber-stamp story: the evidence gate caught a real
   diff. Author fixes rounding order, suite goes to 0 mismatches, links the run in the PR.
4. **Review.** Reviewer comments: "Reviewed as B. Ran golden suite locally, 0/10000 diff.
   Call sites: 4, all covered by suite. Approving." That sentence is what a non-rubber-stamp
   approval looks like.
5. **Contrast, same week:** dropping the legacy `invoice_v1` API endpoint. External
   partners consume it → **C**: consumer list pulled from the API-key table, 30-day
   deprecation notice sent, contract test proving `invoice_v2` serves the migrated fields,
   2 approvals including the API owner per CODEOWNERS, rollback = re-enable route flag.
   And the cleanup migration that deletes `invoice_v1` rows? **X** — rehearsed on a
   prod-snapshot, restore tested, scheduled window, runs two weeks later. Three changes,
   three classes, three different gates — none of them "the maximum gate for everything".

## Instantiate for your project

Goal: produce `.claude/skills/<PROJECT>-change-control/SKILL.md` containing the project's
REAL classes, gates, and non-negotiables — mined from the repo, not invented. Do not write
any rule, gate, or incident you cannot point to an artifact for.

### Step 1 — Mine the explicit change control

Run these from the repo root (GitHub-hosted assumed; adapt endpoints for GitLab/other —
`gh` requires auth via `gh auth login`):

```sh
# Default branch name (fills <MAIN-BRANCH>)
gh repo view --json defaultBranchRef

# Branch protection: required reviews, required status checks, enforce_admins,
# who can push. {owner}/{repo}/{branch} are auto-filled by gh from the current repo/branch.
gh api repos/{owner}/{repo}/branches/{branch}/protection

# Newer repos use rulesets instead of (or on top of) classic protection:
gh api repos/{owner}/{repo}/rulesets

# CODEOWNERS (GitHub reads it from any of these three locations)
cat .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS 2>/dev/null

# PR template(s) — the questions it asks ARE the existing review checklist
cat .github/PULL_REQUEST_TEMPLATE.md PULL_REQUEST_TEMPLATE.md docs/PULL_REQUEST_TEMPLATE.md 2>/dev/null
ls .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null

# CI: what actually runs (the required subset comes from the protection output above)
ls .github/workflows/
```

If `gh api .../protection` returns `404 Branch not protected`, that IS a finding: record
"no branch protection" in the instantiated skill's gaps section.

**If the forge is not GitHub or `gh` is unavailable** (GitLab, Gitea, Azure DevOps,
offline mirror), do not invent endpoints and do not skip the step silently. Mine the
in-repo equivalents:

```sh
# CODEOWNERS equivalents and MR/PR templates:
cat .gitlab/CODEOWNERS CODEOWNERS docs/CODEOWNERS 2>/dev/null
ls .gitlab/merge_request_templates/ 2>/dev/null
# CI config — which jobs exist and which the config marks blocking/required:
cat .gitlab-ci.yml azure-pipelines.yml Jenkinsfile 2>/dev/null | head -60
```

Then read merge patterns from git alone: `git log --merges --first-parent --oneline
<MAIN-BRANCH> | head -50` — merge commits mean an MR/PR flow exists; their absence plus
direct commits on the main line means pushes are (or were) un-gated. For anything not
discoverable in-repo (server-side branch protection, required approval counts), write
`UNKNOWN — verify in the forge UI` into the instantiated skill's Known gaps section.
Then proceed to Step 2, which is pure git and always works.

### Step 2 — Mine the implicit change control (history as evidence)

```sh
# Reverts = changes a gate failed to catch. Read each: what class was it? What gate
# would have caught it? These become your gate table adjustments and NN candidates.
git log -i --grep="revert" --oneline

# Wider net: reverts, rollbacks, hotfixes (multiple --grep are OR'd)
git log -i --grep="revert" --grep="rollback" --grep="hotfix" --grep="emergency" --oneline

# Recency-bounded, with dates, for the "is this still happening" question
git log --since="180 days ago" -i --grep="revert" --format="%h %ad %s" --date=short

# Merge traffic on the main line — is review actually happening via PRs?
git log --merges --first-parent --oneline <MAIN-BRANCH> | head -50

# Recent merged PRs: were they reviewed? (rubber-stamp / routing-around evidence)
gh pr list --state merged --limit 50 --json number,title,mergedAt,reviewDecision

# Who actually touches the risky areas (candidate contract owners for the C-gate)
git shortlog -sn HEAD -- <RISKY-PATH>

# History of a known-dangerous file/table/flag (feeds NN incident pointers)
git log --oneline -S "<DANGEROUS-IDENTIFIER>"
```

(Note: give `git shortlog` an explicit revision like `HEAD` — with piped stdin and no
revision it reads from stdin and prints nothing.)

For each revert found, record: SHA, what broke, the class of the original change, and which
gate (per the §2 table) was missing or skipped. A revert whose original change had no test
evidence is a `validation-and-qa` gap; a revert of an unreviewed direct push is a gate gap
here.

### Step 3 — Mine incident artifacts for non-negotiables

Search for existing rule-shaped knowledge: `docs/` for postmortems/incident files, issue
tracker labels like `incident`/`postmortem` (`gh issue list --label incident --state all`),
comments containing "never" / "do not" / "always" near dangerous code
(`grep -rn -iE "never|do not|DANGER|footgun" --include="*.<EXT>" <SRC-DIR> | head -40`).
Each hit is an NN candidate — but it enters the registry ONLY with the template fully
filled, including the incident pointer. Use `failure-archaeology` to chase a rule back to
its originating commit/issue. No incident found → label `preventive` with a review date, or
drop it.

### Step 4 — Fill the skeleton

```markdown
---
name: <PROJECT>-change-control
description: <triggers specific to this project's change types and danger zones>
---
# <PROJECT> Change Control
## Classes (adapted)          # start from M/B/C/X; ADD project-specific litmus tests
                              # ("touching <DIR-X> is always ≥C because <CONSUMER>"),
                              # each backed by a Step-2 artifact
## Gate table                 # §2 table, edited to match REAL protection from Step 1;
                              # every deviation from default annotated with why + evidence
## Non-negotiables            # full registry, template per §3, every entry sourced (Step 3)
## Emergency protocol         # §4 with real names: who is the second human, where the log lives
## Reviewer checklists        # §5 specialized: real commands for "run the evidence"
## Known gaps                 # what Step 1–2 showed is missing (no protection, no CI check
                              # for X, reverts clustering in <AREA>) — with the evidence
## Provenance                 # date, commands run, SHAs/PRs cited
```

### Step 5 — Evidence bar before filling any blank

- Do not write a gate row that contradicts observed reality without flagging it: if branch
  protection requires 0 reviews, the skill says so and lists it under Known gaps — it does
  not describe the aspirational process as current.
- Do not write an NN entry whose Incident field you have not opened and read (commit, issue,
  or doc). Secondhand folklore gets `preventive` + review date, or nothing.
- Do not copy this file's §2 defaults verbatim if Step 2 shows they'd have missed real
  reverts — adjust and cite the reverts.
- Every claim of the form "X is required" must be reproducible by re-running a Step-1
  command.

## Provenance and maintenance

- Authored 2026-07-06 against no specific project. All project facts in this file are
  labeled illustrative and fictional.
- Verified by execution on 2026-07-06 in a scratch repo (git 2.x, Git Bash/Windows):
  `git log -i --grep=... --oneline` (incl. multiple `--grep` OR behavior),
  `git log --since=... --format="%h %ad %s" --date=short`, `git log --merges --first-parent`,
  `git log -S`, `git shortlog -sn HEAD` (and the no-revision stdin trap noted in Step 2).
- NOT executed here (no `gh` on the authoring machine — syntax from GitHub CLI/REST docs,
  current as of the knowledge cutoff): `gh api repos/{owner}/{repo}/branches/{branch}/protection`,
  `gh api repos/{owner}/{repo}/rulesets`, `gh repo view --json defaultBranchRef`,
  `gh pr list --json ...`, `gh issue list --label ...`. Re-verify with `gh api --help` and
  `gh pr list --json 2>&1 | head` (bare `--json` lists valid fields) before trusting flags.
- Volatile parts: `gh` endpoints and JSON field names (GitHub is migrating classic branch
  protection toward rulesets — re-check `gh api repos/{owner}/{repo}/rulesets` first on new
  repos); CODEOWNERS/PR-template path conventions (re-check GitHub docs); the §2 default
  gate table is doctrine, not data — recalibrate per project via §Instantiate Step 2.
- Instantiated copies MUST add their own Provenance section: date, commands run, and the
  SHAs/PRs/issues cited for every gate deviation and NN entry.
