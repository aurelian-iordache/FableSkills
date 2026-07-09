---
name: domain-reference
description: Load this skill when you must author, review, or extend a project's domain-theory knowledge pack — the field math, protocols, and standards (RFCs, ISO specs, numerical-precision rules, regulatory clauses) that govern specific lines of code, and that a mid-level engineer or small model will silently get wrong without. Triggers include "document the domain knowledge", "why is this constant 86400", "what does the spec say here", "write the theory reference for <PROJECT>", finding unexplained magic numbers or validation rules, or onboarding someone into a standards-heavy codebase (payments, networking, crypto, geodesy, medical, audio/DSP). Delivers scoping rules, a per-entry structure, citation/verification standards, and a codebase-mining procedure.
---

# domain-reference — Authoring the Domain Knowledge Pack

## Purpose

This skill makes you able to write the **domain knowledge pack**: the single document that carries the field theory (math, protocols, standards, units, precision rules) *as it applies to one project* — so a zero-context mid-level engineer or Sonnet-class model can make the same decisions a domain expert would, at the exact lines of code where those decisions live. It is not a textbook. It is the minimum theory that changes a decision someone will actually make in this repo.

## When to use / When NOT to use

Use when:
- You are instantiating this library into a real repo and the repo touches any external standard, protocol, physical unit, or nontrivial math.
- You found an unexplained constant, threshold, or validation rule and are about to document why it is what it is.
- A reviewer asked "is this actually what the spec says?" and nobody could answer from a doc of record.

Do NOT use when the question is really a sibling's job:

| If instead you need... | Use sibling skill |
|---|---|
| WHY a design decision was made (tradeoffs, invariants, ADRs) | architecture-contract |
| Cataloging tunable settings, defaults, and flag guards | config-and-flags |
| The story of a past bug/incident behind a rule | failure-archaeology |
| First-principles proof that code implements the math correctly | proof-and-analysis |
| House style, doc templates, keeping docs from rotting | docs-and-writing |
| The overall repo-discovery and skill-instantiation protocol | skill-factory |

Boundary rule: **architecture-contract** records *choices the team made*; **domain-reference** records *facts the world imposed* (the spec, the math, the physics). A constant lives here if an external standard fixes its value or meaning; it lives in **config-and-flags** if the team may tune it.

## Core doctrine

### Definitions (terms of art, defined once)

- **Knowledge pack**: the project-specific domain-reference document, made of *entries* (see structure below).
- **Governing-line test**: the admission test for any fact — "which line of code or config does this fact govern?" If you cannot name a file (or a decision someone will make about a file), the fact does not enter the pack.
- **Load-bearing claim**: a domain statement that, if wrong, produces a wrong line of code. Load-bearing claims require primary-source citations.
- **Primary source**: the standard itself (RFC, ISO/IEC, IEEE, W3C, ECMA, NIST publication), a peer-reviewed paper, or official normative vendor documentation for a proprietary protocol. Everything else (blog posts, Stack Overflow, textbooks without citation, model memory) is secondary at best.
- **Latent domain knowledge**: theory already encoded in the repo — in constants, validation rules, thresholds — but written down nowhere.

### Rule 1 — Scoping: only theory that changes a decision

Admission checklist for every candidate fact. All three must pass:

- [ ] **Governing-line test passes**: you can name the file/function/config key this fact governs, or the concrete upcoming decision it will steer ("choosing the rounding mode in the new refund path").
- [ ] **Mid-level gap test passes**: a competent generalist would plausibly get this wrong or not know to ask. (`HTTP GET has no body semantics` — borderline; `ISO 4217 says JPY has 0 decimal places` — yes, people divide by 100 anyway.)
- [ ] **Not already owned by a sibling**: it is a fact about the world, not a team choice (→ architecture-contract) or a tunable (→ config-and-flags).

Heuristic sizing: a healthy pack for a mid-size project is 10–40 entries. If you have 100+, you are writing a textbook; re-run the governing-line test on every entry.

### Rule 2 — Entry structure (mandatory, all five parts)

Every entry uses exactly this shape. An entry missing any part is incomplete.

```markdown
### <Short concept name>

**Concept.** One–three sentences of the theory, in plain language.

**Why it matters here.** The project-specific consequence — what goes wrong
in THIS system if you ignore it.

**Governing rule.** The equation, algorithm, or spec clause — with a primary
citation down to section/clause number. E.g. "RFC 9110 §9.3.1", "ISO 8583-1:2003,
data element 4", "IEEE 754-2019 §3.4".

**Code/config it touches.** Concrete paths: `src/…/file.ext:function`, config
keys, schema columns. This is the governing-line test made permanent.

**The mistake without it.** The specific wrong code a reasonable person writes
when they don't know this. Show the wrong line if you can.
```

