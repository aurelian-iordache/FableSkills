---
name: run-and-operate
description: Load this skill when you must run, deploy, or operate a project day-to-day — starting services, running pipelines, deploying to an environment, finding where output files land, reading logs, or writing/executing an operational runbook. Triggers include "how do I run/deploy this", "where does the output go", "is it safe to re-run", "roll back the deploy", "what does this script do", or any command that touches a production path. Delivers the COMMAND ANATOMY documentation format, data/artifact conventions, the OUTPUT MAP, deploy/rollback runbook discipline, and operational safety rails.
---

# run-and-operate — Run/Deploy Runbooks and Operational Safety

## 1. Purpose

This skill makes you able to (a) document every operational command so a stranger can run it
safely, (b) know where every generated artifact lives and whether it is regenerable or precious,
(c) execute deploys with pre-flight checks, verified success criteria, and a rehearsed rollback,
and (d) refuse to run any command whose blast radius you cannot state.

## 2. When to use / When NOT to use

Use when: running or scheduling the project's commands, deploying, cleaning up generated data,
reading logs, or writing the project-specific operations skill.

| If instead you need... | Use sibling skill |
|---|---|
| To build the project or recreate the dev environment from scratch | `build-and-env` |
| To understand or change a config option or feature flag | `config-and-flags` |
| To measure/instrument behavior rather than just run it | `diagnostics-and-tooling` |
| To debug why a run failed (root-causing, not operating) | `debugging-playbook` |
| To decide whether a change is safe to ship at all | `change-control` |
| To judge whether output is *correct*, not just present | `validation-and-qa` |

Boundary rule: `build-and-env` owns "make the machine able to run it"; **this skill owns
"run it, and live with the consequences."** One home per fact — link, don't copy.

## 3. Core doctrine

### 3.1 Definitions (first use)

- **Operational surface**: the complete set of commands a human or CI runs against the project —
  start/stop, deploy, migrate, backfill, clean, publish.
- **Artifact**: any file or record a command produces — build outputs, datasets, reports, logs,
  database rows, uploaded packages.
- **Idempotent**: running the command twice yields the same end state as running it once.
  Non-idempotent commands (append-only imports, "send emails", "charge cards") are the dangerous ones.
- **Dry run**: a mode that prints what *would* happen without doing it (e.g. `rsync --dry-run`,
  `terraform plan`, `kubectl apply --dry-run=client -f <FILE>`, `aws s3 sync --dryrun ...` —
  note AWS spells it without a hyphen).
- **Runbook**: a step-by-step procedure with expected observations at each step, written so
  someone who did not write it can execute it under stress.

### 3.2 COMMAND ANATOMY — the documentation format

Every operational command in the project skill gets one anatomy block. No block, no running it
in production. The format:

```markdown
### <command name>

    <exact copy-pasteable command line>

- **What it does**: one plain-language sentence, including side effects.
- **Flags that matter**: each flag that changes behavior, with the default and when to override.
  Omit cosmetic flags. If a flag guards a destructive path (e.g. `--force`, `--prune`), say so in bold.
- **Output lands in**: exact paths/URLs/tables it writes. "Nothing persisted" is a valid answer.
- **Expected duration**: order of magnitude (seconds / ~2 min / ~1 h). A run at 10x expected
  duration is a failure signal, not patience territory.
- **Success looks like**: the exact final line / exit code / artifact that proves it worked.
- **Failure looks like**: known failure signatures and what each means (link debugging-playbook rows).
- **Idempotent / safe to re-run?**: YES / NO / CONDITIONAL — with the condition spelled out.
  If NO: what state must be cleaned before retrying.
```

Heuristic ordering: document the commands people run daily first, then the scary quarterly ones —
the scary ones are precisely the ones nobody remembers, so their anatomy blocks earn the most.

### 3.3 Data and artifact conventions

Answer these five questions once, in writing, per project:

