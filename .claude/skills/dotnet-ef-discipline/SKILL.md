---
name: dotnet-ef-discipline
description: >-
  STACK TIER. Load this skill when working on a C#/.NET project that uses Entity Framework Core and you
  must add/remove/apply a migration, resolve a migration merge conflict, review a schema
  change, decide how a production database gets migrated, chase an N+1 or slow-query problem,
  or fix DbContext lifetime/threading errors. Trigger phrasings: "add a migration", "the
  model snapshot has a merge conflict", "pending model changes", "can I edit this migration?",
  "database update failed", "which database is this pointing at?", "the EF/LINQ query is
  slow or fires hundreds of SQL statements (N+1)", "DbContext is disposed / used on another thread".
  Delivers the verified migration lifecycle commands, a trap catalog in
  Symptom/Cause/Fix/Tell format, the which-database pre-flight, production schema-change
  rules (idempotent scripts and bundles, never `database update` at prod), and
  query/DbContext discipline.
---

# dotnet-ef-discipline — EF Core Migrations as Gated Changes

## Purpose

This skill makes you able to (1) run the EF Core migration lifecycle with correct, verified
commands, (2) treat every migration as a gated change with the right review class per
`change-control`, (3) recognize and defuse the classic migration traps (snapshot merge
conflicts, out-of-order migrations, silent data loss, untested `Down()`), (4) never point a
migration at the wrong database, and (5) apply baseline query/DbContext discipline so the
data layer stays fast and thread-safe.

Version ground truth: everything marked **[verified]** below was executed against
**EF Core 10.0.9 / dotnet-ef 10.0.9 / .NET SDK 10.0.301 on 2026-07-06**, using the SQLite
provider (`Microsoft.EntityFrameworkCore.Sqlite` 10.0.9) end to end and the SQL Server
provider (`Microsoft.EntityFrameworkCore.SqlServer` 10.0.9) for script generation.
Facts sourced from official docs but not executed here are marked **[docs]**.

## When to use / When NOT to use

Use when: adding or reviewing an EF Core migration; resolving migration/model-snapshot
conflicts after a merge or rebase; planning how schema changes reach staging/production;
debugging EF query performance or DbContext lifetime errors; setting up EF tooling in a
fresh clone.

| If instead you need... | Use sibling skill |
|---|---|
| The general change-classification and gating system (this skill maps migrations onto it) | `change-control` |
| SQL Server server-side work: DMVs, indexes, statistics, backup/restore proof | `sql-server-operations` |
| SDK pinning (`global.json`), tool manifests, restoring a buildable environment | `build-and-env` |
| Diagnosing a bug that is not migration/EF-specific | `debugging-playbook` |
| What counts as proof that a migration or query fix works | `validation-and-qa` |
| Cataloging connection strings and other config axes | `config-and-flags` |
| Measuring query performance instead of eyeballing it | `diagnostics-and-tooling`, `proof-and-analysis` |
| TypeScript API-client types, front-end consumption of the API | `react-frontend-discipline` |
| The HTTP surface in front of the data layer: DTO wire contracts, ProblemDetails/error shapes, OpenAPI, API breaking-change classes | `aspnet-api-discipline` |
| General C# craft outside EF: pattern judgment, smallest-diff discipline, async idiom, analyzer enforcement | `csharp-code-discipline` |
| Whether this migration/schema problem was fought before | `failure-archaeology` |

Boundary rule: this skill ends at the database boundary — what EF generates and how it is
applied. Index tuning, DMV diagnostics, and backup/restore live in `sql-server-operations`.

## Core doctrine

### Definitions (used throughout)

- **Migration**: a generated C# class pair (`<TIMESTAMP>_<NAME>.cs` + `.Designer.cs`) under
  `Migrations/` containing `Up()` (apply) and `Down()` (revert) operations.
- **Model snapshot**: `<CONTEXT>ModelSnapshot.cs`, a single generated file recording the
  model shape *after the latest migration*. EF diffs the current model against it to
  scaffold the next migration. It is the file that merge conflicts hit.
