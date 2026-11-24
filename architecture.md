# Architecture: a failure reaches the package that can fix it, with its failing lines (agentic-flow 2.21.1)
Type: fix · Size: standard

## 1. Goal

A real run of a PowerShell project (`wf_15d1d178-538`, ended REVIEW at "fix wave 1" with 11 gate denials) showed three defects of the flow. First, without a test report, `verify` and the stop gate read the console minus the lines of passing tests, so Pester's `Describing AC-6xx` and `Context` headers of passing tests were kept, and `attribute` sent three packages to fix criteria whose tests passed. Second, the fix's `evidence` is built from the phase's `tail` (its last 8 lines): the regression's own `new_failures` (`[-] XMM-Panel.ps1 has UTF-8 BOM, CRLF only and no non-ASCII`) never reached the package, and a failing acceptance phase carries no lines at all. Third, the denials of the zone stop gate (test-author and QA, design 0029) are not in the run's record, so nobody can tell whether it acted. This release fixes the three, in both engines, which stay equivalent.

## 2. Scope

### Included

- **Pester headers (bug 1).** In the console fallback of `scan_lines` (no `reports` declared, or a report that cannot be read), a `Describing`/`Context` header line is kept only when a failing line follows it inside its block. A header of passing tests no longer names a package. The `reports` path does not change.
- **Failing lines as evidence (bug 2).** `verify` adds `failing_lines` to every phase that blocks (status `regression` or `fails`), the acceptance phase included. Both engines build each failing phase's evidence from `new_failures`, else `failing_lines`, else `tail`.
- **Zone denials in the record (bug 3).** `close-stage` adds `AT=n` / `QA=n` to its `GATE:` line when that zone was refused at least once; both engines read them, after wave 0 and after QA, into `gate_denials`.
- **Docs and release 2.21.1.** The guide's lines, `/implement`'s presentation of `gate_denials`, the notes, the budget, the version pin of `test_acceptance_v221.py`, and one acceptance file.

### Excluded (non-goals)

