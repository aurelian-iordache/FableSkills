---
name: config-and-flags
description: Load this skill when working with configuration options, feature flags, environment variables, CLI switches, or defaults — adding a new flag, flipping one, auditing "what config does this project actually have", debugging behavior that differs between environments, retiring a dead flag, or when the user says "add a setting", "make it configurable", "why is this flag on in prod", or "the config docs are out of date". Delivers a catalog format for every configuration axis, an add-a-flag checklist, a flag lifecycle, and a drift re-verification discipline.
---

# config-and-flags — Cataloging and Governing Every Configuration Axis

## 1. Purpose

This skill makes you able to (a) build and maintain a single trustworthy catalog of every way a project's behavior can be changed without editing code — env vars, config files, CLI flags, feature-flag services, build-time defines; (b) add new flags without growing an untested combinatorial swamp; and (c) keep the catalog true over time via cheap, mechanical re-verification instead of hope.

**Term of art — "configuration axis":** any named knob whose value changes runtime behavior: an environment variable, a config-file key, a CLI flag, a feature-flag-service toggle, or a compile-time define. "Flag" below means any of these unless narrowed.

## 2. When to use / When NOT to use

Use when: adding, flipping, renaming, or removing any configuration axis; auditing the config surface of an unfamiliar repo; debugging "works on my machine / differs per environment" symptoms that smell like config; writing or refreshing the project's config catalog.

Do NOT use for:

| If instead you need... | Use sibling skill |
|---|---|
| Approval/gating process for flipping a flag in production | **change-control** (a production flag flip IS a gated change — this skill defines the flag; that one governs the flip) |
| Where config files live at runtime, what the deploy reads, log/artifact paths | **run-and-operate** |
| Recreating the environment (SDK versions, secrets plumbing, .env bootstrap) | **build-and-env** |
| Deciding what tests a new flag needs and what counts as passing | **validation-and-qa** |
| Diagnosing a bug that turns out not to be config-related | **debugging-playbook** |
| Recording WHY a default was chosen as an architectural decision | **architecture-contract** |

## 3. Core doctrine

### 3.1 The catalog: one file, one row per axis

Keep a single doc of record — recommended path `docs/config-catalog.md` — with one entry per configuration axis. **Entry format (all fields mandatory; write `UNKNOWN` rather than guessing — an honest `UNKNOWN` is a work item, a guess is a landmine):**

| Field | Meaning |
|---|---|
| **Name** | Exact spelling as the code reads it (`RETRY_LIMIT`, `--enable-fast-path`, `server.timeout_ms`). One row per surface: if the same knob exists as env var AND CLI flag, list both names in this row and state which wins. |
| **Type** | bool / int / duration / enum(list values) / string / path / secret. |
| **Default** | The value when unset, verbatim from source. Also state WHERE the default lives (code line, schema file, deploy manifest) — defaults defined in two places is itself a drift bug; record which one wins. |
| **Valid range** | Legal values and units (`1–100`, `ms`, `must be existing dir`). If nothing validates it, write `UNVALIDATED` — that is a finding. |
| **Status** | `experimental` / `production` / `deprecated` (see lifecycle, §3.3). |
| **Guard / kill-switch** | How to instantly revert to old behavior in production without a deploy (e.g. "unset env var; code path is fully skipped"). If reverting requires a deploy, write `NO KILL-SWITCH — deploy required` in bold. |
| **Owner** | A person or team name responsible for answering questions and driving retirement. Not "everyone". |
| **Interaction warnings** | Other flags this one conflicts with, requires, or silently changes the meaning of. `NONE KNOWN` is acceptable; blank is not. |
| **Verify** | A one-line command proving the flag still exists and its default (see §3.4). |
| **Last verified** | Date the Verify command was last run and passed, ISO format. |
| **Retirement plan** | The condition under which this row gets deleted ("remove after 2 releases at 100%", "permanent operator knob — never retires"). Written at creation time, not later. |

