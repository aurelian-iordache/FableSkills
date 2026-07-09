---
name: sql-server-operations
description: STACK TIER. Load this skill when operating a SQL Server database beyond basic CRUD — "the database is slow", "queries are timing out", "something is blocking", "should I add this index?", "is our backup any good?", reading an execution plan, running ad-hoc UPDATE/DELETE against shared or production data, or explaining "works in dev, deadlocks in prod". Delivers a verified DMV diagnostic query pack with interpretation guides, plan-reading for non-experts, index/statistics discipline, the restore-rehearsal doctrine for backups, and the mandatory safety ritual for ad-hoc T-SQL.
---

# sql-server-operations — SQL Server Operational Discipline

Stack tier: facts below marked **[verified]** were executed 2026-07-06 against SQL Server 2025
(17.0.4025.3) Express Edition via LocalDB, sqlcmd 15.0.2000.5, on a throwaway 100k-row database.
The DMVs and T-SQL used here have been stable since SQL Server 2008+ unless noted; still,
re-verify on your version (`SELECT @@VERSION;`) before trusting version-sensitive claims.

## 1. Purpose

This skill makes you able to (a) answer "why is the database slow / stuck?" with DMV queries
instead of guesses, (b) read an execution plan well enough to find the usual five culprits,
(c) change indexes and statistics as measured, gated changes, (d) treat backups as unproven
until restored, and (e) run ad-hoc data-modifying T-SQL without becoming the incident.

## 2. When to use / When NOT to use

Use when: diagnosing SQL Server performance or blocking, deciding on an index, writing or
checking backups, running any hand-typed UPDATE/DELETE against data you can't regenerate,
or instantiating `<PROJECT>-sql-operations`.

| If instead you need... | Use sibling skill |
|---|---|
| Schema changes via EF Core migrations (the usual arrival path for schema), including "the migration generated wrong/slow SQL" (this skill then owns reading the plan it produces) | dotnet-ef-discipline |
| Whether a production index/schema change may ship at all, and through what gate | change-control |
| The general measure-don't-eyeball doctrine and baseline discipline | diagnostics-and-tooling |
| Whether a before/after measurement actually proves the claim | proof-and-analysis |
| Deploy/rollback runbooks, artifact conventions, the irreversibility test | run-and-operate |
| Whether this database problem was fought before (check FIRST for recurring symptoms) | failure-archaeology |
| Root-causing a logic bug that happens to involve SQL | debugging-playbook |

Boundary: this skill owns *SQL Server-specific* instruments and rails. The philosophy of
measurement lives in diagnostics-and-tooling; this is that philosophy applied to the database.

## 3. Core doctrine

### 3.1 Definitions (first use)

- **DMV** (dynamic management view): a built-in system view (`sys.dm_*`) exposing live server
  state — the plan cache, current requests, accumulated waits. Reading them is cheap and safe.
- **Plan cache**: SQL Server compiles each query into an execution plan and caches it;
  `sys.dm_exec_query_stats` accumulates per-plan runtime totals since the plan was cached.
- **Logical reads**: 8 KB pages read from memory. The best single cost proxy for a query —
  stable across runs, unlike duration (which depends on cache warmth and load).
- **Wait stats**: whenever a request can't run (lock held, page not in memory, log flush
  pending) SQL Server records what it waited on. Cumulative since instance restart.
- **Run these queries with**: `sqlcmd -S <SERVER> -d <DATABASE> -E -i <FILE>.sql` (Windows
  auth) or `-U <USER> -P <PASSWORD>`; or any client (SSMS — SQL Server Management Studio,
  the standard GUI client — or Azure Data Studio). [verified]

### 3.2 DMV blind spots — read before trusting any query below

1. **Everything resets on instance restart.** Query stats, wait stats, index usage stats are
   since-restart accumulations. Check uptime first:
   `SELECT sqlserver_start_time FROM sys.dm_os_sys_info;` A server up 20 minutes has 20 minutes
   of evidence.
2. **The AUTO_CLOSE trap.** Databases created on LocalDB default to `AUTO_CLOSE ON`
   [verified on this instance; commonly also true on standalone Express — confirm with the
   check below]: when the last connection closes, the database shuts down and its plan-cache
   entries and index-usage rows are flushed — DMV queries return empty and you conclude,
  falsely, "no load". Check: `SELECT name, is_auto_close_on FROM sys.databases;` Fix for a dev
   box: `ALTER DATABASE <DB> SET AUTO_CLOSE OFF;` (Observed directly: identical workload showed
   zero query-stats rows with AUTO_CLOSE on, full rows with it off.)