1. **Where does generated data live?** One canonical root per class (e.g. `<REPO>/out/` for
   regenerable build products, `<DATA-ROOT>/` for datasets, `<LOG-DIR>/` for logs). Anything
   written outside the canonical roots is a bug in the producing command — file it.
2. **Naming scheme**: encode *what, when, and from-what* in the name. Candidate practice:
   `<ARTIFACT>-<YYYYMMDD-HHMMSS>-<GIT-SHORT-SHA>.<EXT>` — sortable, traceable to the code that
   produced it. Never `final_v2_REAL.csv`.
3. **Regenerable vs precious**: every artifact class is labeled one of:
   - **REGENERABLE** — reproducible from source + inputs by a named command. Deletable freely.
   - **PRECIOUS** — cannot be recreated (raw captures, user uploads, signed releases, incident
     logs). Backed up before ANY command that could touch it; never in the path of a `clean` target.
   - **EXPENSIVE** — technically regenerable but costs hours/money. Treat as precious unless you
     have explicit budget to regenerate.
4. **Retention rules**: per class, how long kept and what deletes it (a documented command or
   cron, never ad-hoc `rm`). Example inspection command before any cleanup:
   `find <LOG-DIR> -name '*.log' -mtime +30 -print` — review the list, then and only then add `-delete`.
5. **Who else reads it**: no artifact convention change (path, name, format) without checking the
   OUTPUT MAP consumers column first.

### 3.4 The OUTPUT MAP

One table, kept next to the command anatomies, answering "what made this file and who needs it":

| Artifact | Producing command | Path / location | Consumer(s) | Class |
|---|---|---|---|---|
| `<what it is>` | `<anatomy block name>` | `<canonical path>` | `<human, CI job, downstream cmd>` | REGENERABLE / PRECIOUS / EXPENSIVE |

Rules: every anatomy block's "Output lands in" entries appear here; every row's producing command
has an anatomy block; a row with consumer "unknown" is a to-do, not an acceptable steady state.
The OUTPUT MAP is the first thing to check before deleting, moving, or renaming anything.

### 3.5 Deployment runbook discipline

A deploy runbook has four mandatory parts. Writing only part 2 is how outages happen.