- **`__EFMigrationsHistory`**: the table EF creates in the target database listing applied
  migration IDs. "Applied" means "present in this table".
- **Provider**: the database-specific package (`Microsoft.EntityFrameworkCore.Sqlite`,
  `.SqlServer`, `Npgsql.EntityFrameworkCore.PostgreSQL`, ...). Migrations are scaffolded
  FOR a provider; they do not port across providers.
- **Design-time**: the `dotnet ef` tool loading your project to scaffold/apply migrations.
  Requires the `Microsoft.EntityFrameworkCore.Design` package in the startup project.

### 1. Tooling setup — local tool manifest, never global [verified]

Pin `dotnet-ef` per-repo so every machine and CI runs the same version (rationale and
`global.json` SDK pinning: `build-and-env`):

```sh
dotnet new tool-manifest              # creates .config/dotnet-tools.json — commit it
dotnet tool install dotnet-ef         # records exact version in the manifest
dotnet tool restore                   # what other clones/CI run to get the pinned version
dotnet ef --version                   # sanity check
```

Never `dotnet tool install --global dotnet-ef`: a global install drifts from the repo and
masks the manifest. The `dotnet ef` commands below all require the manifest restored and
`Microsoft.EntityFrameworkCore.Design` referenced by the startup project.

### 2. The migration lifecycle [verified end to end, EF Core 10.0.9]

All commands run from the project directory (or add `--project <PATH> --startup-project
<PATH>` in multi-project solutions).

| Step | Command | What you saw when it worked (verified output) |
|---|---|---|
| Check drift | `dotnet ef migrations has-pending-model-changes` | Exit 0 + `No changes have been made to the model since the last migration.` — or exit 1 + `Changes have been made to the model since the last migration. Add a new migration.` |
| Scaffold | `dotnet ef migrations add <NAME>` | `Done. To undo this action, use 'ef migrations remove'` — and READ the generated file before anything else |
| Inspect state | `dotnet ef migrations list` | Applied migrations plain; unapplied suffixed `(Pending)`. Connects to the database. |
| Apply locally | `dotnet ef database update` | `Applying migration '<TIMESTAMP>_<NAME>'.` then `Done.` |
| Test the Down | `dotnet ef database update <PREVIOUS-MIGRATION-NAME>` | `Reverting migration '<TIMESTAMP>_<NAME>'.` then `Done.` (`dotnet ef database update 0` reverts ALL migrations) |
| Undo a scaffold | `dotnet ef migrations remove` | Deletes the latest migration files AND prints `Reverting the model snapshot.` Only works if the migration is not applied — revert it first. Never delete migration files by hand; hand-deletion leaves the snapshot wrong. |
| Script for review | `dotnet ef migrations script -o all.sql` (add `--idempotent` on SQL Server — see trap T7 for SQLite) | SQL file; idempotent form wraps each migration in `IF NOT EXISTS (SELECT * FROM [__EFMigrationsHistory] WHERE ...)` guards |
| Package for deploy | `dotnet ef migrations bundle --output efbundle.exe` | Self-contained executable (~34 MB observed); run it as `./efbundle.exe --connection "<CONN>"`; passing migration argument `0` reverts all |
| Pre-flight target | `dotnet ef dbcontext info` | Prints `Type:`, `Provider name:`, `Database name:`, `Data source:` — the "which DB am I about to touch" check |
| Full DDL of model | `dotnet ef dbcontext script` | CREATE statements for the current model (not the migration history) — useful for review diffs |

The routine loop, in order: `has-pending-model-changes` → edit model → `migrations add` →
**read the generated `Up()`/`Down()`** → `database update` → run `<TEST-CMD>` →
`database update <PREVIOUS>` (prove `Down()` works) → `database update` again → commit the
migration files + snapshot together with the model change.

### 3. Migrations are gated changes — the class map

Per `change-control`'s taxonomy, classify every migration before writing it:

| Migration content | Class | Consequence |
|---|---|---|
| Additive: new table, new nullable column | **C** by default — B only if the project has a written compatibility policy (`change-control` §1 rule of thumb) | Contract-owner review; rollback plan = the tested `Down()` |
| New/changed index via migration | **B** (behavioral: plans, locking, write cost — not a consumer contract) | Measured before/after reads per `sql-server-operations` §3.5; prod application still gated per `change-control` |
| Column type change, NOT NULL tightening, rename | **C**, treat as X if data is transformed | Requires a written data-preservation plan in the PR |
| Column/table DROP, destructive data rewrite | **X** (irreversible — `git revert` does not restore data) | Full X gate: rehearsal on a prod-snapshot copy, named recovery mechanism, scheduled window |

Two rules that follow directly:

- **Production never sees `dotnet ef database update`.** The dev loop command applies
  whatever the local build contains, with no review artifact. Production and staging get a
  reviewed artifact: an idempotent script (`migrations script --idempotent`, applied by the
  DBA/pipeline — see `sql-server-operations`) or a migration bundle (`migrations bundle`,
  versioned, checksummed, run with an explicit `--connection`). The artifact is what got
  reviewed; the artifact is what runs.
- **Migration and dependent code deploy separately when rollback matters.** Rolling deploys
  mean old code and new schema coexist; design additive-first (add nullable column → deploy
  code → backfill → tighten) rather than one big destructive step. This is the
  expand/contract pattern **[docs]** — label any project-specific sequencing in the
  instantiated skill.

### 4. Trap catalog (Symptom / Cause / Fix / Tell)

Index — find your trap by what you are seeing:

| You are seeing | Trap |
|---|---|
| Git conflict markers in `*ModelSnapshot.cs` | T1 |
| Migration sorts before an already-applied one after a merge | T2 |
| Edited a migration and nothing changed / environments diverge | T3 |
| Column drop / type change lost data with no warning anyone saw | T4 |
| Rollback (`database update <PREVIOUS>`) throws or loses data | T5 |
| `PendingModelChangesWarning` on another machine / in CI | T6 |
| Works on SQLite, fails on SQL Server (or `--idempotent` refuses) | T7 |
| Tool output disagrees with the files on disk (`--no-build`) | T8 |

**T1 — Model-snapshot merge conflict.**
- Symptom: git conflict markers in `<CONTEXT>ModelSnapshot.cs` after merging two branches
  that each added a migration.
- Cause: the snapshot is a single generated file recording "model after latest migration";
  two branches both regenerated it.
- Fix: do NOT hand-merge the generated code. Accept the other branch's snapshot
  (`git checkout --theirs`/`--ours` as appropriate for your merge direction), keep both
  branches' migration `.cs`/`.Designer.cs` files, then regenerate: revert-and-recreate your
  own migration on top (T2 recipe). The snapshot must equal "model after the final
  migration in the merged order" — only the tool can guarantee that.
- Tell: the conflicted file is `*ModelSnapshot.cs` and both sides' hunks are generated
  builder calls, not human code.

**T2 — Out-of-order migrations across branches (and the rebase-the-migration recipe).**
- Symptom: after merge, `dotnet ef migrations list` shows your migration timestamped
  BEFORE an already-applied one, or `database update` behaves as if your model change is
  missing; snapshot no longer matches the sum of migrations.
- Cause: migration order is the filename timestamp from when each author scaffolded, not
  merge order. Your migration was scaffolded against a snapshot that no longer reflects the
  branch tip.
- Fix — the rebase recipe **[verified mechanics: `remove` deletes files and prints
  `Reverting the model snapshot.`]**:
  1. If you applied it locally: `dotnet ef database update <MIGRATION-BEFORE-YOURS>`.
  2. `dotnet ef migrations remove` (removes your migration, restores the snapshot).
  3. Merge/rebase so the other branch's migrations are present.
  4. `dotnet ef migrations add <NAME>` again — it now scaffolds against the correct
     snapshot, with a fresh (latest) timestamp.
  5. `dotnet ef database update`, re-run `<TEST-CMD>`.
- Tell: `git log --oneline -- <MIGRATIONS-DIR>` shows the merged migration landed after
  yours in git history but sorts before it by filename timestamp.