Why the fifth part is mandatory: the "mistake" line is what lets a reader recognize the trap *while writing code*, before they think to open the pack. It is the retrieval key.

### Rule 3 — Verification standards for domain claims

| Claim tier | Source required | Citation format |
|---|---|---|
| Load-bearing (wrong ⇒ wrong code) | Primary source, exact section | `RFC 8446 §4.1.2`; `ISO 4217:2015, minor-unit table`; `IEEE 754-2019 §4.3.1`; DOI or full ref for papers |
| Supporting context (helps intuition) | Any reputable source, labeled | "(background: <SOURCE>)" |
| Empirical/project-observed | Reproduction command or commit hash | "observed; repro: `<CMD>`; see commit `<SHA>`" |

Hard rules:
1. **Never cite blog folklore as load-bearing.** A blog post may point you *to* the spec clause; the pack cites the clause. If you cannot find a primary source for a load-bearing claim, mark it `UNVERIFIED — do not build on this` in the pack rather than laundering a secondary source.
2. **Cite section numbers, not documents.** "Per RFC 9110" is not checkable in bounded time; "RFC 9110 §8.3" is. Same for ISO clauses, IEEE sections, and paper equation numbers.
3. **Runnable checks beat quotes where possible.** If a claim can be demonstrated in 1–3 lines of code (`python3 -c "print(0.1 + 0.2)"`), include the command and its expected output next to the citation. Readers trust what they can re-run.
4. **Model memory is a secondary source.** If you (an AI author) recall a spec detail, you must confirm it against the spec text or a runnable check before it may be load-bearing. Recalled-but-unconfirmed facts get the `UNVERIFIED` label.
5. **Paywalled standards** (many ISO/IEC docs): cite the clause anyway, and additionally cite the best freely-checkable corroboration (e.g. a national-body mirror, the Wikipedia table *explicitly labeled as corroboration only*). Never silently substitute the free source as the authority.

### Rule 4 — Extracting latent domain knowledge from a codebase

The best entry candidates are already in the repo, unexplained. Mine in this order (commands are real syntax; run from repo root):

1. **Constants with no explanation.** Numeric literals of 4+ digits, or any literal with units in the name:
   ```
   rg -n '\b\d{4,}\b' --type-add 'code:*.{py,ts,js,go,cs,java,rs,c,cpp,h}' -t code
   rg -n -i '(timeout|epsilon|tolerance|max_|min_|threshold|factor|scale)\w*\s*[:=]'
   ```
   For each hit: is the value fixed by a standard (→ entry here), tunable (→ config-and-flags), or arbitrary (→ note as candidate tech debt)?
2. **Validation rules.** Regexes, length checks, range checks, checksum functions:
   ```
   rg -n 'raise|throw|assert|validate|is_valid|check' -g '!*test*'
   ```
   A validation rule is a domain claim in executable form. Find which spec clause it implements; if it implements none, flag it — it may be wrong.
3. **Magic thresholds.** Comparisons against literals (`> 0.5`, `>= 3`, `!= 65535`). Each one encodes either a spec limit, an empirical calibration, or a guess. The pack must say which.
4. **Comment archaeology.** Comments that gesture at theory without citing it:
   ```
   rg -n -i 'per (the )?(spec|rfc|standard)|according to|see rfc|iso[ -]?\d|ieee|because .*(spec|protocol)'
   rg -n 'TODO|FIXME|HACK|XXX' -g '!*test*'
   ```
5. **History of the constant.** For any suspicious value, find the commit that introduced it and read its message and linked issue:
   ```
   git log -S '<LITERAL-VALUE>' --oneline
   git log --follow -p -- <FILE>
   git blame -L <START>,<END> <FILE>
   ```
   If the introducing commit cites an incident, cross-link the entry to **failure-archaeology** instead of retelling the story.
6. **Dependency tells.** Manifest entries reveal domain surface: a `libphonenumber`, `pint` (units), `noda-time`, or decimal-arithmetic dependency each implies a family of entries.

For every mined item, run the Rule 1 admission checklist before writing the entry.

### Rule 5 — Contested and version-dependent facts

Domain facts change: standards get revised (ISO 8583:1987 → :1993 → :2003), RFCs get obsoleted (RFC 2616 → 9110–9112), regulatory thresholds move, and some questions have no consensus answer.