**A. Pre-flight checklist** (each item checkable, with the command):
- [ ] On the intended commit: `git log -1 --oneline` matches what you mean to ship.
- [ ] Working tree clean: `git status --short` prints nothing.
- [ ] CI green on that exact commit (e.g. `gh run list --commit $(git rev-parse HEAD)`).
- [ ] Target environment confirmed and echoed out loud (see safety rails, 3.6).
- [ ] You know the current live version, recorded where you can see it during rollback
  (e.g. `git tag -l 'release-*' | tail -1`, or the platform's "current release" command).
- [ ] Rollback procedure (part D) read *now*, before deploying — not discovered mid-incident.
- [ ] Config/flag deltas between environments reviewed → `config-and-flags`.

**B. The deploy itself**: the anatomy block for the deploy command, plus the expected
step-by-step console narrative ("you will see X, then Y; step Z takes ~3 min and looks hung — it isn't").

**C. Post-deploy verification with expected observations.** "It deployed" is not verification.
Each check pairs a command with the observation that counts as pass:

| Check | Command (illustrative) | Expected observation |
|---|---|---|
| Version live | `curl -s <HEALTH-URL>` | JSON contains the new version/sha |
| Process healthy | `kubectl rollout status deployment/<NAME>` or `systemctl status <SVC>` | "successfully rolled out" / `active (running)` |
| No new errors | log tail for 5 min (see 3.7) | error rate matches pre-deploy baseline |
| Key user path works | one scripted end-to-end request | known-good response body |

**D. Rollback procedure — REHEARSED, not just written.** A rollback that has never been executed
is a hypothesis. Discipline:
- The rollback is a single documented command sequence (e.g. `kubectl rollout undo
  deployment/<NAME>`, or redeploy of the previous tag), with its own anatomy block.
- It has been **actually executed at least once** against a staging/non-prod environment, and the
  runbook records the date of the last rehearsal. A rehearsal older than the last major
  infrastructure change is expired — re-rehearse.
- It states what rollback does NOT undo (database migrations, sent emails, published packages) and
  the separate procedure for each, or the explicit statement "no forward-only side effects".
- Decision rule written in advance: the observation that triggers rollback (e.g. "error rate >2x
  baseline for 5 minutes") — decided calmly, not negotiated during the incident.

### 3.6 Operational safety rails

These are unconditional. They cost seconds and prevent the incidents that cost weekends.

1. **Dry-run first.** If the command has a dry-run/plan/no-op mode, run it first and read the
   output, every time the inputs changed since the last real run. If it has no dry-run mode and is
   destructive, build the preview yourself (e.g. run the `find ... -print` before the
   `find ... -delete`; run `SELECT` before `DELETE`).
2. **The irreversibility test.** Before pressing enter on ANY state-changing command, answer in
   one sentence: *"Can I undo this, and how?"* If the answer is "I can't" or "I don't know", stop —
   either establish the undo (backup, snapshot, previous tag) or escalate. This is the single
   highest-value habit in this skill.
3. **Echo the target before operating on prod paths.** Never let an environment name live only in
   a variable. Print it and read it:
   `echo "DEPLOY TARGET: $DEPLOY_ENV -> $DEPLOY_HOST"` — then run the command on the next line.
   In scripts, require an explicit `--env <NAME>` argument and refuse to default to production.
4. **One terminal, one environment.** Do not keep a prod shell and a staging shell side by side;
   the wrong-window paste is a classic. Close the prod session the moment you are done.
5. **Non-idempotent commands get a written ledger.** Before running (per its anatomy block:
   "safe to re-run? NO"), note timestamp + inputs somewhere durable, so a crash mid-run leaves a
   record of what may be half-done.
6. **10x-duration rule.** A command running 10x its documented expected duration is treated as
   failed: capture its output, then investigate — do not wait indefinitely and do not blind-kill
   without capturing.

### 3.7 Log locations and how to read them

Document, per service/command: where logs go, rotation policy, and the two or three read recipes
that matter. Generic recipes (verify against your stack):

- Follow live: `tail -f <LOG-FILE>`; containers: `docker compose logs -f --tail 100 <SERVICE>`;
  systemd: `journalctl -u <SVC> -f`.
- Recent window after an incident: `journalctl -u <SVC> --since "1 hour ago" --no-pager`.
- First error, not last: errors cascade; scroll to the FIRST occurrence —
  `grep -n -i -m 5 'error\|fatal\|panic' <LOG-FILE>` gives the first five with line numbers.
- Correlate to a deploy: note deploy timestamps in the runbook so "did errors start at deploy
  time?" is answerable in one grep by timestamp.
- Record in the project skill what a HEALTHY log looks like (known-benign warnings included) —
  otherwise every reader re-investigates the same harmless noise. For adding new instrumentation
  → `diagnostics-and-tooling`.

### 3.8 Failure modes of this method

- **Anatomy blocks written from memory, not from a run.** They encode what the author believes,
  not what happens. Rule: every field of an anatomy block is filled from an actual observed run.
- **The OUTPUT MAP rots silently.** Any PR that adds/moves an artifact must touch the map;
  enforce via review checklist (→ `change-control`).
- **Rollback rehearsed once, at project start, never again.** Date-stamp rehearsals; treat an
  expired rehearsal as no rehearsal.
- **Safety rails skipped "because it's a small change."** Blast radius does not scale with diff
  size. Rails are unconditional or they are decoration.

## 4. Worked example (illustrative — all names fictional)

Project "tidefall": a nightly data pipeline plus a small web API, deployed to a single VM.

### Anatomy block: nightly ingest

    python -m tidefall.ingest --date 2026-07-05 --source ferry-feed

- **What it does**: downloads one day of ferry telemetry and writes a cleaned parquet file.
- **Flags that matter**: `--date` (required, one day per run); `--source` (default `ferry-feed`);
  **`--overwrite` re-downloads and clobbers an existing day — destructive to EXPENSIVE data.**
- **Output lands in**: `/srv/tidefall/data/clean/ferry-<YYYYMMDD>-<GITSHA>.parquet`; log to
  `/srv/tidefall/logs/ingest-<YYYYMMDD>.log`.
- **Expected duration**: ~8 minutes. Upstream throttles after 20:00 UTC — runs then take ~25 min (known, benign).
- **Success looks like**: final line `INGEST OK rows=~480000 file=...` and exit 0.
- **Failure looks like**: `HTTP 403` → feed token expired (see config-and-flags: `FERRY_TOKEN`);
  `rows=0` with exit 0 → upstream outage, file is valid-but-empty, re-run next morning.
- **Idempotent / safe to re-run?**: CONDITIONAL — yes without `--overwrite` (it skips existing
  days); with `--overwrite` it destroys the prior download (EXPENSIVE: ~1 h to refetch).

### OUTPUT MAP (excerpt)

| Artifact | Producing command | Path | Consumer(s) | Class |
|---|---|---|---|---|
| Clean daily parquet | nightly ingest | `/srv/tidefall/data/clean/` | report job, API cache warmer | EXPENSIVE |
| Weekly report HTML | `make report` | `/srv/tidefall/out/report-<YYYYMMDD>.html` | ops email cron | REGENERABLE |
| Raw feed captures | nightly ingest (`--keep-raw`) | `/srv/tidefall/data/raw/` | nobody routinely; audits | PRECIOUS |

### Deploy + rollback (condensed)

Pre-flight: `git log -1 --oneline` shows the release commit; CI green; `echo "DEPLOY TARGET:
prod-vm (tidefall.example.internal)"`. Deploy: `make deploy ENV=prod` (~90 s; prints
`RELEASE r2026-07-06a ACTIVE`). Verify: `curl -s https://tidefall.example.internal/healthz`
returns `{"version":"r2026-07-06a","ok":true}`; tail API log 5 min, error rate at baseline.
Rollback: `make deploy ENV=prod RELEASE=r2026-06-28b` (previous tag, recorded in pre-flight) —
last rehearsed 2026-06-30 on staging, 70 s, does not undo DB migrations (separate procedure:
`migrations.md`). Trigger rule: any 5xx on `/healthz`, or error rate >2x baseline for 5 min.

## 5. Instantiate for your project

Goal: produce `.claude/skills/<PROJECT>-run-and-operate/SKILL.md`. A Sonnet-class model executes
this alone. **Evidence bar: no anatomy block field may be filled without an observed run or an
authoritative source (the script's own code, CI config); mark anything unobserved `UNVERIFIED —
do not rely on this in production`.**

1. **Mine the operational surface** (run what applies; each is real syntax, verified 2026-07-06
   where marked):
   - Scripts dirs: `ls scripts/ bin/ tools/ ops/ 2>/dev/null` — read each script's header/usage.
   - package.json scripts: `npm pkg get scripts` and `npm run` (both list scripts; verified).
     Equivalent one-liner if npm is absent:
     `node -e "const s=require('./package.json').scripts; for (const [k,v] of Object.entries(s)) console.log(k,'->',v)"` (verified).
   - Makefile targets: read the Makefile first (comments carry intent). Mechanical list via the
     database dump — `make -qp | awk -F':' '/^[a-zA-Z0-9][^$#\/\t=]*:([^=]|$)/ {split($1,A,/ /);for(i in A)print A[i]}' | sort -u`
     (`-q` = question mode, runs nothing; `-p` = print rule database; awk idiom verified against a
     sample Makefile).
   - CI deploy jobs: `grep -riE 'deploy|release|publish' .github/workflows/ .gitlab-ci.yml Jenkinsfile 2>/dev/null` —
     CI is ground truth for the *real* deploy command and its environment variables.
   - Containers: `ls Dockerfile* docker-compose*.yml compose*.yml 2>/dev/null`; list services with
     `docker compose config --services`; read entrypoints/CMD for the true start command.
   - Other manifests: `pyproject.toml` `[project.scripts]`, `Procfile`, `justfile`, `Taskfile.yml`,
     crontabs, systemd units in the repo.
2. **Verify command syntax before documenting it.** Run each discovered command with `--help`
   (or the tool's equivalent) and, where safe, a dry-run. Do not transcribe a flag you have not
   seen in help output or a real run.
3. **Run each routine command once in a safe environment** and fill its anatomy block (3.2) from
   observation: time it, capture the success line, note every path it wrote (diff the output dirs
   before/after: `find <OUT-DIR> -newer <SCRATCH-DIR>/marker -print` after
   `touch <SCRATCH-DIR>/marker`, where `<SCRATCH-DIR>` is any writable temp directory).
4. **Build the OUTPUT MAP** (3.4) from those observed writes plus `git log --oneline -- <OUT-DIR>`
   history and grep for readers of each path. Classify every row REGENERABLE / PRECIOUS / EXPENSIVE;
   when unsure, PRECIOUS.
5. **Write the deploy runbook** (3.5 A–D) from the CI job or deploy script — then **rehearse the
   rollback on a non-prod environment and date-stamp it**. Until rehearsed, the runbook must carry
   the banner `ROLLBACK UNREHEARSED`.
6. **Document logs** (3.7): locate them from the observed runs, record one healthy excerpt and the
   known-benign warnings.
7. **Skeleton to fill** (section order for the project skill):

   ```markdown
   ---
   name: <PROJECT>-run-and-operate
   description: <triggers for running/deploying <PROJECT>>
   ---
   # Operational surface overview (one table: command -> purpose -> danger level)
   # Command anatomies (3.2 format, one per command, observed-run evidence only)
   # Data & artifact conventions (roots, naming, retention; 3.3 questions answered)
   # OUTPUT MAP (3.4 table)
   # Deploy runbook (pre-flight / deploy / verify / rollback + last-rehearsed date)
   # Safety rails (3.6, plus project-specific irreversible commands listed by name)
   # Logs (locations, read recipes, healthy-log excerpt)
   # Provenance (who observed what, when, on which commit)
   ```

8. **Cross-link**: environment setup → `<PROJECT>-build-and-env`; every env var / flag mentioned →
   `<PROJECT>-config-and-flags`; instrumentation → `<PROJECT>-diagnostics-and-tooling`.

## 6. Provenance and maintenance

Authored 2026-07-06 against no specific project; all project facts in section 4 are fictional.
Verified by execution on the authoring machine: `npm pkg get scripts`, `npm run` (script listing),
the `node -e` package.json one-liner, and `find -mtime` syntax. The Makefile-target awk program
was verified against sample `make -qp` output only — `make` itself was not executable on the
authoring machine; re-check the full pipeline with `make --help` before relying on it.
Volatile parts and one-line re-verification:

- Tool flags (`make -q/-p`, `docker compose logs --tail`, `kubectl --dry-run=client`,
  `aws s3 sync --dryrun`, `rsync --dry-run`, `journalctl -u`): re-check with `<TOOL> --help`
  before trusting in a new environment — these were not all executable on the authoring machine
  and ecosystems drift.
- Ecosystem manifest conventions (package.json scripts, justfile/Taskfile, Compose file names):
  re-survey when instantiating in a stack newer than 2026.

Instantiated copies MUST add their own provenance: commit sha observed against, dates of each
observed run, and the rollback rehearsal date.