**T3 — Editing an already-applied migration.**
- Symptom: your edit "does nothing" on databases that already ran the migration
  (dev machines, staging, prod all silently diverge from the code).
- Cause: applied = its ID is in `__EFMigrationsHistory`; EF will never re-run it **[docs]**. The edit
  only affects databases that have not applied it yet — you now have two schema realities.
- Fix: never edit an applied migration's operations. Write a NEW migration that makes the
  correction. (Editing an *unapplied, unmerged* migration you just scaffolded is fine —
  that is the moment to add data-preservation SQL via `migrationBuilder.Sql(...)`.)
- Tell: `dotnet ef migrations list` shows the migration without `(Pending)` anywhere it
  matters, or it exists on `<MAIN-BRANCH>` — treat "merged" as "applied somewhere".

**T4 — Silent data loss in scaffolded operations.** [verified]
- Symptom: a column drop or type change ships and data is gone; nobody remembers a warning.
- Cause: EF prints the warning ONCE, at scaffold time, on the author's terminal:
  `An operation was scaffolded that may result in the loss of data. Please review the
  migration for accuracy.` It does not recur at `database update` time and no CI step sees
  it unless you build one.
- Fix: the scaffold warning gates the author: on seeing it, classify the migration X per
  §3 and say so in the PR. Reviewers: grep the diff for `DropColumn|DropTable|AlterColumn`
  — a hit is a mandatory stop-and-classify, not proof of loss (widening AlterColumns are
  safe; narrowing ones are not). Heuristic: treat every hit as lossy until argued
  otherwise in the PR.
- Tell: `grep -n "DropColumn\|DropTable\|AlterColumn" <MIGRATIONS-DIR>/<NEW-FILE>.cs`
  is non-empty.

**T5 — `Down()` that was never tested.**
- Symptom: rollback night: `dotnet ef database update <PREVIOUS>` (or the bundle with the
  previous migration as its argument) throws, or "succeeds" but loses data — the rollback
  plan was fiction.
- Cause: scaffolded `Down()` is a best-effort inverse; for destructive `Up()` operations it
  cannot restore data (the inverse of DropColumn is AddColumn — empty). Nobody ran it.
- Fix: the lifecycle in §2 includes the round-trip: apply → revert to previous → re-apply,
  on a scratch DB, before the PR. For X-class migrations where `Down()` cannot restore
  data, the PR's rollback plan must name a real mechanism (backup restore — see
  `sql-server-operations`) and say "Down() does not restore data" explicitly.