- **Always state the version/edition of the standard** in the citation: `ISO 8583-1:2003`, not `ISO 8583`. If the project targets an older edition on purpose, say so and say why (link the architecture-contract ADR if one exists).
- **Date-stamp volatile claims**: `"As of 2026-07: <FACT>. Re-verify: <one-line command or URL>."` Anything regulatory, pricing-related, or tied to a living standard (Unicode, TZ database, currency lists) is volatile by default.
- **Contested facts get both positions**, each cited, plus the project's chosen position and where that choice is recorded: `"Sources disagree on X (A says …, B says …). This project follows A per <ADR-OR-COMMIT>. Revisit if <CONDITION>."` Never present a contested fact as settled.
- **Obsoleted specs**: if code was written against an obsoleted document, cite what the code actually implements AND note the successor: `"implements RFC 2616 §14.9 semantics; note RFC 9111 changed <DETAIL>."`

### Rule 6 — The textbook-dump anti-pattern

The dominant failure mode of domain packs is the *textbook dump*: pages of correct, well-written field theory that governs nothing in the repo. It feels productive and rots instantly.

Enforcement rules:
- **Cut-at-instantiation rule**: when this template is instantiated for a real project, any section or entry that does not name a file, config key, or pending decision in that project **gets cut**. No exceptions for "nice background".
- The generic-template version of a pack may contain placeholder entries; the instantiated version may not contain entries whose "Code/config it touches" line is empty or hand-wavy ("various places").
- Ban intro chapters ("A Brief History of X"). If context is genuinely needed, it goes inside an entry's **Concept** line, capped at three sentences.
- Review probe: pick three random entries and ask a colleague/model to state, from the entry alone, what code change the entry would prevent or cause. If they can't, the entry fails.

### Failure modes of this method itself

| Failure | Symptom | Countermeasure |
|---|---|---|
| Textbook dump | Entries with no file paths | Cut-at-instantiation rule (Rule 6) |
| Citation laundering | Blog claim dressed with an RFC number nobody opened | Spot-check: open 3 random citations per review; a fabricated section number fails the whole pack |
| Fossilized versions | Pack cites a spec edition the code no longer targets | Date-stamps + re-verification commands (Rule 5); re-check on dependency upgrades |
| Sibling bleed | Entries retelling incidents or defending design choices | Boundary rule in "When to use"; link out instead |
| False precision | `UNVERIFIED` claims silently promoted to load-bearing | Grep the pack for `UNVERIFIED` in every review; each one is either resolved or still labeled |

## Worked example

**Illustrative example — every project detail below is fictional.** The pack excerpt is for "Acme PayCore", a made-up card-payments switch. The *standards facts* cited (ISO 8583 field 4, ISO 4217 exponents, IEEE 754 binary64 behavior) are real and were chosen because they are verifiable; the file paths and project decisions are invented to show the entry format.

```markdown
### Amounts travel as minor units, and the exponent is per-currency

**Concept.** Card networks transmit money as integer counts of a currency's
minor unit, and the number of minor-unit digits (the "exponent") varies by
currency: USD has 2, JPY has 0, BHD has 3.

**Why it matters here.** PayCore stores `amount_minor` (integer) plus
`currency` and converts to display units only at the UI edge. Any code that
assumes "divide by 100" corrupts JPY (100x too small) and BHD (10x too big).

**Governing rule.** ISO 8583-1:2003, data element 4 ("Amount, transaction"):
n 12, expressed in minor currency units. Minor-unit exponents per currency:
ISO 4217:2015 minor-unit column. (ISO texts paywalled; corroboration only:
any current ISO 4217 published list.)

**Code/config it touches.** `settlement/amount.py:to_display()`,
`iso8583/encode.py:pack_de4()`, DB column `ledger.amount_minor`,
lookup table `settlement/currency_exponents.py`.

**The mistake without it.** `display = amount_minor / 100` — correct for
USD/EUR, silently wrong for ~50 currencies. As of 2026-07 the exponent
table is vendored; re-verify against the current ISO 4217 list on update.

### Never hold money in binary floating point

**Concept.** IEEE 754 binary64 ("double") cannot represent most decimal
fractions exactly; decimal arithmetic on doubles accumulates representation
error.

**Why it matters here.** PayCore fee calculation multiplies amounts by
percentage rates. Done in doubles, per-transaction rounding differences of
1 minor unit appear at scale and break end-of-day reconciliation
(ledger vs. network totals must match exactly).

**Governing rule.** IEEE 754-2019 §3.6, Table 3.5 (binary64: p = 53, i.e.
53-bit significand; decimal fractions like 0.1 have no exact binary
representation — encodings are defined in §3.4).
Runnable check: `python3 -c "print(0.1 + 0.2)"` → `0.30000000000000004`;
`python3 -c "print(round(2.675, 2))"` → `2.67` (not 2.68 — the stored
value is just below 2.675). Integers are exact only up to 2^53:
`python3 -c "print(float(2**53) == float(2**53 + 1))"` → `True`.

**Code/config it touches.** `fees/calc.py` (uses `decimal.Decimal` with
explicit context, ROUND_HALF_EVEN per fictional PayCore ADR-012),
lint rule `no-float-money` in `.lint/rules.yml`.

**The mistake without it.** `fee = round(amount_minor * 0.0275)` in float —
passes every small unit test, drifts at volume. Also: keeping amounts as
integer minor units in a double is safe below 2^53 but the safety is
accidental; the lint rule bans it anyway.
```