3. **Plan cache is not complete.** Plans get evicted under memory pressure; `RECOMPILE` hints
   and DBCC FREEPROCCACHE leave gaps. Absence of evidence in `dm_exec_query_stats` is not
   evidence of absence.
4. **Cumulative wait stats answer "since restart", not "right now".** For a live problem,
   sample twice a minute apart and diff, or read the waits on *current requests* (query B).

### 3.3 Diagnostic query pack

Run these top-down when someone says "the database is slow". Each was executed with real
output at authoring time [verified].

#### A. Top queries by CPU (swap ORDER BY for reads)

```sql
SELECT TOP (10)
    qs.total_worker_time / qs.execution_count / 1000 AS avg_cpu_ms,
    qs.execution_count,
    qs.total_logical_reads / qs.execution_count      AS avg_logical_reads,
    qs.max_elapsed_time / 1000                       AS max_elapsed_ms,
    qs.creation_time                                 AS plan_cached_since,
    SUBSTRING(st.text, (qs.statement_start_offset/2) + 1,
        ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
          ELSE qs.statement_end_offset END - qs.statement_start_offset)/2) + 1) AS statement_text
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
ORDER BY qs.total_worker_time DESC;   -- or: qs.total_logical_reads DESC
```

Interpretation guide:

| Column | Meaning | Reading → action |
|---|---|---|
| `avg_cpu_ms` | CPU per execution | High avg + low count → one bad query; tune it. Low avg + huge count → chatty application; fix the caller (N+1 loop), not the query. |
| `avg_logical_reads` | pages touched per execution | Thousands of reads returning few rows → scan where a seek belongs; go to plan reading (3.4). (In verification, the same aggregate on a 100k-row table cost 256 reads as a scan vs 59 as a seek; more selective predicates seek in single-digit reads.) |
| `execution_count` | runs since plan cached | Divide everything by this before comparing queries. |
| `plan_cached_since` | when totals started | A "top" query cached 3 weeks ago may just be old. Compare totals only across similar cache ages. |

Blind spot: totals are per *plan*, so the same SQL text can appear multiple times (different
set options / plans).

#### B. Who is blocked, and by whom

```sql
SELECT r.session_id, r.blocking_session_id, r.wait_type, r.wait_time AS wait_ms,
       r.status, DB_NAME(r.database_id) AS db, st.text AS running_sql
FROM sys.dm_exec_requests AS r
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) AS st
WHERE r.blocking_session_id <> 0;

-- The head blocker often runs NOTHING (idle in an open transaction), so it has no row in
-- dm_exec_requests. Find it via its last statement:
SELECT s.session_id AS head_blocker, s.login_name, s.host_name, s.program_name,
       txt.text AS last_sql
FROM sys.dm_exec_sessions AS s
CROSS APPLY (SELECT MAX(c.most_recent_sql_handle) AS h
             FROM sys.dm_exec_connections AS c WHERE c.session_id = s.session_id) AS mc
OUTER APPLY sys.dm_exec_sql_text(mc.h) AS txt
WHERE s.session_id IN (SELECT blocking_session_id FROM sys.dm_exec_requests
                       WHERE blocking_session_id <> 0)
  AND s.session_id NOT IN (SELECT session_id FROM sys.dm_exec_requests
                           WHERE blocking_session_id <> 0);
```

[verified live: a deliberately held transaction produced `blocking_session_id` chains with
lock waits (`LCK_M_U` in that run — the exact `LCK_M_*` type depends on the statement
shapes), and the second query identified the idle head blocker with its last SQL.]