- The project's own plan (its `reports` with Pester's NUnitXml, the missed test `FeatureFlagList AC-001` in its 4b): a note to the user, not this flow.
- What the stop gate shows a package: `own_failure` keeps returning the lines that name the package's markers (section 11).
- `verification_failures` in the result keeps `tail` as today.
- `qa_passes`: it was `[]` in that run because the run stopped before QA. Expected, not a bug.
- Any agent definition, prompt template or schema.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`
- Bench: `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/bin/verification.py            WP-01  Pester headers in the console fallback; failing_lines in verify
.claude/bin/stage.py                   WP-01  AT=n / QA=n in close-stage's GATE line
.claude/bin/test_failure_lines.py      WP-01  new: unit cases
.claude/bin/pipeline.py                WP-02  evidence from the failing lines; zone denials summed
.claude/workflows/agentic-implement.js WP-02  the same, in the native engine
.claude/bin/conformance.json           WP-02  three new scenarios
.claude/bin/test_pipeline.py           WP-02  EngineTests: what the new scenarios end with
docs/how-it-works.md                   WP-03  the stop gate's and the failed verifications' lines
.claude/commands/implement.md          WP-03  the gate_denials line
.claude-plugin/plugin.json             WP-03  2.21.1
.claude/bin/upgrade.py                 WP-03  NOTES["2.21.1"]
.claude/flow-budget.json               WP-03
.claude/bin/test_acceptance_v221.py    WP-03  its version pin: 2.21.1
.claude/bin/test_failure_evidence.py   AT
.claude/flow-history.json              by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| `FAILURE_LINE_RE` (a failing line, Pester's `[-]` included) and `PASS_LINE_RE` (a passing test's line, Pester's `[+]` included) | `.claude/bin/verification.py:21`, `.claude/bin/verification.py:34` | Unchanged. The header regex goes beside them | read |
| `failure_lines(lines)`: the lines that match `FAILURE_LINE_RE`, normalised by `normal_failure` (no durations, counts or repeated spaces), sorted, without repeats | `.claude/bin/verification.py:211-218` | `failing_lines` is its first 10 | read |
| `scan_lines(manifest, key, console)`: with a report read, one line per failing test; otherwise `[line for line in console if FAILURE_LINE_RE.search(line) or not PASS_LINE_RE.search(line)]` | `.claude/bin/verification.py:220-229` | Only the second branch changes | read |
| Its three callers: `run_phases` (every verify phase, and the baseline), `verify` (the acceptance phase), `gate_check` (the stop gate of a package) | `.claude/bin/verification.py:231-245`, `.claude/bin/verification.py:353-360`, `.claude/bin/stage.py:325-352` | The fix reaches all three through `scan_lines` | read |
| `attribute(manifest, lines, by_criteria=True)`: a package is a suspect when the lines name one of its files or, by criteria, one of its `acs` (`AC-NNN` anywhere in the text) | `.claude/bin/verification.py:247-266` | Unchanged: it reads what `scan_lines` keeps | read |
| `verify`: per phase `status` (`ok`, `pre-existing failure`, `regression`, `fails`); a regression gets `new_failures = new[:10]` and its `_scan` filtered to the new lines; the acceptance phase is `{name, command, passed, verdict, status, _scan}` with no `tail`; the suspects loop pops `_scan` from every phase | `.claude/bin/verification.py:327-378` | `failing_lines` is set in that loop, where `_scan` is popped | read |
| The baseline saves `failures` (every `failure_lines` of a failing phase) and `verify` compares with it | `.claude/bin/verification.py:307-325`, `.claude/bin/verification.py:338-341` | Hence the new key is `failing_lines`, not `failures`: the baseline's key keeps its meaning | read |
| `close_stage` prints `GATE: WP-01=1 WP-02=0` for the packages it closes, from `gate_denials(lambda d: None)` | `.claude/bin/stage.py:236-277` (the GATE line at 268-271) | Zones are added there, only when their count is above 0 | read |
| A test pins that a QA stage prints no GATE line when QA was not refused | `.claude/bin/test_guardrail.py:241-249` | Must stay green: hence "only when above 0" | read |
| `gate_line(output)` in the fallback engine and `gateLine(out)` in the workflow read `(WP-\d+)=(\d+)` from the `GATE:` line | `.claude/bin/pipeline.py:93-96`, `.claude/workflows/agentic-implement.js:300-305` | The regex widens to `(WP-\d+\|AT\|QA)` | read |
| The engines sum the denials after a wave closes, only from `close-stage <wave>` | `.claude/bin/pipeline.py:470-478`, `.claude/workflows/agentic-implement.js:470-471` | The same sum after wave 0 closes and after QA closes | read |
| Wave 0 closes with `close-stage acceptance AT=<state> --expect red`, once per round; a revision round reopens the stage (`open-stage acceptance`, which resets AT's counter) | `.claude/bin/pipeline.py:360-372`, `.claude/bin/pipeline.py:390`, `.claude/workflows/agentic-implement.js:724-731`, `.claude/workflows/agentic-implement.js:746` | Summing every round's line counts each denial once | read |
| QA closes through `seq([close_qa, ...])`: `step(fin, 0)` is the `close-stage qa` step, in both of its branches | `.claude/bin/pipeline.py:705-729`, `.claude/workflows/agentic-implement.js:805-825` | Its output is read from `step(fin, 0).output` | read |
| `seq` of one command returns `{steps: [{cmd, exit_code, output}]}`; of several, the JSON of `agentic.py seq` | `.claude/workflows/agentic-implement.js:190-198` | Same shape for both | read |
| `verification_defects` / `verificationDefects` build one `evidence` from every failing phase: `name + ": " + tail.join("\n")`, cut at 1500 characters | `.claude/bin/pipeline.py:280-293`, `.claude/workflows/agentic-implement.js:348-356` | The function that changes in both engines | read |
| The conformance scenarios: each engine runs a simulated world declared in `conformance.json`; `ConformanceTests` compares `prompts` and `gate_denials` among other keys; `run_scenario(decl)` runs one in the fallback engine and returns its summary, `prompts` keyed `"<agent type>:<id>#<n>"` | `.claude/bin/test_pipeline.py:199-226`, `.claude/bin/test_pipeline.py:154-166` | The acceptance tests use `run_scenario` and `test_workflow.mjs --dump` | read |
| The simulated world splits a `seq a + b` into steps and answers each by `gate_fail` prefix; `verify` answers come from a scenario's `verify` list | `.claude/bin/test_workflow.mjs:54-57`, `.claude/bin/test_workflow.mjs:517`, `.claude/bin/test_pipeline.py:51-60` | A scenario can give `close-stage qa` and `close-stage acceptance` their own output | read |
| The existing scenarios "verification fails on a package: it is fixed and verified again" and "gate denials are summed from close-stage" | `.claude/bin/conformance.json:50`, `.claude/bin/conformance.json:793` | The shape of the new ones | read |
| Pester tests with and without a report: `test_ac_005` (report), `test_ac_006` (console, pytest lines), `test_ac_009` (the stop gate reads the report) | `.claude/bin/test_runner_reports.py:207-230`, `.claude/bin/test_runner_reports.py:275-285` | They stay green | read |
| `new_failures` is pinned by tests | `.claude/bin/test_runner_reports.py:231-247`, `.claude/bin/test_agentic.py:686`, `.claude/bin/test_agentic.py:710` | Unchanged | read |
| The release pattern of a fix | `.claude/bin/upgrade.py:156-161`, `.claude/bin/test_quality_limits.py:158-170` | `NOTES["2.21.1"]` right above `"2.21.0"` | read |
| The last minor release's acceptance file pins `2.21.0` | `.claude/bin/test_acceptance_v221.py:140-153` | Only the pin changes | read |
| Tests pinning `implement.md`: one line with `` `zone_suspects` ``; `` `gate_denials` `` present | `.claude/bin/test_quality_limits.py:149-155`, `.claude/bin/test_definitions.py:231-235` | Stay green | read |
| The fix call's label is `"<wp> (fix)"`, so its prompt key is `implementer:<wp> (fix)#<n>` | `.claude/bin/pipeline.py:415`, `.claude/bin/test_fix_cycles.py:132` | The key AC-005 reads | read |
| The guide's lines on the stop gate and on failed verifications; `/implement`'s line on `gate_denials` | `docs/how-it-works.md:389`, `docs/how-it-works.md:391`, `.claude/commands/implement.md:71` | Lines to extend | read |
| What Pester 4 and 5 print on the console (`Describing`, `Context`, `[+]`, `[-]`, indentation) | not measured: no Pester run in this session | Section 11 | inferred |

What must not change: the `reports` path, `attribute`, `own_failure`, the baseline's `failures`, the package gate's `GATE:` output, the stages' `check`, `verification_failures`.

## 5. Data model

```python
# verification.py, beside PASS_LINE_RE
HEADER_LINE_RE = re.compile(r"^\s*(?:Describing|Context)\s+\S")  # Pester's block headers: a test's name, not a result
MAX_FAILING_LINES = 10  # as new_failures
```

A **summary line** is a line `COUNT_BEFORE_RE` matches (`.claude/bin/verification.py:29-30`) that is not a Pester failing test (`^\s*\[-\]`; `[-] reports Errors: 0 for a clean file` is a failing test): Pester's `Tests Passed: 2, Failed: 1, Skipped: 0`. It names no test, so it keeps no header and it closes every open block; it is itself kept, as today.

A blocking phase of `verify`'s output gains one key:

```json
{"name": "acceptance", "command": "...", "passed": false, "verdict": "...", "status": "fails",
 "failing_lines": ["[-] XMM-Panel.ps1 has UTF-8 BOM, CRLF only and no non-ASCII"]}
```

`failing_lines` = `failure_lines(<the phase's _scan>)[:MAX_FAILING_LINES]`, on every phase whose status is `regression` or `fails`, possibly `[]`. Phases with another status do not get it.

`close-stage`'s summary line, examples:

```
GATE: WP-01=1 WP-02=0          (a wave: unchanged)
GATE: AT=1                     (close-stage acceptance AT=done after one zone denial)
                               (close-stage qa QA=pass with no denial: no GATE line, as today)
```

`gate_denials` in the result may now hold `"AT"` and `"QA"` beside package ids: `{"WP-01": 3, "AT": 1}`. Like a package, a zone appears only with a sum above 0.

The evidence of one failing phase, in both engines:

```
<name>: <lines joined by "\n">
lines = new_failures if it is a non-empty list, else failing_lines if non-empty, else tail (or [])
```

The phases are joined by `"\n"` and the whole text is cut at 1500 characters, as today.

## 6. Contracts between modules

**`verification.py`:**

```python
def console_lines(console)
    """The console lines that failure comparison and attribution read when no report is read: every line that is
    not a passing test's, except a Pester block header (HEADER_LINE_RE), which is kept only when a failing line
    (FAILURE_LINE_RE) follows it inside its block. A `Describing` opens a block and closes the one before; a
    `Context` opens a block inside the current `Describing` and closes the previous `Context`. The headers that
    enclose a failure are kept once, in their order, right before the first failing line under them. A header is
    never kept because its own text matches FAILURE_LINE_RE. A summary line (COUNT_BEFORE_RE: "Tests Passed: 2,
    Failed: 1"), unless it starts with "[-]", is not a failing line for this rule: it keeps no header and closes
    every open block."""
```

`scan_lines` returns `console_lines(console)` in place of today's comprehension, with the same `state`.

`verify(manifest)`: as today, plus `failing_lines` on every blocking phase (section 5), set where `_scan` is popped (after a regression's `_scan` has been filtered, so a regression's `failing_lines` are its new lines).

**`stage.py`:** `close_stage` keeps the package part of the `GATE:` line as is. For each mark whose id is `AT` or `QA` with a denial count above 0, it appends `<id>=<n>`; it prints the line when the line has at least one entry. Order: packages first, in the order of the marks, then the zones, in the order of the marks.

**Both engines** (`pipeline.py`, `agentic-implement.js`), equivalent in every scenario:

- `gate_line(output)` / `gateLine(out)` return `{id: n}` for `(WP-\d+|AT|QA)=(\d+)`.
- One helper, `add_gate_denials(output)` / `addGateDenials(out)`, adds each `n > 0` to `run.gate_denials[id]`; a missing or null output adds nothing. The wave close (`.claude/bin/pipeline.py:475-477`, `.claude/workflows/agentic-implement.js:471`) calls it in place of today's loop.
- One more, `close_seq(cmds, label)` / `closeSeq(cmds, label)`: runs `seq(cmds, label)`, calls the helper with the output of its first step when there is one, and returns what `seq` returned. Wave 0's `close-stage acceptance` and both QA closes call `close_seq` in place of `seq`, on the same line: `runAfterPlan` (126 lines, allowance 128) and `Pipeline.judge` (71 lines, allowance 73) may not grow. Since it runs before any `stop`, a failed close still records its denials.
- "A non-empty list" is `isinstance(x, list) and x` in Python and `Array.isArray(x) && x.length` in JS.
- `verification_defects(v)` / `verificationDefects(v)`: the evidence of section 5. Nothing else changes in a defect.

## 7. Conventions

- English everywhere; usage errors keep the `Uso:` prefix (design 0016).
- No type annotations in signatures (Python 3.9), as in the rest of `.claude/bin`. This overrides the python rules' "type annotations on every public signature": it is the existing code's style, not a finding.
- Every `open` and `read_text` names `encoding="utf-8"`.
- The two engines change together: a scenario that differs in `prompts` or `gate_denials` fails `ConformanceTests`.
- This repository's own quality phase measures `.claude/bin` and `.claude/workflows`, the tests of this design included: no line over 120 characters, no new function over 60 lines (100 in a test), no new file over 800 lines. Recorded allowances that this design reaches (`.claude/quality-baseline.json`): `agentic-implement.js` 861 lines (831 today) and 64 lines over 120 characters (64 today); `agentic-implement.js::runAfterPlan` 128 lines (126 today); `pipeline.py::Pipeline.judge` 73 lines (71 today); `test_pipeline.py` 16 lines over 120 characters (16 today). None of them may grow: a new long expression is split. `pipeline.py` is at 773 of 800 lines.
- `test_agentic.py` (1,875 lines) and `test_guardrail.py` do not grow: new unit cases go in `test_failure_lines.py`.
- The guides do not cite flow version numbers. Commit format `type: summary`; the flow history is regenerated as the last commit.

## 8. Work packages and acceptance criteria

### Acceptance criteria

The console of AC-001 and AC-002, written by a script `t.py` that prints it and exits 1 (the shape of `.claude/bin/test_runner_reports.py:207-230`):

```
Describing AC-601 launcher
  [+] starts 3ms
Describing AC-602 settings
  Context AC-605 flags
    [+] lists the flags 2ms
Describing FeatureFlagList
  [-] XMM-Panel.ps1 has UTF-8 BOM, CRLF only and no non-ASCII 5ms
Tests Passed: 2, Failed: 1
```

The manifest of AC-001 to AC-003: three packages `WP-01` (`acs` `["AC-601"]`), `WP-02` (`["AC-602"]`), `WP-03` (`["AC-605"]`), each owning one file under `src/` that no output names, `verify` `{"tests": "<python> t.py"}`, no `reports`.

- AC-001 · A Pester header of passing tests names no package (reproduces bug 1)
  - Scenario: the manifest and console above, in a temporary repo built by the tests' `Repo` helper (`.claude/bin/test_agentic.py:45-76`).
  - Action: `agentic.py verify`.
  - Expected: exit 3; `blocking` contains `tests`; `suspects` is `{}`. Today it is `{"WP-01": …, "WP-02": …, "WP-03": …}`. The same with the `Describing AC-601 launcher` block (header and `[+]` line) moved to the end, right before the summary line, and again with the summary line replaced by `Tests Passed: 3, Failed: 0`: `suspects` is `{}` in both.
  - Must not: any package in `suspects`; a header kept by the summary line; a `Traceback` on stderr.
  - Check: `test_failure_evidence.py`
  - WP: WP-01

- AC-002 · A failing test keeps the header that names its criterion, at both levels
  - Scenario: as AC-001, with the console changed: (a) the `[-]` line moved right under `Describing AC-602 settings` (before its `Context`); (b) the `[-]` line moved under `Context AC-605 flags`; (c) (a)'s console with a passing block prepended: `Describing AC-603 failure handling` and one `[+]` line.
  - Action: `agentic.py verify` in each.
  - Expected: (a) `suspects` has exactly `WP-02`, with `acs` `["AC-602"]`; (b) exactly `WP-02` and `WP-03` (the `Context` is inside `AC-602`'s block); (c) exactly `WP-02`, and no package answers for `AC-603` (the manifest of (c) gives `WP-01` `acs` `["AC-601", "AC-603"]`).
  - Must not: a package whose criterion's block has no failing line; a header kept because its words match `FAILURE_LINE_RE`.
  - Check: `test_failure_evidence.py`
  - WP: WP-01

- AC-003 · The stop gate does not refuse a package for a passing header
  - Scenario: the manifest of AC-001 with `acceptance.command` `<python> acc.py`, where `acc.py` prints the console of AC-001 and exits 1; no `reports`.
  - Action: the hook receives an implementer's `DONE` report with `AGENTIC_WP=WP-02` (the payload of `.claude/bin/test_runner_reports.py:270-273`).
  - Expected: exit 0; `.claude/state/gate.json` gains no `WP-02` entry. With the `[-]` line moved under `Describing AC-602 settings`, the same call exits 2 and stderr contains `AC-602`.
  - Must not: a denial for a criterion whose tests pass.
  - Check: `test_failure_evidence.py`
  - WP: WP-01

- AC-004 · Every blocking phase lists its failing lines, the acceptance phase included
  - Scenario: a repo with one package (`acs` `["AC-001"]`), `verify` `{"tests": "<python> t.py"}` where `t.py` prints `FAILED acceptance/test_x.py::test_ac_001_total - assert 3 == 4` and `1 failed, 4 passed in 0.12s` and exits 1, and an acceptance command that prints `[-] XMM-Panel.ps1 has UTF-8 BOM, CRLF only and no non-ASCII` and exits 1. No baseline.
  - Action: `agentic.py verify`.
  - Expected: the `tests` phase has `status` `fails` and `failing_lines` containing a line with `test_ac_001_total`; the `acceptance` phase has `status` `fails` and `failing_lines` == `["[-] XMM-Panel.ps1 has UTF-8 BOM, CRLF only and no non-ASCII"]`; each `failing_lines` has at most 10 entries (a `t.py` printing 15 distinct `FAILED` lines gives 10). With both commands exiting 0, no phase has `failing_lines`.
  - Must not: `failing_lines` on a phase with status `ok` or `pre-existing failure`; a duration such as `0.12s` inside a line of `failing_lines`.
  - Check: `test_failure_evidence.py`
  - WP: WP-01

- AC-005 · The fix receives a regression's new failures and a failing phase's lines, in both engines (reproduces bug 2)
  - Scenario: the conformance scenarios named `a regression's new failures are the fix's evidence` (verify phases: `tests` with `status` `regression`, `tail` `["Tests Passed: 40, Failed: 3"]` and `new_failures` `["[-] XMM-Panel.ps1 has UTF-8 BOM, CRLF only and no non-ASCII"]`; suspect `WP-02`) and `a failing acceptance phase gives its lines to the fix` (phases: `acceptance` with `status` `fails`, no `tail`, `failing_lines` `["FAILED acceptance/test_x.py::test_ac_002_total"]`; suspect `WP-02`), each followed by a passing verification.
  - Action: `test_pipeline.run_scenario(<the scenario>)`, and `node .claude/bin/test_workflow.mjs --dump`.
  - Expected: in the fallback engine, the first fix prompt of WP-02 (key `implementer:WP-02 (fix)#1`, the label of `.claude/bin/pipeline.py:415`) contains `[-] XMM-Panel.ps1 has UTF-8 BOM, CRLF only and no non-ASCII` in the first and `FAILED acceptance/test_x.py::test_ac_002_total` in the second, and does not contain `Tests Passed: 40`; the native engine's prompts for both scenarios are equal to the fallback's.
  - Must not: the evidence built from `tail` when `new_failures` or `failing_lines` has lines; the two engines differing.
  - Check: `test_failure_evidence.py`
  - WP: WP-02

- AC-006 · `close-stage` reports the zone's denials
  - Scenario: the tests' `Repo` with its default manifest; `.claude/state/gate.json` written by the test as `{"AT": {"denials": 1, "last": []}, "QA": {"denials": 2, "last": []}}` after the stage is opened.
  - Action: `agentic.py open-stage acceptance`, write `gate.json`, `agentic.py close-stage acceptance AT=done`; then `agentic.py open-stage qa`, write `gate.json` again as above, `agentic.py close-stage qa QA=pass`; then `agentic.py open-stage qa`, write `gate.json` as `{}`, `agentic.py close-stage qa QA=pass` (the order of `.claude/bin/test_guardrail.py:241-249`).
  - Expected: the first output contains the line `GATE: AT=1` before `RESULT:`; the second contains `GATE: QA=2`; the third contains no `GATE:`. A wave's line is unchanged: `close-stage 1 WP-01=done WP-02=done` with `{"WP-01": {"denials": 1}}` prints `GATE: WP-01=1 WP-02=0`.
  - Must not: `AT=0` or `QA=0` printed; the line of a wave changed.
  - Check: `test_failure_evidence.py`
  - WP: WP-01

- AC-007 · The run's record keeps the zone's denials, in both engines (bug 3)
  - Scenario: the conformance scenario named `zone gate denials are summed from close-stage`: `close-stage acceptance` answers exit 0 with output `ACCEPTANCE (red): red\nGATE: AT=1\nRESULT: OK`, and `close-stage qa` answers exit 0 with `GATE: QA=2\nRESULT: OK`; QA reports `PASS`.
  - Action: `test_pipeline.run_scenario(<the scenario>)`, and `node .claude/bin/test_workflow.mjs --dump`.
  - Expected: `gate_denials` == `{"AT": 1, "QA": 2}` in the fallback engine and the same in the native engine; the scenario `gate denials are summed from close-stage` still gives `{"WP-01": 1}`.
  - Must not: a zone with 0 in `gate_denials`; the engines differing.
  - Check: `test_failure_evidence.py`
  - WP: WP-02

- AC-008 · Docs and release 2.21.1
  - Scenario: this repository.
  - Action: read `plugin.json`, `upgrade.NOTES`, `docs/how-it-works.md`, `.claude/commands/implement.md`, the test files.
  - Expected: version `2.21.1`; `NOTES["2.21.1"]` is the key right above `"2.21.0"`, with at least one note containing `Describing`, one containing `failing_lines` and one containing `gate_denials`; the guide's line that starts `- **Stop gate:**` contains `AT=1`; the guide contains `failing_lines`; the line of `implement.md` that contains `` `gate_denials` `` also contains `` `AT` `` and `` `QA` ``; `test_acceptance_v221.py` pins `2.21.1`.
  - Must not: `2.21.1` anywhere in `docs/how-it-works.md`.
  - Check: `test_failure_evidence.py`
  - WP: WP-03

### Work packages

#### WP-01 · Headers, failing lines and the GATE line
- Wave 1.
- Files: `.claude/bin/verification.py`, `.claude/bin/stage.py`, `.claude/bin/test_failure_lines.py`.
- Implements: `console_lines`, `failing_lines` in `verify`, the zones in `close_stage`'s `GATE:` line (sections 5 and 6).
- ACs: AC-001, AC-002, AC-003, AC-004, AC-006.
- **Patterns to mirror:** `.claude/bin/verification.py:211-229` (`failure_lines`, `scan_lines`: their style and docstrings); `.claude/bin/verification.py:362-372` (the loop that pops `_scan`); `.claude/bin/stage.py:268-271` (the GATE line); `.claude/bin/test_runner_reports.py:207-230` (how a console is scripted and `verify` read).
- **Gotchas:**
  - Header check first: a line matching `HEADER_LINE_RE` is handled as a header even when `FAILURE_LINE_RE` also matches it (`Describing AC-603 failure handling`).
  - A `[-]` line with a trailing duration still matches `FAILURE_LINE_RE`; the duration is stripped later by `normal_failure`, not by `console_lines`.
  - Lines that are neither a header nor a passing test (`Tests completed in 1s`, an error's stack trace) are kept as today.
  - The baseline reads `scan_lines` too: a passing header whose words matched `FAILURE_LINE_RE` was in an older baseline's `failures` and is no longer produced. That only removes lines from the current side, so it cannot create a regression.
  - The GATE line of a stage that closes both a zone and packages is not a case the engines produce; the rule of section 6 still orders it.
  - `test_guardrail.py:249` asserts no `GATE:` for `close-stage qa QA=pass` with no denial: it stays green only with "above 0".
  - `test_failure_evidence.py`'s `ReleaseTests` (AC-008) is red until WP-03: expected in wave 1. So is `test_lean.py`'s budget check, if the code exceeds it.
- **Exact imports and APIs:** `failure_lines`, `normal_failure` already in `verification.py`; `gate_denials` already used in `close_stage`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_failure_lines.py"`; `python3 -m unittest discover -s .claude/bin -p "test_runner_reports.py"`; `python3 -m unittest discover -s .claude/bin -p "test_guardrail.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · The engines read the failing lines and the zone's denials
- Wave 1 (it consumes WP-01's output by signature: the keys of section 5 and the GATE line; its scenarios declare that output, they do not run `verify`).
- Files: `.claude/bin/pipeline.py`, `.claude/workflows/agentic-implement.js`, `.claude/bin/conformance.json`, `.claude/bin/test_pipeline.py`.
- Implements: section 6's engine contracts; the three scenarios named in AC-005 and AC-007.
- ACs: AC-005, AC-007.
- **Patterns to mirror:** `.claude/bin/pipeline.py:280-293` and `.claude/workflows/agentic-implement.js:348-356` (the evidence); `.claude/bin/pipeline.py:470-478` and `.claude/workflows/agentic-implement.js:470-471` (the sum to turn into the helper); `.claude/bin/test_pipeline.py:239-249` (EngineTests: how a scenario's end is asserted).
- **Gotchas:**
  - Use `close_seq` / `closeSeq` at wave 0's close and at both QA closes, replacing `seq` on the same line: no line may be added to `runAfterPlan` or `Pipeline.judge` (section 7).
  - `seq` can return null when the gatekeeper is lost, and `pipeline.py:368` already reads `close["output"]` without a check: the helpers must not repeat that (a null result adds nothing).
  - The scenarios are compared by `ConformanceTests` on `prompts`, `gate_denials` and the rest: write each scenario once in `conformance.json`, never per engine. Name them exactly as AC-005 and AC-007 say: the acceptance tests find them by name.
  - `new_failures` or `failing_lines` may be missing or `[]`; only a non-empty list replaces `tail`.
  - `agentic-implement.js` must stay within 861 lines and 64 long lines: the new evidence expression at `agentic-implement.js:351` is split over lines of at most 120 characters; line 730 goes over 120 once `seq` becomes `closeSeq`, paid for by line 471 (over 120 today), which the helper call replaces; the helpers' own definition lines stay at 120 or fewer. `pipeline.py` within 800 lines.
  - `test_pipeline.py`'s `EngineTests` gains the assertions of AC-005 and AC-007 for the fallback engine; `test_workflow.mjs` needs no change (it runs every scenario by name).
- **Exact imports and APIs:** none new.
- **WP validation:** `node .claude/bin/test_workflow.mjs`; `python3 -m unittest discover -s .claude/bin -p "test_pipeline.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-03 · Docs, notes and release 2.21.1
- Wave 2 (the budget is measured after the code).
- Files: `docs/how-it-works.md`, `.claude/commands/implement.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_acceptance_v221.py`.
- ACs: AC-008.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-161`; `.claude/bin/test_quality_limits.py:158-170` (a fix release's tests: no version pin, the key right above the release it fixes); `docs/how-it-works.md:389`, `docs/how-it-works.md:391`; `.claude/commands/implement.md:71`.
- **Gotchas:**
  - `test_acceptance_v221.py`: change only `"2.21.0"` to `"2.21.1"` in its `plugin["version"]` assertion; its other checks stay.
  - `implement.md`'s line says how to read a zone's count: an `AT` or `QA` with denials means the test-author or QA was held to the quality limits of its own files.
  - `flow-budget.json`: raise only what is exceeded, with its why.
  - `implement.md` is pinned by `test_quality_limits.py:150-155` (exactly one line with `` `zone_suspects` ``) and `test_definitions.py:231-235` (`` `gate_denials` ``): extend line 71, add no line mentioning `zone_suspects`.
  - `.claude/flow-history.json` is regenerated by the maintainer as the last commit, not by this package.
- **WP validation:** the five commands of section 3 and `python3 -m unittest discover -s acceptance`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)", "Bash(python3 .claude/bin/agentic.py quality)"],
  "acceptance": {"files": [".claude/bin/test_failure_evidence.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_failure_evidence.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/verification.py", ".claude/bin/stage.py", ".claude/bin/test_failure_lines.py"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-006"], "mirror": [".claude/bin/verification.py:211-229", ".claude/bin/verification.py:362-372", ".claude/bin/stage.py:268-271", ".claude/bin/test_runner_reports.py:207-230"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/pipeline.py", ".claude/workflows/agentic-implement.js", ".claude/bin/conformance.json", ".claude/bin/test_pipeline.py"],
     "acs": ["AC-005", "AC-007"], "mirror": [".claude/bin/pipeline.py:280-293", ".claude/workflows/agentic-implement.js:348-356", ".claude/bin/pipeline.py:470-478", ".claude/bin/test_pipeline.py:239-249"]},
    {"id": "WP-03", "wave": 2, "depends_on": ["WP-01", "WP-02"], "files": ["docs/how-it-works.md", ".claude/commands/implement.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_acceptance_v221.py"],
     "acs": ["AC-008"], "mirror": [".claude/bin/upgrade.py:156-161", ".claude/bin/test_quality_limits.py:158-170", "docs/how-it-works.md:389", ".claude/commands/implement.md:71"]}
  ]
}
```

## 9. Test strategy

- **Acceptance** (`test_failure_evidence.py`, written first and red): AC-001 to AC-004 and AC-006 run `agentic.py` (`verify`, `hook`, `close-stage`) in temporary repos with scripted consoles; AC-005 and AC-007 run the named conformance scenarios through `test_pipeline.run_scenario` and compare with `test_workflow.mjs --dump` (skipped without `node`, as `ConformanceTests` is); AC-008 reads files. Nothing is spent.
- **Unit:** `test_failure_lines.py` covers `console_lines` directly (no header, a header with no test under it, nested `Context`, two failures under one header kept once, a header at the end of the output, a summary line, a `[-]` line that contains `Errors: 0`, a `[-]` at the `Describing` level after a `Context`) and the GATE line's ordering.
- **Teeth:** each behaviour is broken once by hand (headers kept as today; `failing_lines` not set on the acceptance phase; the evidence from `tail`; the zone sum skipped in one engine) and an acceptance test must fail.
- **By hand, before the pull request:** the reproduction of this session (three packages suspected today) run again, giving `{}`; `acceptance/`, `qa/`, the installed-project job, and `agentic.py flow-history` as the last commit with its `--check`.

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| A Pester header is kept only when a failure follows it in its block | Drop every header; or attribute criteria only from failing lines | Dropping every header loses the criterion of a real failure whose `It` name has none (the run's `FeatureFlagList AC-001` case). Reading criteria only from failing lines would break runners whose detail lines carry the name (Jest-style blocks, pytest's tracebacks). The narrow rule changes only what a header of passing tests contributes |
| The headers are recognised by `Describing`/`Context` at the line's start | A general "block header" detector | Those are the lines the run showed; other runners mark a block differently and were not reported. Section 11 |
| `failing_lines` on every blocking phase | `new_failures` only (the request's first wording) | The user chose to extend it: the acceptance phase has no `tail` and the run's BLOCKED package had no lines at all |
| The key is `failing_lines` | `failures` | The baseline already uses `failures` for the full list it compares; one name, one meaning |
| Evidence: `new_failures`, else `failing_lines`, else `tail` | Concatenate them | A regression's new lines are the ones that say who broke something; the old ones belong to nobody (the rule `verify` already applies to suspects) |
| Zones in the `GATE:` line and in `gate_denials`, reversing design 0003 (`docs/architecture/0003-stop-gate-statuses.md:140`, `:197`: judge ids never listed) and design 0029 (`docs/architecture/0029-zone-stop-gate.md:257`: zones left out to avoid an engine change) | Keep both decisions | 0029 left them out only to avoid touching the engines; the real run showed nobody can tell whether the zone gate acted. 0003's reason (judges have no acceptance gate) ended when 0029 gave `AT` and `QA` one. `REVIEW` and `DOCS` stay unlisted |
| A summary line keeps no header | Treat it as any failing line | `Tests Passed: 2, Failed: 1` contains `Failed`: it would keep the last block's header whatever passed (found by the plan review) |
| `close_seq` replaces `seq` at the closes | Add a call after each close | Two functions are at their recorded size allowance |
| Zone counts in the GATE line only above 0 | Always print them | A test pins no GATE line for a QA stage without denials, and an engine reading `QA=0` would add nothing |
| The engines read the zone's denials into `gate_denials` | Leave the line only in `stages[].check` | QA's close output is not kept anywhere in the result; without the engine change QA's denials stay invisible. Chosen with the user ("record the denials of AT and QA") |
| Contracts first: WP-01 and WP-02 in the same wave | WP-02 after WP-01 | The engines only read declared outputs in their scenarios; nothing of WP-01 needs to run for WP-02 |
| A new acceptance file, the 2.21.0 file keeps only a bumped pin | Rewrite `test_acceptance_v221.py` | The fix-release pattern since 2.20.1 |
| No change to `own_failure` | Show the failing line under a package's header | Not reported as a defect; the gate's message names the criterion and the agent can run its tests. Section 11 |

## 11. Risks and open questions

- **Pester's exact console is not measured.** The header rule follows Pester 4 and 5's documented `Describing`/`Context` lines and the run's agents' quotes. If a project's Pester prints another header word (a localised build, `Describe` without `-ing`, a custom formatter), its headers are kept as today. The robust path stays the one the flow already has: `reports` with NUnitXml.
- **Other console lines can still carry an AC.** A `Running tests from '…AC-601.Tests.ps1'` line is not a header and is kept. Not seen in the run; not handled.
- **The gate's message for a real failure under a header** shows the header (the line with the marker), not the `[-]` line under it (`own_failure`, `.claude/bin/stage.py:310-323`). Unchanged by this design.
- **A header after a regression.** A regression's scan keeps only its new failing lines (`.claude/bin/verification.py:350`), so a Pester header that names a criterion does not attribute a regression; the package is found only through a file or a criterion in the failing line itself. Unchanged by this design.
- **Blocks end by header, not by indentation.** A `[-]` printed at the `Describing` level after a `Context` is counted inside that `Context` and keeps its header too. Not seen in the run; `test_failure_lines.py` pins the behaviour so a later change is deliberate.
- **The project's own fix** (its `reports`, `FeatureFlagList AC-001` in its 4b, `XMM-Panel.ps1`'s encoding) is the user's, outside the flow.

No question blocks a WP.