Note what the excerpt does: five parts per entry, section-level citations, runnable checks with expected output, real file paths (fictional but specific), the wrong line of code spelled out, a date-stamp on the volatile currency table, and a link out to an ADR rather than re-arguing the rounding-mode choice.

## Instantiate for your project

Produce `.claude/skills/<PROJECT>-domain-reference/SKILL.md` in the target repo. A Sonnet-class model can execute this unaided.

1. **Identify the domain surface.** Run, from repo root:
   ```
   rg -n -i 'rfc[ -]?\d{3,4}|iso[ /-]?\d{3,5}|ieee|w3c|nist|spec(ification)?|protocol' -g '!*lock*'
   cat <MANIFEST>            # package.json / pyproject.toml / *.csproj / go.mod ...
   git log --oneline -20
   ```
   List every external standard, protocol, unit system, or math area the project touches. If the list is empty and stays empty after step 2, this project may not need a domain pack — record that finding and stop.
2. **Mine latent knowledge.** Run the full Rule 4 command sequence (constants, validations, thresholds, comment archaeology, `git log -S` on each suspicious literal). Collect candidates into a scratch list with file:line for each.
3. **Apply the admission checklist** (Rule 1) to every candidate. Route rejects to the correct sibling (config-and-flags, architecture-contract, failure-archaeology) as one-line TODOs in those skills' instantiation notes.
4. **Draft entries** using the mandatory five-part structure. Evidence gate: **do not write a "Governing rule" line you have not confirmed against a primary source or a runnable check in this session; do not write a "Code/config it touches" line you have not opened the file to confirm.** Unconfirmable claims get `UNVERIFIED — do not build on this`.
5. **Apply the cut-at-instantiation rule** (Rule 6): delete any entry with no concrete file/config/decision reference, including any of this template's illustrative material.
6. **Fill the skeleton:**
   ```markdown
   ---
   name: <PROJECT>-domain-reference
   description: Domain theory governing <PROJECT>: <the 3–5 standards/areas found in step 1>. Load before touching <the files most entries point at>.
   ---
   # <PROJECT> Domain Reference
   ## Scope
   Standards/areas covered: <list, with edition/version for each>.
   Explicitly out of scope: <adjacent theory that governs nothing here>.
   ## Entries
   <five-part entries, grouped by subsystem or standard>
   ## Unverified claims (do not build on these)
   <UNVERIFIED items with what would resolve each>
   ## Provenance
   Instantiated <DATE> from FableSkills domain-reference. Sources opened this
   session: <LIST>. Volatile entries and their re-verification commands: <LIST>.
   ```
7. **Review probes before calling it done:**
   - [ ] Open 3 random citations; confirm each section number says what the entry claims.
   - [ ] Run every runnable check; paste actual output into the entry if it differs.
   - [ ] Governing-line audit: every entry names at least one real path that exists (`ls` each).
   - [ ] `rg -n 'UNVERIFIED' <PACK-FILE>` — each hit is deliberate and labeled.

## Provenance and maintenance

Authored 2026-07-06 against no specific project; all project details in the worked example are fictional and labeled as such. Standards facts used illustratively (ISO 8583-1:2003 DE 4; ISO 4217 minor-unit exponents; IEEE 754-2019 binary64) were chosen for verifiability; the three Python runnable checks were executed on 2026-07-06 with the outputs shown.

Volatile parts and re-verification:
- `rg` flag syntax (`--type-add`, `-g`): `rg --help` — verified 2026-07-06.
- `git log -S`, `git log -G`, `git blame -L`, `git log --follow -p`: `git log --help` / `git blame --help` — executed successfully 2026-07-06.
- Ecosystem examples (dependency names like `pint`, `libphonenumber`) drift; treat as illustrations, not an inventory.
- RFC/ISO edition numbers cited in examples will be superseded eventually; instantiated packs must cite the editions *their* project targets, per Rule 5.

Instantiated copies must add their own provenance block (step 6) listing sources actually opened and the date, and must re-run the review probes (step 7) whenever a dependency carrying domain logic is upgraded or a cited standard is revised.