Compact table layouts are fine for small catalogs; one `####` subsection per flag scales better past ~20 entries. What matters is that every field exists for every entry.

### 3.2 ADD-A-FLAG checklist

Run this checklist for every new configuration axis. Every item is check-able; do them in order.

1. **Justify the axis.** Write one sentence: who changes this value, and why can't it be a constant? If the honest answer is "we're not sure which value is right" — that's fine, but then the retirement plan (item 9) must say "pick a winner and delete the flag", not "keep forever".
2. **Follow the naming convention.** Match the project's existing pattern exactly (prefix, case, separator — e.g. all env vars start `<PROJECT>_`, all CLI flags are `--kebab-case`). If no convention exists yet, this flag sets it: pick one, write it at the top of the catalog. Name booleans for the behavior when true (`ENABLE_FAST_PATH=1`), never negated (`DISABLE_...`, `NO_...`) — double negatives in config are a classic operator trap.
3. **Default choice discipline: new behavior defaults OFF.** The default value must reproduce pre-flag behavior bit-for-bit. Shipping a flag whose default already changes behavior is not adding a flag — it is making an unguarded behavior change wearing a flag costume, and it silently converts every existing environment. If the new behavior should eventually be the default, that flip is a separate, later, gated change (see **change-control**).
4. **Guard requirement.** Verify the OFF path is truly the old code path, not a rewritten "equivalent". Check: with the flag unset, does execution reach any new code beyond the single `if` that tests the flag? If yes, you have no kill-switch — fix that before merging.
5. **Validate input.** Reject out-of-range values loudly at startup (fail fast), don't clamp silently. A typo'd `TIMEOUT_MS=30000000` should crash the process at boot with a clear message, not run with a bizarre value for a week.
6. **Log the effective value once at startup** (secrets redacted). This is the cheapest diagnostic you will ever add; **run-and-operate** covers where that log line lands.
7. **Assess test matrix impact.** Each independent boolean flag doubles the theoretical state space. Decide and record which combinations are actually tested: at minimum, (a) flag OFF = existing suite unchanged and green, (b) flag ON = targeted tests for the new behavior, (c) any combination named in an interaction warning. See **validation-and-qa** for what counts as adequate coverage. If you cannot afford to test a combination, record it as unsupported in the interaction warnings.
8. **Write the catalog entry** (§3.1) in the same commit as the code. A flag that exists in code but not the catalog is drift from day zero.
9. **Write the retirement plan now.** "Experimental flag: promote or delete within N releases / by <DATE>." Flags are cheap to add and expensive to own; the plan is the forcing function. Heuristic: a project where flags outnumber engineers ×10 has stopped retiring them.
10. **Documentation.** Update `--help` text / config schema / operator docs in the same commit — whichever of these the project treats as user-facing.

### 3.3 Flag lifecycle

```
experimental ──promote──> production ──deprecate──> deprecated ──remove──> removed
      └────────────────────delete (didn't pan out)────────────────────────────┘
```

| Transition | Criteria (all required) |
|---|---|
| create → **experimental** | ADD-A-FLAG checklist complete; default OFF; catalog entry with retirement plan exists. |
| experimental → **production** | (a) Ran enabled in a production-like environment for the period the retirement plan named; (b) test matrix rows from checklist item 7 are green; (c) owner signs off; (d) if the default flips ON as part of promotion, that flip goes through **change-control** as its own gated change — never bundled silently into the promotion commit. |
| production → **deprecated** | Replacement exists or the knob is obsolete. Deprecated means: still works, warns at startup when explicitly set, catalog row says what to use instead and the removal date. Deprecating a `production`-status flag is a class-C (contract-breaking) change — gate it per **change-control**: consumers named, announcement per policy, rollback plan. |
| deprecated → **removed** | At least one release shipped with the deprecation warning; a search shows no in-repo references left (`git grep -n '<FLAG_NAME>'` returns only the changelog); deploy manifests and runbooks scrubbed. Removal of a formerly-production flag is itself a class-C change gated per **change-control** — the in-repo grep cannot see out-of-repo consumers (operator scripts, deploy manifests elsewhere), which is exactly what class C exists for. Then delete the code path, the flag parsing, the tests for the dead combination, and the catalog row (move the row to a "removed" appendix or changelog so history survives). |
| experimental → **deleted** | The experiment lost. Same scrubbing as removal, but no change-control class-C gate: experimental flags have no external consumers by definition, so ordinary review suffices. Deleting a failed experimental flag is a success, not a failure — say so in the changelog so the next person knows it was tried (see **failure-archaeology**). |