| Reading | Action |
|---|---|
| Chain of A←B←C | Only the HEAD matters. Walk `blocking_session_id` to the session that is blocked by 0. |
| Head blocker `status` missing from requests / "sleeping" | Open transaction left idle — the classic (app crashed mid-transaction, or a human forgot COMMIT). Contact the owner (`login_name`, `host_name`, `program_name`); `KILL <SESSION-ID>` rolls it back — rollback can take as long as the work done, and killing an unknown session is a gated action, not a reflex (run-and-operate's irreversibility test: answer "can I undo this?" first, and get the session owner or a second person on the line). |
| `wait_ms` growing across two samples | Real live blocking, not a snapshot artifact. |

#### C. Wait stats — what the server spends its time waiting on

```sql
SELECT TOP (15) wait_type, waiting_tasks_count, wait_time_ms, signal_wait_time_ms,
    CAST(100.0 * wait_time_ms / NULLIF(SUM(wait_time_ms) OVER (), 0) AS DECIMAL(5,1)) AS pct
FROM sys.dm_os_wait_stats
WHERE wait_type NOT IN (   -- benign idle/background waits; extend as needed
    'SLEEP_TASK','LAZYWRITER_SLEEP','SQLTRACE_BUFFER_FLUSH','CHECKPOINT_QUEUE',
    'REQUEST_FOR_DEADLOCK_SEARCH','XE_TIMER_EVENT','XE_DISPATCHER_WAIT','WAITFOR',
    'BROKER_TASK_STOP','BROKER_TO_FLUSH','BROKER_EVENTHANDLER','BROKER_RECEIVE_WAITFOR',
    'BROKER_TRANSMITTER','ONDEMAND_TASK_QUEUE','DBMIRROR_EVENTS_QUEUE','DBMIRRORING_CMD',
    'LOGMGR_QUEUE','DIRTY_PAGE_POLL','SLEEP_SYSTEMTASK','SLEEP_BPOOL_FLUSH',
    'SQLTRACE_INCREMENTAL_FLUSH_SLEEP','SP_SERVER_DIAGNOSTICS_SLEEP',
    'QDS_PERSIST_TASK_MAIN_LOOP_SLEEP','QDS_ASYNC_QUEUE',
    'QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP','HADR_FILESTREAM_IOMGR_IOCOMPLETION',
    'SOS_WORK_DISPATCHER','DISPATCHER_QUEUE_SEMAPHORE','SERVER_IDLE_CHECK',
    'AZURE_IMDS_VERSIONS','PWAIT_ALL_COMPONENTS_INITIALIZED','SLEEP_MASTERDBREADY',
    'SLEEP_DCOMSTARTUP','CHKPT')
ORDER BY wait_time_ms DESC;
```

Dispatcher/idle waits dominating = no workload, not a problem. On an idle instance,
parked worker threads accumulate enormous "wait time" that means nothing: observed on the
verification LocalDB (17.0.4025.3), `SOS_WORK_DISPATCHER` was 71.4% and
`DISPATCHER_QUEUE_SEMAPHORE` 26.2% of all wait time before they were excluded [verified].
If a wait you cannot place tops this list on a quiet server, suspect idle/background noise
first and extend the exclusion list — do not tune the server around it.

Classic wait types — meanings are established; the "first response" column is a **heuristic
starting point**, not a diagnosis:

| Wait type | Means | First response (heuristic) |
|---|---|---|
| `LCK_M_*` (LCK_M_S, LCK_M_U, LCK_M_X...) | Waiting for a lock: shared/update/exclusive | Go to query B; find and fix the head blocker. Long transactions and missing indexes (scans lock more) are the usual roots. |
| `PAGEIOLATCH_SH/EX` | Waiting for a data page to arrive **from disk** | Big scans flushing the buffer pool (SQL Server's in-memory cache of data pages), too little RAM, or genuinely slow storage — in that order of likelihood. Find the top-reads queries (query A) before blaming hardware. |
| `WRITELOG` | Waiting for the transaction log flush on commit | Many tiny commits (row-by-row loops) or slow log-file storage. Batch the commits; put the log on fast storage. |
| `CXPACKET` / `CXCONSUMER` | Parallel query threads coordinating | Not inherently a problem — parallelism is how big queries finish. CXCONSUMER (SQL 2017+) is the benign share. Chronic high CXPACKET with slow queries → look for huge scans that shouldn't go parallel at all; review MAXDOP (max degree of parallelism — the server/db setting capping threads per query) / cost threshold for parallelism as a gated config change. |
| `SOS_SCHEDULER_YIELD` | Tasks yielding the CPU voluntarily | CPU pressure signal (heuristic): check top-CPU queries (query A) before adding cores. |
| `PAGELATCH_*` (no "IO") | Contention on a page **in memory** — not disk | Classic: allocation contention in tempdb (the shared system database used for temp tables, sorts, and row-versioning) or a hot last-page insert pattern. Do not confuse with PAGEIOLATCH. |

Blind spots: cumulative-since-restart (3.2); on Express/LocalDB you will never see CXPACKET
because Express does not produce parallel plans — the plan XML says
`NonParallelPlanReason="NoParallelPlansInDesktopOrExpressEdition"` [verified] — one reason
parallelism problems appear only in production.

#### D. Missing-index suggestions — WITH MANDATORY WARNING

```sql
SELECT DB_NAME(mid.database_id) AS db, OBJECT_NAME(mid.object_id, mid.database_id) AS table_name,
       migs.user_seeks + migs.user_scans AS times_wanted,
       migs.avg_total_user_cost AS avg_query_cost, migs.avg_user_impact AS est_pct_improvement,
       mid.equality_columns, mid.inequality_columns, mid.included_columns
FROM sys.dm_db_missing_index_details AS mid
JOIN sys.dm_db_missing_index_groups AS mig  ON mig.index_handle = mid.index_handle
JOIN sys.dm_db_missing_index_group_stats AS migs ON migs.group_handle = mig.index_group_handle
ORDER BY migs.avg_user_impact * (migs.user_seeks + migs.user_scans) DESC;
```

**WARNING — these suggestions are naive. Never create them verbatim.** The optimizer emits one
suggestion per query shape with no view of the whole table: it will happily propose five
overlapping indexes differing by one INCLUDE column, ignores your existing indexes, and never
accounts for write cost. Treat each row as "queries on `<TABLE>` filter on the
`equality_columns` and would like the `included_columns` covered" — then design ONE index against the full picture
(3.5), and ship it as a measured, gated change. [verified: 20 runs of a single scan query
produced a suggestion claiming 84.7% improvement — plausible here, but the DMV would have kept
stacking near-duplicates for each query variant.]

#### E. Index usage — dead-index candidates

```sql
SELECT OBJECT_NAME(i.object_id) AS table_name, i.name AS index_name, i.type_desc,
       ius.user_seeks, ius.user_scans, ius.user_lookups, ius.user_updates,
       ius.last_user_seek, ius.last_user_scan
FROM sys.indexes AS i
LEFT JOIN sys.dm_db_index_usage_stats AS ius
       ON ius.object_id = i.object_id AND ius.index_id = i.index_id
      AND ius.database_id = DB_ID()
WHERE OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
ORDER BY OBJECT_NAME(i.object_id), i.index_id;
```

| Reading | Action |
|---|---|
| seeks+scans+lookups = 0 (or NULL row) but `user_updates` high | Every write pays for an index nobody reads — a DROP candidate. But: usage resets on restart and AUTO_CLOSE (3.2), and month-end/annual jobs read indexes that look dead for 29 days. Require a full business cycle of uptime evidence, then drop as a gated change with the CREATE statement saved for instant rollback. |
| High `user_lookups` on the clustered index | Nonclustered seeks are bouncing to the base table for missing columns → covering-index candidate (3.5). |

### 3.4 Query plan reading for non-experts

**Actual vs estimated:** an *estimated* plan is the optimizer's intention (no execution); an
*actual* plan adds runtime row counts. Always prefer actual for diagnosis. Get it in SSMS with
"Include Actual Execution Plan" (Ctrl+M), or textually: `SET STATISTICS XML ON;` before the
query [verified].

**The numeric before/after tool** — run this around any query you're tuning, and record both
numbers before touching anything (baseline discipline per diagnostics-and-tooling):

```sql
SET STATISTICS IO ON;   -- per-table: logical reads, physical reads
SET STATISTICS TIME ON; -- CPU time, elapsed time
<YOUR QUERY>;
SET STATISTICS IO OFF; SET STATISTICS TIME OFF;
```

Output looks like: `Table 'Orders'. Scan count 1, logical reads 256, physical reads 0, ...`
[verified]. **Logical reads is the number to compare** — duration varies with cache and load;
reads don't.

**The five things to look at first**, in order:

1. **Scans vs seeks on big tables.** A Clustered Index Scan or Index Scan on a large table
   feeding a small result = reading everything to return a little. Look at the plan's
   `ActualRowsRead` vs `ActualRows` (XML) or "Number of Rows Read" vs "Actual Number of Rows"
   (SSMS): 100,000 read for 25,000 returned is work the right index would skip. Scans on tiny
   tables are fine — cheapest possible plan.
2. **Key Lookups.** A nonclustered Index Seek paired with a Key Lookup per row means the index
   found the rows but lacks columns the SELECT needs. Cheap at 10 rows, brutal at 100k.
   Fix: covering index / INCLUDE (3.5) — or stop selecting columns you don't use.
3. **Warnings.** Yellow-triangle operators in SSMS; `<Warnings>` elements in XML. Spills
   (`SpillToTempDb` — sort/hash ran out of memory grant and hit disk) and
   `PlanAffectingConvert` (see item 5) are the common ones. A plan with a warning is guilty
   until proven innocent.
4. **Estimated vs actual rows.** Estimated 1, actual 500,000 (or the reverse) means the
   optimizer chose the plan for a different data shape than reality — stale statistics (3.5),
   or a parameter value that doesn't represent typical data. Everything downstream of a bad
   estimate is built on sand; fix the estimate before micro-tuning operators.
5. **Implicit conversions — the nvarchar-vs-varchar classic [verified].** If the column is
   `varchar` and the parameter is `nvarchar` (the default for .NET strings — fix via
   column-type configuration, dotnet-ef-discipline §6), SQL Server must convert
   **the column**, which kills the seek.
   Verified head-to-head on the same indexed 100k-row table: varchar literal → Index Seek,
   59 logical reads; `N'...'` literal → Index Scan, 256 reads, 100,000 rows read for 24,982
   returned, and this warning in the plan:
   `PlanAffectingConvert ConvertIssue="Seek Plan" Expression="CONVERT_IMPLICIT(nvarchar(20),[dbo].[Orders].[Status],0)=[@1]"`.
   Fix the parameter's type at the caller; don't widen the column reflexively.

### 3.5 Index and statistics discipline

**Clustered index choice** (the table IS the clustered index; every nonclustered index carries
its keys). Rules of thumb — established practice, but judgment calls, labeled heuristic:
prefer narrow (fewer/smaller columns), unique, unchanging, and ever-increasing keys (identity
int/bigint is the default answer). Wide/random keys (GUIDs, composite natural keys) bloat every
other index and fragment on insert. Deviate only with a written reason.

**Covering indexes and INCLUDE.** An index *covers* a query when it contains every column the
query touches, eliminating Key Lookups. Key columns are for seeking/sorting; `INCLUDE` columns
ride along at the leaf only — cheaper than adding them as keys:

```sql
CREATE NONCLUSTERED INDEX IX_<TABLE>_<COLS> ON <SCHEMA>.<TABLE> (<FILTER-COL>[, ...])
INCLUDE (<SELECTED-COL>[, ...]);   -- [verified syntax]
```

**When NOT to add an index:** the table is small (scan is already optimal); the column is
low-selectivity alone (`Status` with 4 values — unless filtered/covering for a specific hot
query); the table is write-hot and the index serves one rare report; an existing index already
leads on the same column (widen it instead — one good index beats three overlapping ones);
or the real problem is a bad estimate or implicit conversion (3.4 items 4–5) that an index
cannot fix.

**Statistics staleness.** The optimizer estimates row counts from per-column statistics;
`modification_counter` shows churn since the last update [verified: 30k updates → counter
30002 → 0 after `UPDATE STATISTICS dbo.Orders;`]:

```sql
SELECT OBJECT_NAME(s.object_id) AS table_name, s.name AS stats_name,
       sp.last_updated, sp.rows, sp.modification_counter
FROM sys.stats AS s
CROSS APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) AS sp
WHERE OBJECTPROPERTY(s.object_id, 'IsUserTable') = 1
ORDER BY sp.modification_counter DESC;
```

Heuristic: counter comparable to `rows` (or a huge estimate/actual gap in a plan) → run
`UPDATE STATISTICS <SCHEMA>.<TABLE>;` off-peak and re-check the plan. Auto-update exists but
lags on large tables.

**Fill factor** (space deliberately left free in index pages to absorb inserts): pure
heuristic territory. Default 0/100 is right until measured page-split pain says otherwise;
lowering it taxes every read to help some writes. Don't touch without a before/after.

**Every index change is a measured before/after.** Record `SET STATISTICS IO` reads and the
plan shape for the affected queries before; create the index; record after; keep both numbers
in the change record. Statistical honesty rules (multiple runs, medians, conditions) are owned
by proof-and-analysis. **Index changes on production are gated changes** — they lock/consume
resources while building and shift plans for everyone — classify and route per change-control.

### 3.6 Backup and restore as proof

**Doctrine: a backup that has never been restored is a hope, not a backup.** The only proof a
backup works is a completed restore that answers a real query. Schedule restore rehearsals
(monthly is a common cadence — heuristic) and date-stamp the last one, exactly like rollback
rehearsal in run-and-operate.

**Recovery models** — what each costs you:

| Model | Point-in-time restore? | Log management cost |
|---|---|---|
| SIMPLE | No — you can restore only to full/diff backup points; everything after the last backup is lost | None: log truncates on checkpoint |
| FULL | Yes — to any moment covered by an unbroken log-backup chain | You MUST take regular log backups or the log file grows until the disk is full — the classic "help, the LDF is 400 GB" incident |

Rule: production data anyone would miss → FULL plus scheduled log backups. Dev/scratch →
SIMPLE. Check yours: `SELECT name, recovery_model_desc FROM sys.databases;` [verified]

**Backup anatomy** — FULL = complete database; DIFF = changes since the last FULL (restore
needs FULL + latest DIFF); LOG = the transaction log since the last log backup (restore needs
FULL [+ DIFF] + every log backup in order). All patterns below executed end-to-end [verified]:

```sql
BACKUP DATABASE <DB> TO DISK = '<PATH>\<DB>_full.bak' WITH INIT, CHECKSUM, STATS = 25;
BACKUP DATABASE <DB> TO DISK = '<PATH>\<DB>_diff.bak' WITH DIFFERENTIAL, INIT, CHECKSUM;
BACKUP LOG      <DB> TO DISK = '<PATH>\<DB>_log1.trn' WITH INIT, CHECKSUM;
```

`CHECKSUM` verifies pages as they're written; `INIT` overwrites the file (omit to append).
`RESTORE VERIFYONLY FROM DISK = '<PATH>\<DB>_full.bak' WITH CHECKSUM;` checks the backup is
readable and complete — **necessary, not sufficient**: it does not restore, does not run
recovery, and cannot promise the database inside is usable. Only a real restore proves that.

**Restore rehearsal pattern** — restore under a NEW name beside the source (never over it):

```sql
RESTORE FILELISTONLY FROM DISK = '<PATH>\<DB>_full.bak';  -- get logical file names first
RESTORE DATABASE <DB>_rehearsal FROM DISK = '<PATH>\<DB>_full.bak'
WITH MOVE '<LOGICAL-DATA-NAME>' TO '<PATH>\<DB>_rehearsal.mdf',
     MOVE '<LOGICAL-LOG-NAME>'  TO '<PATH>\<DB>_rehearsal_log.ldf',
     NORECOVERY, STATS = 25;                -- NORECOVERY = "more backups coming"
RESTORE LOG <DB>_rehearsal FROM DISK = '<PATH>\<DB>_log1.trn' WITH RECOVERY;  -- last one: RECOVERY
-- Proof = a real query answers correctly:
SELECT COUNT(*) FROM <DB>_rehearsal.dbo.<KEY-TABLE>;
```

Then verify the count against expectation, record the rehearsal date, and drop the rehearsal
copy. Restoring OVER a live database is an irreversible, gated action (run-and-operate
irreversibility test) — rehearse beside, never over.

### 3.7 Safety rails for ad-hoc T-SQL

The ritual below governs *execution*. The *decision* to run hand-typed UPDATE/DELETE
against production or shared data is itself a gated change: classify per change-control
(a rewrite you could only undo from backup is class X — rehearse on a restored copy, name
the tested recovery mechanism, second person present). The Step-1 predicted count and
Step-2 `@@ROWCOUNT` output are the evidence you attach to that gate, not a substitute
for it.

**The mandatory ritual for every hand-typed UPDATE or DELETE** on data you can't regenerate.
Predict before you run (research-discipline: a prediction written after the result is not a
prediction):

```sql
-- Step 1: SELECT-first with the EXACT WHERE you intend to modify. Note the count: that is
-- your written prediction.
SELECT COUNT(*) FROM <SCHEMA>.<TABLE> WHERE <PREDICATE>;

-- Step 2: transaction, modify, compare @@ROWCOUNT to the prediction.
BEGIN TRAN;
UPDATE <SCHEMA>.<TABLE> SET <COL> = <VALUE> WHERE <PREDICATE>;   -- SAME predicate, pasted
SELECT @@ROWCOUNT AS actual_rows;   -- must be read IMMEDIATELY after the statement

-- Step 3: actual == predicted -> COMMIT TRAN;
--         anything else       -> ROLLBACK TRAN;  then find out why before retrying.
```

[verified end-to-end: predicted 231, `@@ROWCOUNT` 231, and after a deliberate ROLLBACK the
data was untouched.] A mismatch means your WHERE doesn't say what you think — the transaction
just saved you. Never run the UPDATE "real quick" without the transaction; typing `BEGIN TRAN`
costs two seconds, and the missing-WHERE UPDATE is a career classic. Don't leave the
transaction open while you wander off — you are now the head blocker in query B.

**Other rails:**
- No `ALTER`, index changes, or permission/`sp_configure` changes on production outside a
  gated change (change-control). Ad-hoc means *read* by default.
- **NOLOCK honesty.** `WITH (NOLOCK)` = READ UNCOMMITTED. It does not "just skip locks": you
  can read rows that were never committed (dirty reads), read the same row twice, or miss
  committed rows entirely during page splits. Acceptable for rough monitoring dashboards;
  never for anything feeding a decision, a report of record, or a WHERE clause of a later
  write. If readers blocking writers is the real problem, the grown-up fix is row-versioning
  (READ_COMMITTED_SNAPSHOT) — a gated, tested change with tempdb cost; verify for your
  version/edition.
- Large DELETEs/UPDATEs: batch (`DELETE TOP (5000) ... ; ` in a loop with a rowcount check)
  rather than one giant transaction that bloats the log and holds locks for minutes.
  Heuristic batch size; measure.

### 3.8 Environment drift — why dev lies to you

"Works in dev, deadlocks in prod" is usually not mystery — it's one of these. Check them
before debugging anything cross-environment:

```sql
SELECT name, compatibility_level, collation_name, recovery_model_desc, is_auto_close_on
FROM sys.databases;                       -- [verified]
SELECT SERVERPROPERTY('ProductVersion') AS version, SERVERPROPERTY('Edition') AS edition;
```

| Axis | The drift | Consequence |
|---|---|---|
| Data volume | Dev has 1k rows, prod has 50M | The optimizer picks different plans at different sizes: dev scans are cheap and lock little, prod scans are slow and lock ranges → timeouts and deadlocks that "can't be reproduced". This is the #1 cause. Test on production-scale data before believing a query is fine. |
| Edition | LocalDB/Express dev vs Standard/Enterprise prod | Express: no parallel plans [verified], DB size cap, no SQL Agent (no scheduled jobs — LocalDB additionally auto-shuts-down when idle). Developer edition = Enterprise features you may not have in prod. Azure SQL: no cross-DB queries as on-prem, no manual BACKUP TO DISK (platform-managed backups). Feature lists are volatile — verify against the official edition-comparison docs for YOUR version. |
| Compatibility level | Old level survives DB migration to a new server | Different optimizer behavior per level; two servers on the same engine can plan differently. Level 170 = SQL Server 2025-native [verified on this instance]; check with the query above. |
| Collation | Server or column collation differs | Case-sensitivity surprises and `Cannot resolve the collation conflict` errors on joins across databases; collation mismatches can also force conversions that kill seeks (3.4 item 5). |
| AUTO_CLOSE / auto-shutdown | On in dev-tier, off in prod | First query after idle is mysteriously slow in dev; DMV evidence evaporates (3.2). |

## 4. Worked example (illustrative — project fictional; the numbers are of the shape observed in verification)

Project "Harborline" reports checkout timeouts at lunch. Order of operations:

1. **History first** (failure-archaeology): the chronicle shows a similar incident resolved by
   an index — but on a different table. Not settled; proceed.
2. **Query B**: four sessions blocked in a chain ending at session 71 — `sleeping`, open
   transaction, `program_name = 'HarborlineWorker'`, last SQL an UPDATE on `dbo.Orders`. The
   worker holds a transaction across an external API call (code bug, not a database bug).
   Team restarts the worker; blocking clears. Root-cause fix filed: commit before the API call.
3. **Timeouts persist, milder.** Query A ordered by reads: `SELECT ... FROM Orders WHERE
   Status = @p` — 256 avg logical reads, 40k executions/hour. Plan (SET STATISTICS XML):
   Index **Scan**, `PlanAffectingConvert` warning, `CONVERT_IMPLICIT(nvarchar(20), Status)`.
   The app sends .NET strings as nvarchar; the column is varchar. The nvarchar-vs-varchar
   classic (3.4 item 5).
4. **Fix at the caller** (typed parameter — see dotnet-ef-discipline §6, string parameter
   typing), measured per 3.5: before 256 reads/scan, after 59 reads/seek (predicted
   "under 100" beforehand, per research-discipline). Shipped through change-control as a behavioral change; the missing-
   index DMV's suggestion to add a whole new Status index is declined — the existing index
   works fine once the conversion is gone.
5. **Chronicle updated** with symptom → root cause → evidence (the two before/after numbers
   and the plan warning) → status: fixed.

## 5. Instantiate for your project

Produce `.claude/skills/<PROJECT>-sql-operations/SKILL.md`. A Sonnet-class model can execute
this alone. Evidence bar: no claim about the project's database goes in the file unless you
ran the discovery query/command and captured its output. If you cannot connect to an
environment, do not guess: record `<ENV>: UNKNOWN — no access; needs <ROLE-OR-OWNER>` in
that skeleton section and continue; a partially-filled skill with honest UNKNOWNs beats a
stalled or invented one.

1. **Find the databases and connection strings:**
   - `grep -riE "connectionstring|Data Source=|Server=|Initial Catalog" --include="*.json" --include="*.config" --include="*.env*" .` — check `appsettings*.json`, `web.config`, CI variables. Secrets may live in user-secrets/vaults: note WHERE, never the values.
   - For each connection string record: server, database, auth mode, and which environment it belongs to. Then connect read-only and run `SELECT @@VERSION;` plus the 3.8 drift query per environment; tabulate the differences.
2. **Schema source of truth** — exactly one of:
   - EF Core migrations: `git ls-files "*Migrations/*.cs"` returns files → schema changes route through dotnet-ef-discipline; say so and link.
   - DACPAC/SSDT: `git ls-files "*.sqlproj" "*.dacpac"`.
   - Manual scripts: `git ls-files "*migrations/*.sql" "*db/*.sql"` or a tool config (Flyway/DbUp).
   - None found → record "schema source of truth: UNKNOWN — changes are untracked" as a top-line risk.
3. **Index inventory**: run the 3.3-E usage query and `SELECT OBJECT_NAME(object_id) AS tbl, name, type_desc FROM sys.indexes WHERE OBJECTPROPERTY(object_id,'IsUserTable')=1 ORDER BY tbl;` against a production-like environment. Note uptime (3.2) alongside — usage numbers without uptime are meaningless.
4. **Backup evidence** — belief is not evidence; query the history:
   ```sql
   SELECT TOP (30) bs.database_name, bs.type,  -- D=full, I=diff, L=log
          bs.backup_start_date, bmf.physical_device_name
   FROM msdb.dbo.backupset AS bs
   JOIN msdb.dbo.backupmediafamily AS bmf ON bmf.media_set_id = bs.media_set_id
   ORDER BY bs.backup_start_date DESC;   -- [verified]
   ```
   (Azure SQL: platform-managed — record retention settings instead.) Record: cadence by type, last successful of each, and the date of the last restore REHEARSAL (ask; if none is documented, write `RESTORE REHEARSAL: NEVER — schedule one` in bold).
5. **Baseline the top queries**: run 3.3-A and 3.3-C against production (read-only, off-peak), save output with date/uptime/commit into `<PROJECT>/diag/baselines/` per diagnostics-and-tooling. This is the "before" for every future incident.
6. **Fill the skeleton:**
   ```markdown
   ---
   name: <PROJECT>-sql-operations
   description: <triggers naming THIS project's databases and symptoms>
   ---
   # Environments        <!-- server/db/auth per env + drift table (3.8) with real values -->
   # Schema source of truth   <!-- one of the step-2 outcomes + change route -->
   # Diagnostic pack     <!-- 3.3 queries with any project tweaks; where baselines live -->
   # Index inventory     <!-- step-3 output + dead-index candidates with uptime evidence -->
   # Backup reality      <!-- step-4 evidence + last rehearsal date + rehearsal runbook -->
   # Safety rails        <!-- 3.7 ritual + project-specific forbidden operations -->
   # Provenance          <!-- who ran what, when, against which server/uptime -->
   ```
7. **Cross-link**: schema changes → `<PROJECT>-dotnet-ef-discipline` (if EF); gates →
   `<PROJECT>-change-control`; incident history → `<PROJECT>-failure-archaeology`.

## 6. Provenance and maintenance

- Authored 2026-07-06 against no specific project. All T-SQL and DMV queries marked
  [verified] were executed on SQL Server 2025 (RTM-CU3, 17.0.4025.3) Express Edition via
  LocalDB (`(localdb)\MSSQLLocalDB`), sqlcmd 15.0.2000.5, Windows 11, on a throwaway 100k-row
  database — including the full backup/restore chain, live blocking capture, the implicit-
  conversion seek-vs-scan comparison, and the safety ritual. Numbers quoted (59 vs 256
  reads, 84.7% impact, counter 30002) are from those runs; an earlier draft's "554 vs 2
  reads" pair had no surviving artifact and was replaced with the corroborated pair.
  The extended benign-waits exclusion list in 3.3-C (dispatcher/idle waits) was re-run
  verbatim against the same LocalDB build on 2026-07-07: idle noise gone, remaining top
  waits were genuine (tiny) startup waits.
- Not exercised locally (Express/LocalDB limits): parallel-plan behavior beyond confirming its
  absence, Enterprise-only features, Azure SQL behavior, SQL Agent. Claims in those areas are
  stated generally and flagged "verify for your edition/version".
- Volatile parts and re-verification one-liners:
  - Engine version/edition facts: `sqlcmd -S <SERVER> -E -Q "SELECT @@VERSION;"`.
  - Edition feature differences: check the official "Editions and supported features of SQL
    Server <VERSION>" page for the target version; they move between releases.
  - The benign-waits exclusion list in 3.3-C: new versions add wait types; extend the list
    when a top wait is clearly idle/background.
  - DMV column additions: `SELECT TOP (0) * FROM sys.dm_exec_query_stats;` to see the current
    shape on a new version.
- Instantiated copies must add their own provenance: server, version/edition, uptime at
  observation, dates, and who ran each discovery step.