- Tell: PR says "rollback: revert the migration" for a migration containing `DropColumn` —
  that plan is impossible; block it (per `change-control`'s X checklist).

**T6 — Model drift: code changed, no migration scaffolded.** [verified]
- Symptom: works locally (where you last updated), but `dotnet ef database update` on
  another machine throws `PendingModelChangesWarning`: `The model for context '<CONTEXT>'
  has pending changes. Add a new migration before updating the database.` — or worse, on
  EF Core 8 and earlier the update proceeds and runtime queries hit missing columns
  **[docs — EF Core 9 made this warning throw by default; re-verify on the installed
  major]**.
- Cause: someone edited the model and committed without scaffolding a migration.
- Fix: `dotnet ef migrations add <NAME>` to capture the drift; inspect it — it documents
  exactly what changed.
- Tell / CI gate: `dotnet ef migrations has-pending-model-changes` — exit code 0 clean,
  **exit code 1 with `Changes have been made to the model since the last migration.`**
  [verified, EF Core 10.0.9]. Put it in CI as a required check. The subcommand exists as of
  EF Core 8 **[docs]**; confirm on older repos with `dotnet ef migrations --help`.

**T7 — Provider differences bite the deploy path.** [verified where marked]
- Symptom: a command or migration that works in dev (SQLite) fails against SQL Server, or
  vice versa.
- Cause: migrations and tooling capabilities are provider-specific.
- Known differences: `dotnet ef migrations script --idempotent` on SQLite fails with
  `Generating idempotent scripts for migrations is not currently supported for SQLite.`
  [verified] — plain `script` works. SQLite has limited `ALTER TABLE`, so many operations
  (column type changes, most constraint changes) make EF rebuild the whole table
  **[docs]**; SQL Server alters in place. Generated SQL types differ (`TEXT`/`INTEGER` vs
  `nvarchar`/`int` — both observed in verified script output).
- Fix: scaffold and CI-test migrations against the SAME provider production uses. A
  SQLite-for-tests, SQL-Server-for-prod split means migrations must be validated against
  SQL Server in CI anyway — budget for it.
- Tell: `git grep -n "UseSqlite\|UseSqlServer\|UseNpgsql" -- "*.cs"` returns more than one
  provider.

**T8 — Stale build: `--no-build` and friends lie to you.** [verified]
- Symptom: `dotnet ef migrations list --no-build` shows a migration you just removed, or
  `database update --no-build` right after `migrations add` fails with
  `PendingModelChangesWarning` even though you DID add the migration.
- Cause: `dotnet ef` reads migrations from the compiled assembly. `--no-build` (or a failed
  build you didn't notice) means the tool sees the previous compilation.
- Fix: let `dotnet ef` build (the default), or `dotnet build` explicitly after any
  model/migration file change before using `--no-build`.
- Tell: the tool's view disagrees with the files in `<MIGRATIONS-DIR>`.

### 5. Environment safety — which database am I about to migrate?

**The pre-flight, before EVERY `database update` and every bundle run:**

```sh
dotnet ef dbcontext info
```

[verified] — prints `Provider name:`, `Database name:`, and `Data source:` for the context
as currently configured. If `Data source:` is not the database you intend, STOP. For
bundles, the equivalent is passing `--connection "<CONN>"` explicitly — never rely on
whatever the bundled appsettings default to.

Where the connection string actually comes from (ASP.NET Core default host, later wins)
**[docs]**: `appsettings.json` → `appsettings.<ENVIRONMENT>.json` (chosen by
`ASPNETCORE_ENVIRONMENT`, default `Production` when unset — which is exactly backwards
from what a dev machine wants) → user secrets (Development environment only) → environment
variables (`ConnectionStrings__<NAME>` with double underscore) → command-line args.
Catalog your project's real layering per `config-and-flags`.

Dev credentials belong in user secrets, not in `appsettings.json` [verified]:

```sh
dotnet user-secrets init                                        # stamps UserSecretsId into the .csproj
dotnet user-secrets set "ConnectionStrings:<NAME>" "<CONN>"     # stored per-user outside the repo
dotnet user-secrets list
```

Hard rules (route waivers through `change-control`'s non-negotiables registry):
- `dotnet ef database update` is a DEV-loop command. Staging/production apply a reviewed
  artifact: idempotent script or bundle (§3). The artifact is attached to the PR/release.
- Destructive migrations are class X: rehearse against a restored production snapshot and
  verify row counts before and after (`validation-and-qa` owns what counts as evidence).
- Any tooling that auto-migrates on app start (`context.Database.Migrate()` in `Program.cs`)
  is a production hazard flag: it applies migrations with app-deploy timing and no
  operator. Find it: `git grep -n "Database.Migrate()"`. If present, the instantiated
  skill must document who decided that and for which environments.

### 6. Query and DbContext discipline

**Tracking decision rule.** Tracked entities cost memory and change-detection time.
Rule: if the query result will be modified and saved in this unit of work → default
(tracked). Read-only (DTOs — data transfer objects, plain classes shaped for the caller,
not entities — lists, reports) → `.AsNoTracking()`. Read-only with entity
graphs where the same row appears repeatedly → `.AsNoTrackingWithIdentityResolution()`
**[docs]**. Projections (`.Select(x => new Dto{...})`) are never tracked — prefer them for
read paths anyway.

**Entity type shape.** Entities stay mutable classes with identity semantics. Do not model
entities as `record` types: record value equality and `with`-copy semantics fight the
change tracker's reference-identity model **[docs — re-verify on your EF version]**.
Records are for DTOs/projections (`csharp-code-discipline` §4.1).

**N+1 detection — measure, don't guess.** (N+1: one query for a parent list plus one more
query per row of it — the signature of lazy or per-item loading.) Turn on command logging
and count SQL statements for the suspect operation:

```csharp
// Quick dev-loop form (OnConfiguring or AddDbContext options):
options.LogTo(Console.WriteLine, LogLevel.Information);
// In ASP.NET Core, the same data flows through ILogger category
// "Microsoft.EntityFrameworkCore.Database.Command" at Information level.
```

**[docs — API names stable across EF Core 5+; not executed here]**. One user action
emitting one query per row of a parent list is the N+1 signature; fix with `.Include()`,
a projection, or batching. Statement counts and timings are `diagnostics-and-tooling`
territory — capture before/after numbers, not impressions.

**Cartesian explosion.** Multiple `.Include()` of sibling collections multiplies rows
(parent × childrenA × childrenB) in the single JOIN query. Fix: `.AsSplitQuery()` — one
query per included collection, at the cost of losing single-query consistency **[docs]**.
Tell: the logged SQL row count vastly exceeds the entity count.

**String parameter typing (the varchar/nvarchar classic).** .NET strings are sent as
`nvarchar` parameters by default; against a `varchar` column SQL Server converts the
*column*, which kills index seeks (symptom, evidence, and measurement:
`sql-server-operations` §3.4 item 5). Fix in the model: configure the column/property type
so EF sends the matching type — e.g.
`builder.Property(x => x.Status).HasColumnType("varchar(20)")` (or `.IsUnicode(false)`) —
then confirm in the logged SQL that the parameter is no longer `nvarchar` **[docs — API
names from official EF docs; re-verify on your version]**.

**Client evaluation: modern EF throws.** [verified, EF Core 10.0.9] A `Where` (or any
non-final operator) that EF cannot translate to SQL throws
`InvalidOperationException: The LINQ expression '...' could not be translated.` at query
execution — it does NOT silently pull the table into memory (EF Core 1–2 behavior; gone
since 3.0). Only the final `Select` projection may run client-side. Consequence: an
untranslatable expression is a hard runtime failure — integration-test your queries against
a real provider (`validation-and-qa`).

**DbContext lifetime rules** **[docs — these are the documented contracts]**:
- `AddDbContext<T>()` registers scoped: one instance per request. Correct default.
- A DbContext is NOT thread-safe. Never share one across threads; never fire parallel
  queries on one context (`Task.WhenAll` over the same context throws
  "A second operation was started on this context...").
- Parallel or background work: `AddDbContextFactory<T>()`, then
  `await using var db = await factory.CreateDbContextAsync()` per unit of work.
- Singletons must never capture a scoped DbContext — inject the factory instead.

**Async all the way down.** Use `SaveChangesAsync`, `ToListAsync`, `FirstOrDefaultAsync`
(namespace `Microsoft.EntityFrameworkCore`). Never bridge with `.Result` or `.Wait()` —
sync-over-async is the classic ASP.NET deadlock/thread-starvation pattern. Tell:
`git grep -n "\.Result\b\|\.Wait()" -- "*.cs"` in request-path code. (General async
discipline and its analyzer enforcement, CA1849: `csharp-code-discipline` §4.3/§6.)

## Worked example

**Illustrative example — all project facts fictional.** Project "Harborline", ASP.NET Core
API, SQL Server in prod, EF Core 10, `dotnet-ef` pinned in `.config/dotnet-tools.json`.

Task: dockets need a `ClosedAtUtc` column, and the obsolete `Dockets.LegacyCode` column
should go.

1. **Split by class.** Additive column = class C. Column drop = class X. Two migrations,
   two PRs (per §3 — never bundle an X change inside a C change).
2. **PR 1 — additive.** Add `public DateTime? ClosedAtUtc { get; set; }`. Then:
   `dotnet ef migrations add AddDocketClosedAtUtc` → read the file: one `AddColumn`,
   nullable, no data-loss warning. `dotnet ef dbcontext info` → `Data source:
   localhost\dev` — correct. `database update` → tests green → `database update
   AddDocketIndexes` (previous — an index migration, class B per §3, measured per
   `sql-server-operations` §3.5) → `database update` again: Down round-trip proven.
   Artifact for staging: `dotnet ef migrations script --idempotent -o
   artifacts/0071_AddDocketClosedAtUtc.sql`, attached to the PR. Reviewer greps the
   migration for `DropColumn|DropTable|AlterColumn`: clean. Merged, deployed; pipeline
   applies the reviewed script.
3. **PR 2 — destructive, two weeks later** (after confirming no reader of `LegacyCode`
   remains: `git grep -n "LegacyCode"` → only the entity class). Remove the property;
   `migrations add DropDocketLegacyCode` prints `An operation was scaffolded that may
   result in the loss of data.` — author labels the PR class X. Rollback plan: "Down()
   re-adds the column EMPTY; real recovery = point-in-time restore, rehearsed 2026-06-30
   against the prod snapshot, 4.1M rows verified." Bundle built
   (`dotnet ef migrations bundle --output artifacts/efbundle-0072.exe`), rehearsed against
   the snapshot with explicit `--connection`, scheduled window, second operator present.
4. **The merge wrinkle.** Meanwhile a teammate merged `AddPortCallTable`. PR 2's branch now
   has an out-of-order migration (T2): `database update AddDocketClosedAtUtc` →
   `migrations remove` → rebase onto main → `migrations add DropDocketLegacyCode` →
   `database update`. Snapshot correct, timestamps ordered, no hand-merged generated code.

## Instantiate for your project

Produce `.claude/skills/<PROJECT>-ef-discipline/SKILL.md`. A Sonnet-class model can execute
these steps unaided.

### Step 1 — Mine the EF surface (evidence gathering)

```sh
# The contexts
git grep -l "DbContext" -- "*.cs"
# Where migrations live (one dir per context, usually)
git ls-files | grep -i "Migrations/"
# Providers and EF packages + versions
git grep -n "Microsoft.EntityFrameworkCore" -- "*.csproj"
git grep -n "UseSqlServer\|UseSqlite\|UseNpgsql\|UseMySql" -- "*.cs"
# Tool pinning
cat .config/dotnet-tools.json
# Connection-string sources
git grep -n "ConnectionStrings" -- "appsettings*.json" "*.cs"
git grep -n "GetConnectionString\|UserSecretsId" -- "*.cs" "*.csproj"
# Auto-migrate-on-start hazard (§5)
git grep -n "Database.Migrate()\|EnsureCreated()" -- "*.cs"
# Migration history = the project's actual schema-change cadence and past incidents
git log --oneline -- "*Migrations*" | head -30
git log -i --grep="migration" --grep="rollback" --grep="schema" --oneline | head -30
```

`EnsureCreated()` anywhere near production code is its own finding: it bypasses migrations
entirely and is incompatible with them **[docs]** — record it under Known gaps.

### Step 2 — Prove the lifecycle in THIS repo

Run `dotnet tool restore`, then `dotnet ef dbcontext info` per context (with the right
`--project`/`--startup-project` — record the exact working invocation; multi-project
solutions are where the generic commands need flags). Then on a scratch database: apply all
migrations from zero (`database update`), revert one (`database update <PREVIOUS>`),
re-apply. Record what worked and what failed verbatim.

Obtaining the scratch DB, in preference order:
(a) a throwaway database on a local SQL Server / LocalDB instance you create and name
`<PROJECT>_efscratch` (LocalDB: `sqllocaldb create <INSTANCE>` then connect to
`(localdb)\<INSTANCE>`);
(b) `docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=<STRONG-PW>" -p 1433:1433
mcr.microsoft.com/mssql/server:2022-latest` (volatile — verify the current tag);
(c) if no disposable server of the production provider is obtainable, DO NOT run
`database update` anywhere — downgrade Step 2 to script review only
(`dotnet ef migrations script`) and record "lifecycle unproven — no scratch `<PROVIDER>`
available" in Known gaps. Never substitute SQLite to "prove" a SQL Server repo (T7).

### Step 3 — Fill the skeleton

```markdown
---
name: <PROJECT>-ef-discipline
description: <triggers naming this project's contexts, providers, and danger tables>
---
# <PROJECT> — EF Core Discipline
## Contexts and providers      # context → project → provider → prod database, from Step 1
## Exact commands              # the working --project/--startup-project invocations, from Step 2
## Migration gate map          # §3 classes mapped to THIS repo's review rules (link <PROJECT>-change-control)
## Environment matrix          # env → connection-string source → who may run what against it
## How prod is migrated        # script/bundle/pipeline — as it ACTUALLY happens, with the CI/pipeline file cited
## Trap instances              # T1–T8 entries that have actually occurred here, each citing a commit/PR/incident
## Query discipline notes      # known N+1 hotspots, AsNoTracking conventions, factory usage — each with evidence
## Known gaps                  # e.g. auto-migrate on start, no drift check in CI, SQLite-tests/SqlServer-prod split
## Provenance                  # date, EF/tool versions, scratch-DB used for Step 2, SHAs cited
```

### Step 4 — Evidence gates (do not fill a blank without its evidence)

- Do not list a context/provider you have not confirmed via Step 1 output.
- Do not write an "Exact commands" line you have not executed successfully in this repo.
- Do not claim "prod is migrated via X" from a README — cite the pipeline/CI file and line,
  or write `UNKNOWN — verify with the operator` (per `run-and-operate`).
- Do not record a trap instance without a commit SHA, PR, or incident pointer
  (`failure-archaeology` has the mining method).
- Do not copy §6 performance advice as project fact — a hotspot goes in only with a
  measured statement count or timing behind it (`diagnostics-and-tooling`).

## Provenance and maintenance

- Authored 2026-07-06 against no specific project. Stack facts verified by execution in a
  scratch project (console app, .NET SDK 10.0.301, EF Core 10.0.9, dotnet-ef 10.0.9,
  SQLite provider end to end; SQL Server provider for script generation only — no live SQL
  Server was used).
- Verified by execution 2026-07-06: `dotnet new tool-manifest`; `dotnet tool install
  dotnet-ef` (local); `dotnet ef migrations add / remove / list /
  has-pending-model-changes` (both exit codes and both messages); `dotnet ef database
  update` (apply, revert-to-named-migration, and the `PendingModelChangesWarning` refusal);
  `dotnet ef migrations script` (plain on SQLite; `--idempotent` on SQL Server provider,
  and the SQLite not-supported error); `dotnet ef migrations bundle` (built and executed
  against a fresh DB with `--connection`; `--help` confirms migration arg `0` = revert
  all); `dotnet ef dbcontext info / script`; `dotnet user-secrets init / set / list`;
  the scaffold-time data-loss warning text; the client-evaluation
  `InvalidOperationException ... could not be translated` throw. The scratch-DB recipe's
  `sqllocaldb create <INSTANCE>` / `sqllocaldb delete <INSTANCE>` pair was executed against
  LocalDB 17.0.4025.3 on 2026-07-07.
- [docs] items NOT executed here — re-verify on first use: appsettings/environment
  layering order; `LogTo`/logging category name; `AsSplitQuery`,
  `AsNoTrackingWithIdentityResolution`, `AddDbContextFactory`, `HasColumnType`/`IsUnicode`
  column-type configuration (API names from official EF
  docs); SQLite table-rebuild behavior; expand/contract pattern; `has-pending-model-changes`
  introduction version (EF 8); EF Core ≤8 proceed-on-pending-changes behavior;
  `EnsureCreated()` incompatibility with migrations.
- Volatile parts: dotnet-ef flag surface and messages (`dotnet ef migrations --help`,
  `dotnet ef database update --help`); provider package names and the SQLite `--idempotent`
  limitation ("not *currently* supported" — re-run `dotnet ef migrations script
  --idempotent` on the installed version); bundle size/behavior; EF's throw-on-untranslatable
  behavior is stable since 3.0 but re-confirm on major-version upgrades.
- Instantiated copies must add their own provenance: EF/tool versions in the repo, the
  scratch database used to prove the lifecycle, and the SHAs/PRs behind every trap instance
  and gate deviation.