**Failure mode of the lifecycle itself:** flags that live in `experimental` forever because promotion requires effort and nothing forces it. Countermeasure: the retirement plan date, plus a periodic catalog sweep (§3.4) that flags every experimental entry past its plan date.

### 3.4 CONFIG DRIFT — the first-class problem

**Definition:** config drift is any divergence between the catalog and reality — the doc says default 30, code says 60; the doc lists a flag that was deleted; a flag exists that the doc never heard of; production has a value nobody recorded.

Catalogs rot for structural reasons, not laziness: (a) the flag change and the doc live in different files, so nothing forces them to move together; (b) defaults get changed in hotfixes under time pressure; (c) flags are added by people who never read the catalog; (d) the catalog is prose, so nothing can check it mechanically.

**The re-verification discipline** attacks (d): every catalog entry carries a one-line **Verify** command that a human or model can paste to prove the flag still exists and (where feasible) its default. Categories, with real, tested syntax:

| Technique | Example Verify command | What a pass looks like |
|---|---|---|
| Grep the source of truth | `git grep -n 'RETRY_LIMIT' -- src/` | Hits at the read site and the default assignment; eyeball the default value in the hit line. |
| Grep the schema / defaults file | `git grep -nE 'retry_limit' -- config/schema.*` | The key exists in the schema with the documented default. |
| `--help` output diffing | `diff <(<TOOL> --help) docs/config/help-baseline.txt` | Empty diff. Regenerate the baseline (`<TOOL> --help > docs/config/help-baseline.txt`) deliberately, in the same commit as any flag change — an unexpected diff IS the drift alarm. (`<(...)` is bash process substitution; in plain POSIX sh, write to temp files and diff those.) |
| Dump effective config | `<TOOL> --print-config` (or the project's equivalent: `nginx -T`, `git config --list`, a `/debug/config` endpoint) | The running default matches the catalog. If the project has no config-dump facility, building one is a high-value task — see **diagnostics-and-tooling**. |
| Pickaxe for silent changes | `git log -S'RETRY_LIMIT' --oneline -- src/` | No commits newer than the Last-verified date. Any newer hit means re-read the change and update the row. |

Sweep cadence (candidate practice, tune to project pace): run every Verify command and refresh Last-verified dates (1) whenever the catalog is consulted and a row's date is older than ~90 days, (2) before every release, (3) whenever a config-shaped bug burned anyone. A row whose Verify command fails is drift confirmed: fix the row or the code the same day, while the discrepancy is understood.

**Heuristic trust rule:** treat any catalog row with a Last-verified date older than the newest `git log -S'<FLAG_NAME>'` hit as UNVERIFIED, no matter what it claims.

### 3.5 Flag interaction hazards

- **Combinatorial explosion.** N independent booleans = 2^N states; nobody tests 2^N states. Keep N small by retiring flags (§3.3) and record explicitly which combinations are supported. Untested combinations are unsupported by default — say so in the catalog.
- **Rule: experimental must not gate experimental.** An experimental flag must not enable, require, or change the meaning of another experimental flag unless the catalog records a written reason in both rows' interaction warnings. Two half-tested features multiplying each other's state space is how "it only crashes when both are on" bugs are born, and those cost days because each flag's owner tests their flag alone.
- **Precedence ambiguity.** When the same knob is settable via env var, config file, and CLI flag, the precedence order (conventionally CLI > env > file > built-in default, but verify — projects differ) must be stated once at the top of the catalog and validated by one test.
- **Meaning-shift interactions.** The nastiest class: flag A silently changes what flag B's value means (e.g. `CACHE_MODE=async` makes `CACHE_TTL` a hint instead of a bound). These MUST be in both rows' interaction warnings; they are invisible in any per-flag test.
- **Cross-service skew.** If two deployed services read the same flag, a flip that reaches them at different times creates a mixed state. Record "must flip atomically with <SERVICE>" as an interaction warning and treat the flip per **change-control**.

## 4. Worked example

**Illustrative example — all names and numbers fictional.** Project "Lanternfish", a log-ingestion daemon. Adding an experimental batching fast path.

Checklist walk: (1) Justification: "operators need to trade latency for throughput per site; no single constant fits." (2) Existing convention is `LF_`-prefixed env vars → name it `LF_ENABLE_BATCH_FASTPATH` (boolean, named for true-behavior, not `LF_NO_SLOWPATH`). (3) Default OFF → unset reproduces today's per-record path exactly. (4) Guard check: with it unset, the only new code executed is one `if (env-is-set)` test — pass. (5) `LF_BATCH_SIZE` (companion int, default 64, range 1–4096) crashes at boot on 0 or 5000 with `invalid LF_BATCH_SIZE: must be 1..4096`. (6) Startup log line: `config: LF_ENABLE_BATCH_FASTPATH=off LF_BATCH_SIZE=64`. (7) Test matrix: existing suite with flag off (unchanged), new `batch_fastpath_test` suite with flag on, plus the one recorded interaction row. (8–10) Catalog entries land in the same commit as the code, with `--help` baseline regenerated.

Catalog entry produced:

> **`LF_ENABLE_BATCH_FASTPATH`** — bool (env var). Default: `off` (unset; default lives in `src/config.c`, the only definition site). Status: experimental. Guard: unset → batching code fully skipped; kill-switch is unset + process restart, no deploy. Owner: ingest-team. Interactions: requires `LF_BATCH_SIZE` ≥ 1 when on; **must not be combined with experimental `LF_ENABLE_ZERO_COPY`** — recorded reason: both patch the writer path, combination untested, revisit after either promotes. Verify: `git grep -n 'LF_ENABLE_BATCH_FASTPATH' -- src/config.c` and `git log -S'LF_ENABLE_BATCH_FASTPATH' --oneline`. Last verified: 2026-07-06. Retirement plan: promote to production or delete by release 4.2 (two releases out).

Three months later the sweep runs the Verify command; pickaxe shows a newer commit that changed `LF_BATCH_SIZE`'s default from 64 to 128 in a hotfix. Drift confirmed and caught mechanically: the row is updated the same day, and the hotfix author is pointed at checklist item 8. Flipping the fast path ON for the production fleet is filed as a gated change under **change-control** — this skill only guarantees the catalog told the truth when the flip was proposed.

## 5. Instantiate for your project

Produce `<PROJECT>-config-and-flags` in the target repo. A Sonnet-class model can execute this unaided. Evidence bar: **no catalog row may be written from memory or inference — every field comes from a source line, a command output, or is marked `UNKNOWN`.**

**Step 1 — Discover the config surface.** Run each command from the repo root; every hit is a candidate catalog row. (All syntax below verified 2026-07-06 against git 2.x in bash.)

```bash
# Environment variables (covers Python/Node/C/C#/Java/Ruby readers):
git grep -nE 'getenv|process\.env|os\.environ|ENV\[|Environment\.GetEnvironmentVariable|System\.getenv' -- .

# CLI argument parsers (add the project's language's parser to this list):
git grep -nE 'add_argument|ArgumentParser|flag\.(Bool|String|Int|Duration)|cobra\.Command|clap|yargs|commander|GetOpt' -- .

# Config files and schemas checked into the repo:
git ls-files | grep -iE '\.(json|ya?ml|toml|ini|cfg|conf|env(\.[a-z]+)?)$'

# Feature-flag services: grep for the SDK the project uses
# (LaunchDarkly, Unleash, Flagsmith, a homegrown flags table...):
git grep -niE 'launchdarkly|unleash|flagsmith|featureflag|feature_flag' -- .
```

Also check: build-time defines (`-D` in build scripts), deploy manifests (Kubernetes `env:` blocks, systemd `Environment=`, Dockerfiles `ENV`), and CI variable definitions — these are config axes even though the app code never spells them.

**Step 2 — For each candidate, extract the row fields from source.** Read the definition site for type/default/validation. For default, quote the exact line. For owner, use `git log --format='%an %ae' -n 5 -- <FILE>` on the defining file as a starting hypothesis, then confirm with a human or team doc — blame is evidence of authorship, not ownership. For status: a flag referenced in production deploy manifests is de facto `production` regardless of what anyone remembers.

**Step 3 — Write the Verify command for each row and RUN it once.** A Verify command that has never passed is not evidence. The run date becomes the first Last-verified value.

**Step 4 — Fill the project skill from this skeleton:**

```markdown
---
name: <PROJECT>-config-and-flags
description: <one sentence: the config surfaces this project actually has, and where the catalog lives>
---
# <PROJECT> configuration catalog and flag rules
## Config surfaces (verified <DATE>)
<env vars: prefix convention | config files: paths + format | CLI: entry points | flag service: name or NONE>
## Precedence order
<CLI > env > file > default — AS TESTED BY <TEST-FILE>, not as assumed>
## Naming convention
<observed pattern; cite 3 existing examples>
## Catalog
<one §3.1-format entry per axis; every field sourced or UNKNOWN>
## Project-specific ADD-A-FLAG deltas
<anything this project adds to §3.2 — e.g. "also update <DEPLOY-MANIFEST>", "flag service changes need <TEAM> review">
## Known interaction warnings
<each with the commit/incident that proved it — link, don't retell; details belong in failure-archaeology>
## Sweep log
<date | who/what ran the sweep | drift found>
```

**Step 5 — Wire the forcing functions.** (a) Add "catalog updated?" to the PR checklist or a CI grep that fails when a new `getenv`-family hit has no catalog row (candidate practice — needs tuning to avoid false positives on test files). (b) Schedule the §3.4 sweep cadence in the project's routine-maintenance doc. (c) Cross-link the project's **change-control** skill so production flag flips route through its gate.

**Step 6 — Record gaps honestly.** Every `UNKNOWN` and `UNVALIDATED` in the catalog is a listed work item at the bottom of the skill, not silently dropped.

## 6. Provenance and maintenance

Authored 2026-07-06 against no specific project; all project-flavored content is placeholder or labeled illustrative.

Volatile parts and re-verification one-liners:

| Volatile item | Re-verify with |
|---|---|
| `git grep -nE`, `git log -S`, `git ls-files` syntax | `git grep --help`, `git log --help`, `git ls-files --help` (verified working 2026-07-06, git 2.x) |
| Process substitution `<(...)` in the help-diff recipe | bash-only; confirm shell with `echo $0` — fall back to temp files under POSIX sh |
| Env-var/parser grep patterns (§5 step 1) | Patterns are heuristics, not exhaustive — extend per language; re-test against a known flag in the target repo before trusting a zero-hit result |
| Feature-flag vendor names (LaunchDarkly, Unleash, Flagsmith) | Ecosystem churns; grep for whatever SDK the target repo's manifest imports instead of this list |
| Sweep cadence numbers (~90 days) and precedence convention | Heuristics — instantiated copies must replace with project-observed values |

Instantiated copies must add their own provenance block: date of each discovery run, git revision the catalog was extracted at, and the sweep log required by the skeleton.
