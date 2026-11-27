# Architecture: a QA test that fails after a fix is triaged by QA's own report, and QA tests can pin a line (issue 148; agentic-flow 2.22.4)
Type: fix · Size: standard

## 1. Goal

In a 2.22.2 field run (xmm-test-tool) the verification after a fix cycle failed on `test_d1`, a QA test that reproduces QA defect `D1` (low, `wp: WP-07`). QA had left it red on purpose, as `qa.md` asks. Verification compares failures with a baseline taken before the run, and QA's tests did not exist then, so the failure was a regression. `verification.attribute` maps a failure only through package files and `AC-NNN`, so nobody owned it and the run stopped for a person. The fix that broke it was a Standards fix: it split a line that `test_d1` reads from the source, and `agentic.py pinned` (#145) only looked at acceptance tests.

After this fix, three things change:
1. **QA declares its red tests.** Its report gains `red_tests`: each test it leaves red on purpose, with the defect it reproduces.
2. **The engines triage QA failures.** After a fix, failures that match a declared red test no longer block and are recorded. A failing line that names a defect of QA's last report goes back to that defect's package. Anything else stops as today, with QA's open defects named in the detail.
3. **QA tests can pin a line.** `pinned` also searches QA's zone, so a Standards finding on a line a QA test reads becomes the same `acceptance conflict` item, with the zone named. `qa.md` discourages tests that read the source when the behaviour can be observed.

## 2. Scope

### Included

- `findings.qa_triage(verification, qa)` and its mirror in the workflow.
- Both engines: the triage on a failed verification; `run.qa_known_failures`; the stop's detail.
- QA's schema: optional `red_tests` (pipeline-spec and the workflow).
- `repo_scan.pinned`: QA's zone is searched; each pin carries `zone` (`AT` or `QA`). `split_pinned` and its mirror copy `zone` into `pinned_by`.
- `qa.md`: list `red_tests`; avoid source-text assertions.
- Release 2.22.4.

### Excluded (non-goals)

- A deterministic run of QA's tests when its pass closes (user's choice: QA declares them).
- Giving a failure that names no QA defect to QA (user's choice: stop as today, with a better detail).
- A red test that a fix breaks in a new way: it still counts as known (accepted risk, user's choice).
- `verification.py`: `verify` and `attribute` do not change.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow: `node .claude/bin/test_workflow.mjs`
- The repository's suites CI also runs: `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`
- Quality limits: `python3 .claude/bin/agentic.py quality`

## 4. Repository structure

```
.claude/bin/findings.py                  WP-01  qa_triage, QA_ID_RE; split_pinned copies zone
.claude/bin/pipeline.py                  WP-01  the triage in judge(); qa_known_failures; the stop detail
.claude/workflows/agentic-implement.js   WP-01  the same, with mirrors of qa_triage and of zone in splitPinned; QA_SCHEMA
.claude/workflows/pipeline-spec.json     WP-01  schemas.qa.red_tests
.claude/bin/conformance.json             WP-01  three scenarios (Annex A)
.claude/bin/test_workflow.mjs            WP-01  the pinned_by.zone test; qa_known_failures in the --dump summary
.claude/bin/test_qa_triage.py            WP-01  new: unit cases
.claude/bin/repo_scan.py                 WP-02  pin_tests over AT and QA; zone in each pin
.claude/bin/test_pinned.py               WP-02  a QA-zone case
.claude/bin/test_pinned_conflict.py      WP-02  its expected pin gains "zone": "AT" (lines 148-168)
.claude/agents/qa.md                     WP-02  red_tests; no source-text assertions
docs/how-it-works.md                     WP-03
.claude/commands/implement.md            WP-03  qa_known_failures; pinned_by.zone
.claude-plugin/plugin.json               WP-03  2.22.4
.claude/bin/upgrade.py                   WP-03  NOTES["2.22.4"]
.claude/flow-budget.json                 WP-03
.claude/bin/test_acceptance_v222.py      WP-03  its version pin (line 229): 2.22.4
.claude/quality-baseline.json            by hand (the person executing the plan): agentic-implement.js's stored lines, after WP-01
.claude/bin/test_qa_baseline.py          AT
.claude/flow-history.json                by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| `verify` marks a phase `regression` or `fails`, keeps up to `MAX_FAILING_LINES` (10) failing lines and `new_failures`, and attributes them by file and `AC-NNN`; `zone_suspects` only for the quality phase | `.claude/bin/verification.py:40`, `.claude/bin/verification.py:356-407` | Unchanged. The triage reads its output | read |
| The native engine's failed-verification branch, `verificationDefects`, `failingLines` | `.claude/workflows/agentic-implement.js:893-918`, `.claude/workflows/agentic-implement.js:395-406` | The triage goes at the start of the branch | read |
| The fallback engine's same branch | `.claude/bin/pipeline.py:623-645`, `.claude/bin/pipeline.py:163-187` | Same change | read |
| `WAVE_TAIL = ['verify', 'open-stage review', 'callers']` runs in one gate call that stops at the first failing step: when `verify` fails, the review stage is not opened | `.claude/workflows/agentic-implement.js:294` | When the triage clears every blocking phase, the engine opens the review itself with `open-stage review` and `callers` | read |
| `run.qa` holds QA's last report (`null` before QA) in both engines | `.claude/workflows/agentic-implement.js:309`, `.claude/bin/pipeline.py:53-56` | The triage applies only when it is a dict | read |
| QA's schema, both copies (the workflow's must equal pipeline-spec's: `test_workflow.mjs` checks it) | `.claude/workflows/agentic-implement.js:74-84`, `.claude/workflows/pipeline-spec.json:527-670` | Add `red_tests` to both, optional | read |
| QA already names a defect's test with its ID (`test_d1_...`) and leaves medium and low ones red | `.claude/agents/qa.md:38`, `.claude/agents/qa.md:69` | `red_tests` lists exactly those | read |
| `pin_tests` reads only the acceptance zone; `pins_for` and `find_pin` | `.claude/bin/repo_scan.py:347-380` | Add QA's zone; tag each test with its zone | read |
| `qa_entity(manifest)["files"]`, `qa/` by default | `.claude/bin/core.py:244-246` | Import it in `repo_scan.py` (`.claude/bin/repo_scan.py:13-16`) | read |
| `split_pinned` builds `pinned_by` from a pin; `_usable_pin` | `.claude/bin/findings.py:279-300`, `.claude/workflows/agentic-implement.js:270-282` | Copy `zone` when it is `"AT"` or `"QA"` | read |
| A conformance scenario with a list of `verify` answers (`null` is the default green) | `.claude/bin/conformance.json:50-78` | Annex A uses the same keys | read |
| The workflow is at 963 lines with an allowance of 967 (stored 937, growth 30) and 64 long lines | `.claude/quality-baseline.json`, `.claude/bin/quality.py:232-235` | Its stored `lines` is raised by hand in WP-01's commit, as designs 0033 and 0035 needed | read |
| `test_pinned_conflict.py` compares `pinned`'s whole answer with a pin that has no `zone` | `.claude/bin/test_pinned_conflict.py:145-168` | WP-02 adds `"zone": "AT"` to its expected pin | read |
| `Pipeline.judge` (stored 73 lines) and `runAfterPlan` (stored 128) are at their stored size; functions get no growth allowance | `.claude/quality-baseline.json`, `.claude/bin/quality.py:225-229` | The failed-verification branch moves into a new helper in each engine; neither function may grow | read |
| The `--dump` summary of the native engine | `.claude/bin/test_workflow.mjs:576-589` | WP-01 adds `qa_known_failures` | read |
| Release notes newest first, `2.22.3` at the top | `.claude/bin/upgrade.py:156-162` | `2.22.4` right before it | read |

What must NOT change: a verification with no QA report, or whose failures match no declared red test and name no QA defect, takes today's path (defects from `suspects`, or the stop) with today's gate calls; `pinned`'s answer for acceptance pins (only `zone` is added).

## 5. Data model

```python
# findings.py
QA_ID_RE_TEMPLATE = r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"  # a defect id as a whole word, ASCII case folded
TRIAGED = ("quality", "acceptance")  # phases never triaged: their failures are never QA's tests
```

QA's report, new optional field:

```json
"red_tests": [{"test": "<the test's name as the runner prints it>", "defect": "D1"}]
```

The QA schema's new property, in both copies: `red_tests: { type: 'array', items: obj(['test'], { test: { type: 'string' }, defect: { type: 'string' } }) }` (written inline: `TEXT` is declared after `QA_SCHEMA`, `.claude/workflows/agentic-implement.js:85`) (pipeline-spec: the same as JSON). `test` is required in an item, `defect` is not; `red_tests` is not in the schema's `required`.

`run.qa_known_failures`: a list of `{"fix_cycle": <n>, "phase": "<name>", "line": "<failing line>"}`, each `(phase, line)` once. A pin gains `"zone": "AT" | "QA"`; `pinned_by` gains `zone` when the pin had it.

## 6. Contracts between modules

### C1 · `findings.qa_triage(verification, qa) -> dict` (WP-01; mirrored as `qaTriage`)

- Returns `{"known": [{"phase", "line"}], "cleared": [phase names], "all_cleared": bool, "defects": [defect], "open": [{"id", "wp"}]}`. Pure; never raises.
- `all_cleared` is true only when `qa` is a dict, `verification["blocking"]` is a non-empty list, and every name in it is in `cleared`. A failed verification without a readable `blocking` (no JSON, an old shape) is never cleared.
- `qa` not a dict → every list empty and `all_cleared` false.
- `open`: the defects of `qa["defects"]` with a string `id`, as `{"id", "wp"}`, in order.
- `red`: the strings `t["test"]` of `qa["red_tests"]` entries that are dicts with a non-empty string `test`.
- For each phase of `verification["phases"]` whose `status` is `regression` or `fails` and whose `name` is not in `TRIAGED`:
  - `lines` = `new_failures` when it is a non-empty list, else `failing_lines` when it is a non-empty list, else `[]` (never `tail`: do not reuse `pipeline_parts.failing_lines`, which falls back to it).
  - Each line containing (as a substring) one of `red` is **known**.
  - The phase is **cleared** when `lines` is non-empty, every line is known, and `len(lines) < MAX_FAILING_LINES` (10). A full list may hide more failures, so it is never cleared.
  - Each line that is not known and matches `QA_ID_RE_TEMPLATE % re.escape(id)` with `re.IGNORECASE | re.ASCII` (JS: the `i` flag, the id escaped with `id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')`) for an `open` defect whose `wp` is a string gives one defect per such `(wp, id)`, once each, in order: `{"source": "verification", "severity": "high", "wp": <wp>, "file": "", "problem": "verification fails (<phase>) on QA's test of <id>", "evidence": "<phase>: <the matching lines joined by \\n>"[:1500]}`.
- `MAX_FAILING_LINES` is a literal `10` in `findings.py` (`QA_TRIAGE_MAX_LINES = 10`, commented: as `verification.MAX_FAILING_LINES`).

### C2 · The engines' failed-verification branch (WP-01)

The whole branch moves into a new helper, `Pipeline.failed_verification(v)` in `pipeline.py` and `failedVerification(v)` in the workflow, returning one of `{"post": [...]}` (go on to the review), `{"defects": [...]}` (a fix cycle) or `{"stopped": <result>}`. `judge` and `runAfterPlan` call it and shrink or stay the same size: `quality` holds functions to their stored length. The helper, after recording `verification_failures`:

1. `t = qaTriage(run.verification, run.qa)`. Append each `known` line to `run.qa_known_failures` as `{fix_cycle: run.fix_cycles, phase, line}`, unless that `(phase, line)` is there.
2. When `t.all_cleared`: one gate call `seq(['open-stage review', 'callers'], 'open-stage review')`; when its first step is not ok, stop `('verification', 'the review stage could not be opened')`; otherwise `post = [v, ...its steps]` and go on to the review exactly as a passing verification does.
3. Otherwise `defects` = the `suspects` defects, as today, but from a copy of `verification` whose `suspects` drop the phases in `cleared` (a suspect left with no phase is dropped), plus `t.defects` for packages (`isWp`) not already among them.
4. No defects: stop `('verification', DETAIL)`, where DETAIL is today's sentence plus, when `t.open` is not empty, `"; QA's open defects: " + "D1 (WP-07), D2 (WP-02)"` (each `id (wp)`, joined by `, `).
5. `run.qa_known_failures` starts as `[]` in both engines' `run`.
6. Who does what: the helper returns `{"defects"}` and the caller (`judge` / the `while` loop of `runAfterPlan`) runs `split_by_limit`, sets `pending`, returns the run when nothing is eligible, and runs the fix cycle, exactly as today. On `{"post"}` the caller replaces `post` and falls through to the review in the same iteration: it must not `continue`, which would read the same failed `verify` again and loop.
7. `run.verification` keeps the failed verification after a clear; `run.qa_known_failures` says why the run went on.

### C3 · `repo_scan.pinned` and `split_pinned` (WP-02 and WP-01)

- `pin_tests(manifest)` returns `[(path, lines, zone)]` over the files of the acceptance zone (`zone "AT"`) and of QA's zone (`qa_entity(manifest)["files"]`, `zone "QA"`), in path order, with the same reading rules as today. A file in both zones counts once, as `AT`.
- `find_pin(path, line, source, tests)` keeps its signature and its 2-tuples `(path, lines)`; `pins_for` passes it `[(p, ls) ...]` as today and adds `"zone"` to the pin it returns, from the zone of the test file the pin names.
- `split_pinned` (and `splitPinned`): `pinned_by` gains `"zone": pin["zone"]` when it is `"AT"` or `"QA"`; otherwise `pinned_by` is as today.

## 7. Conventions

- English for code, comments and docs; the repository's existing style.
- Standard library only; `findings.py` keeps no flow import.
- No line over 120 characters; functions ≤ 60 lines; nesting ≤ 4 (`agentic.py quality`).
- A comment above each JS mirror names the Python function.
- Docs and notes name no flow version outside `upgrade.NOTES` and `plugin.json`.
- Commits: `type: summary` in lowercase, ending with the session's attribution lines.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · A QA test QA left red on purpose does not stop the verification after a fix (the bug)
  - Scenario: Annex A scenario "a QA test left red on purpose does not block the verification after a fix".
  - Action: the fallback engine (`test_pipeline.run_scenario`, and a `full_result` helper as in `.claude/bin/test_pinned_conflict.py:40-45`) and the native one (`node .claude/bin/test_workflow.mjs --dump`).
  - Expected: `failed_stage` `None`, `result` `OK`, `fix_cycles` 1; the gates contain `open-stage review` twice (the first review and the one after the fix); `qa_known_failures` is `[{"fix_cycle": 1, "phase": "tests", "line": "qa/test_x.py::test_d1_flags_errors_only FAILED"}]` in the fallback's full result and in the native `--dump` summary. Both engines agree on result, failed_stage, detail, fix_cycles, pending, gates, gate_calls, agents and prompts.
  - Must not: the detail `a verification phase fails and no work package owns the failure`.
  - Check: `test_qa_baseline.py`, AC-001 tests.
  - WP: WP-01
- AC-002 · A failing QA test that names an open defect goes to that defect's package
  - Scenario: Annex A scenario "a failing QA test that names an open defect goes to its package".
  - Action: both engines.
  - Expected: `fix_cycles` 2; the agents include `implementer:WP-02 (fix)`; `result` `OK`; both engines agree.
  - Must not: a stop at `verification`.
  - Check: `test_qa_baseline.py`, AC-002 tests.
  - WP: WP-01
- AC-003 · An unowned failure stops as today, naming QA's open defects
  - Scenario: Annex A scenario "an unowned failure after QA names QA's open defects".
  - Action: both engines.
  - Expected: `failed_stage` `verification`; `detail` is `a verification phase fails and no work package owns the failure (see verification); QA's open defects: D1 (WP-02)`; both engines agree.
  - Must not: a fix call after the first fix cycle.
  - Check: `test_qa_baseline.py`, AC-003 tests.
  - WP: WP-01
- AC-004 · The triage's rules
  - Scenario: unit calls of `findings.qa_triage`.
  - Action: (a) `qa = None`; (b) a `tests` phase `regression` with `new_failures` `["x test_d1_a", "y"]` and `red_tests` `[{"test": "test_d1_a"}]`; (c) the same with every line known; (d) ten known lines; (e) a `quality` phase whose lines contain a red test; (f) a line `"test_d10_z"` with open defects `D1` (WP-01) and `D10` (WP-02); (g) a line naming `d1` for an open defect without a string `wp`; (h) case (c) with `blocking` missing; (i) case (c) with `blocking` `["tests", "lint"]`.
  - Expected: (a) all four lists empty; (b) `known` holds `x test_d1_a`, `cleared` `[]`; (c) `cleared` `["tests"]`; (d) `cleared` `[]`; (e) nothing known or cleared; (f) one defect, on `WP-02`; (g) no defect; (c) `all_cleared` true; (h) and (i) `all_cleared` false.
  - Must not: an exception on `None`, strings or lists where dicts are expected.
  - Check: `test_qa_baseline.py`, AC-004 tests.
  - WP: WP-01
- AC-005 · A QA test pins a line, with its zone
  - Scenario: a temporary repo (`test_agentic.Repo`) with `src/w.ps1` line 2 `  $re = [regex]::new('==(TVM)==;')`, `qa/t.Tests.ps1` with line 1 `$src = Get-Content "$PSScriptRoot/../src/w.ps1"` and line 3 `$src | Should -Match '\[regex\]::new\(''==\(TVM\)==;'`, `src/v.ps1` line 2 `  $n.ShowBalloonTip(10000, 'a')`, and `acceptance/a.Tests.ps1` with line 1 `$s = Get-Content "$PSScriptRoot/../src/v.ps1"` and line 2 `$s | Should -Match 'ShowBalloonTip\(10000'`.
  - Action: `agentic.py pinned src/w.ps1:2 src/v.ps1:2`.
  - Expected: two pins: `src/w.ps1:2` with `"test": "qa/t.Tests.ps1"`, `"test_line": 3`, `"zone": "QA"`; `src/v.ps1:2` with `"test": "acceptance/a.Tests.ps1"`, `"test_line": 2`, `"zone": "AT"`.
  - Must not: the QA file ignored.
  - Check: `test_qa_baseline.py`, AC-005 tests.
  - WP: WP-02
- AC-006 · The conflict item names the zone
  - Scenario: `findings.split_pinned` with an answer pin carrying `"zone": "QA"`, and one carrying `"zone": "X"`.
  - Expected: `pinned_by["zone"]` is `"QA"` for the first; the second's `pinned_by` has no `zone`.
  - Must not: `zone` copied from a non-string or unknown value.
  - Check: `test_qa_baseline.py`, AC-006 test.
  - WP: WP-01
- AC-007 · QA is told
  - Scenario: the repository.
  - Action: read `.claude/agents/qa.md`, `pipeline-spec.json`.
  - Expected: `qa.md` has a line containing `red_tests` and one containing both `source text` and `section 6`; `schemas.qa.properties.red_tests` exists and is not in `schemas.qa.required`.
  - Must not: `red_tests` required.
  - Check: `test_qa_baseline.py`, AC-007 test.
  - WP: WP-02 (qa.md), WP-01 (schema)
- AC-008 · Release 2.22.4
  - Scenario: the repository.
  - Action: read the release files; run `agentic.py quality`.
  - Expected: version ≥ `(2, 22, 4)`; `NOTES["2.22.4"]` right before `"2.22.3"`, some note containing `red_tests`; `implement.md` has exactly one line containing `` `qa_known_failures` ``; `how-it-works.md` contains `red_tests` and not `2.22.4`; `quality` exits 0.
  - Must not: a line of `test_acceptance_v222.py` with both `plugin[` and `"2.22.3"`.
  - Check: `test_qa_baseline.py`, AC-008 test (flow repo only).
  - WP: WP-03

### Work packages

#### WP-01 · Both engines triage a failed verification with QA's report
- Wave 1.
- Files: `.claude/bin/findings.py`, `.claude/bin/pipeline.py`, `.claude/workflows/agentic-implement.js`, `.claude/workflows/pipeline-spec.json`, `.claude/bin/conformance.json`, `.claude/bin/test_workflow.mjs`, `.claude/bin/test_qa_triage.py`.
- Implements C1, C2, and C3's `split_pinned` part. Consumes C3's pin shape by signature.
- ACs: AC-001, AC-002, AC-003, AC-004, AC-006, AC-007 (schema).
- **Patterns to mirror:** `.claude/bin/findings.py:279-300` (pure helpers); `.claude/workflows/agentic-implement.js:893-918` and `.claude/bin/pipeline.py:623-645` (the branch you change); `.claude/bin/conformance.json:50-78` (a scenario with `verify` answers).
- **Gotchas:**
  - Both engines in one package: `test_pipeline.ConformanceTests` compares their prompts and gates.
  - After clearing, `post` must look like a passing `WAVE_TAIL`: `[verify, open-stage review, callers]`. The review reads `post[1]` (opened) and `post[2]` (callers).
  - The schema in `agentic-implement.js` must equal `pipeline-spec.json`'s (`test_workflow.mjs` asserts it).
  - The workflow grows past its allowance (963 of 967): the person executing the plan raises its stored `lines` in `.claude/quality-baseline.json` after this package, saying why; never `long_lines` and never a function's entry.
  - `judge` and `runAfterPlan` may not grow: move the branch into `failed_verification` / `failedVerification`.
  - Append the Annex A scenarios to `scenarios` and write the file with `json.dumps(data, indent=2)` plus a final newline (its current format).
  - Known red until WP-02 and WP-03: AC-005, AC-007's `qa.md` part, AC-008, `test_lean` and `test_lean_hook`'s budget checks.
- **Exact imports and APIs:** in `pipeline.py`, add `qa_triage` to the `from findings import (...)` block. In the workflow: `seq`, `step`, `ok`, `isWp`, `stop`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p test_qa_triage.py`; `node .claude/bin/test_workflow.mjs`; `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · QA's zone can pin a line, and QA is told
- Wave 1.
- Files: `.claude/bin/repo_scan.py`, `.claude/bin/test_pinned.py`, `.claude/bin/test_pinned_conflict.py`, `.claude/agents/qa.md`.
- Implements C3's `pinned` part.
- ACs: AC-005, AC-007 (qa.md).
- **Patterns to mirror:** `.claude/bin/repo_scan.py:347-380`; `.claude/agents/qa.md:36-38`.
- **What to write in `qa.md`:** in Process step 4, "Do not assert on the source text of production code when the behaviour can be observed through section 6: a Standards fix that reformats the line breaks such a test." In the Report section, after `plan`, a bullet: "`red_tests`: each test you leave red on purpose, as `{"test": <its name as the runner prints it>, "defect": <the defect's id>}`; after a fix the flow does not count those as new failures. In a re-check, list again every red test that is still red."
- **Gotchas:** `qa.md` must keep the words `the rules printed in your prompt` (`.claude/bin/test_definitions.py:646`, `.claude/bin/test_qa_recheck.py:171`). Known red until WP-01 and WP-03: AC-001..004, AC-006, AC-007's schema part, AC-008 and `test_lean`'s budget. `qa_entity` must be added to the `from core import (...)` block of `repo_scan.py`. A file in both zones is tagged `AT`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p test_pinned.py`; `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-03 · Documentation and release 2.22.4
- Wave 2.
- Files: `docs/how-it-works.md`, `.claude/commands/implement.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_acceptance_v222.py`.
- Depends on WP-01 and WP-02 by implementation.
- ACs: AC-008.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-162`; `.claude/commands/implement.md:59`.
- **What to write:** `implement.md`'s QA bullet adds one sentence on `qa_known_failures` (QA tests left red on purpose that a later verification saw, not counted as new failures); its acceptance-conflict bullet mentions `pinned_by.zone`. `how-it-works.md`: a paragraph on `red_tests`, the triage and the QA zone in `pinned`. One note in `NOTES["2.22.4"]` naming issue 148 and `red_tests`. The budget, measured with `test_lean.code_lines(Path('.'))` and `test_lean.prompt_bytes(Path('.'))`, with a `why`.
- **Gotchas:** `implement.md` must keep exactly one line containing `` `acceptance conflict` `` (`.claude/bin/test_pinned_conflict.py:203`): add the zone to that line, not a new one.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 -m unittest discover -s acceptance`; `python3 -m unittest discover -s qa`; `python3 .claude/bin/agentic.py quality`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)", "Bash(python3 .claude/bin/agentic.py quality)"],
  "acceptance": {"files": [".claude/bin/test_qa_baseline.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_qa_baseline.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/findings.py", ".claude/bin/pipeline.py", ".claude/workflows/agentic-implement.js", ".claude/workflows/pipeline-spec.json", ".claude/bin/conformance.json", ".claude/bin/test_workflow.mjs", ".claude/bin/test_qa_triage.py"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-006", "AC-007"], "mirror": [".claude/bin/findings.py:279-300", ".claude/workflows/agentic-implement.js:893-918", ".claude/bin/pipeline.py:623-645", ".claude/bin/conformance.json:50-78"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/repo_scan.py", ".claude/bin/test_pinned.py", ".claude/bin/test_pinned_conflict.py", ".claude/agents/qa.md"],
     "acs": ["AC-005", "AC-007"], "mirror": [".claude/bin/repo_scan.py:347-380", ".claude/agents/qa.md:36-38"]},
    {"id": "WP-03", "wave": 2, "depends_on": ["WP-01", "WP-02"], "files": ["docs/how-it-works.md", ".claude/commands/implement.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_acceptance_v222.py"],
     "acs": ["AC-008"], "mirror": [".claude/bin/upgrade.py:156-162", ".claude/commands/implement.md:59"]}
  ]
}
```

## 9. Test strategy

- **Unit:** WP-01 in `test_qa_triage.py` (C1's rules); WP-02 in `test_pinned.py` (a QA-zone pin). The JS mirrors are held equal by the conformance scenarios.
- **Acceptance (AT, wave 0):** `.claude/bin/test_qa_baseline.py`, red today: AC-001's run stops at verification; `qa_triage` does not exist; pins carry no zone. Engine criteria use the Annex A scenario names as `test_owner_split_v2.py` does. AC-008 is skipped outside the flow repo. The AT must not write `"2.21.2"`, `"2.22.0"`, `"2.22.1"`, `"2.22.2"` or `"2.22.3"` on a line containing `version`.
- **QA:** a red test name that is a substring of another; QA reports without `red_tests`; a re-check report that drops a red test.
- Executed by hand (`"maintainer": true`).

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| QA declares `red_tests` | Run the suite when QA closes | User's choice: no extra suite run per QA pass. |
| A failure naming no QA defect stops as today, with QA's open defects in the detail | Give it to QA as a zone suspect | User's choice: a name alone does not say a test is QA's. |
| A known red test broken in a new way still counts as known | Compare the failure's text | User's choice (accepted risk); `pinned` over QA's zone prevents the field run's cause. |
| The triage in the engines, from `run.qa` | In `verify` | `verify` never sees QA's report; the engines hold it. |
| A full list of failing lines (10) is never cleared | Clear it | More failures may hide past the cap. |
| `quality` and `acceptance` are never triaged | Triage every phase | Their failures name files or criteria, never QA's tests. |
| Defects from a QA id go to the defect's package even when it is low | Only blocking defects | User's choice (#148's expected behaviour). |
| WP-01 holds both engines | One per engine | Conformance compares them (designs 0033, 0035). |
| Version 2.22.4 | 2.23.0 | A fix. |

## 11. Risks and open questions

- **QA forgetting `red_tests`** gives today's behaviour for its red tests (the stop), now with its open defects named.
- **A re-check that leaves out `red_tests`** replaces `run.qa` whole and brings the stop back; `qa.md` asks QA to list them again.
- **`qa_known_failures` is compared across engines only by AC-001**: `test_pipeline.ConformanceTests` does not list the key. Accepted.
- **The conflict's decision text** says "acceptance test" for a QA-zone pin too; `pinned_by.zone` tells them apart. Accepted.
- **A short or generic red test name** may match other failing lines. Not measured; QA names carry the defect id.
- **The workflow's line allowance** is raised by hand again (WP-01).

## Annex A · Conformance scenarios

WP-01 adds these to `.claude/bin/conformance.json`, at the end of `scenarios`, exactly.

```json
[
  {
    "name": "a QA test left red on purpose does not block the verification after a fix",
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-02", "file": "src/b/x.py", "problem": "STD-PROBLEM", "evidence": "e", "fix": "f",
         "if_skipped": "s", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]}
    ],
    "qa": [
      {"status": "PASS", "plan": ["contracts", "test_d1 stays red on purpose"], "gaps": [],
       "defects": [{"tier": "finish", "id": "D1", "severity": "low", "wp": "WP-02", "kind": "implementation",
                    "section": "6", "repro": "r", "fix": "f", "if_skipped": "s"}],
       "red_tests": [{"test": "test_d1_flags_errors_only", "defect": "D1"}]}
    ],
    "verify": [
      null,
      {"exit_code": 3, "output": {"ok": false, "blocking": ["tests"], "preexisting_failures": [], "suspects": {},
       "zone_suspects": {}, "phases": [{"name": "tests", "passed": false, "status": "regression",
       "failing_lines": ["qa/test_x.py::test_d1_flags_errors_only FAILED"]}]}}
    ]
  },
  {
    "name": "a failing QA test that names an open defect goes to its package",
    "qa": [
      {"status": "FAIL", "plan": ["contracts"], "gaps": [],
       "defects": [{"tier": "floor", "id": "D1", "severity": "high", "wp": "WP-01", "kind": "implementation",
                    "section": "6", "repro": "r", "fix": "f", "if_skipped": "s"},
                   {"tier": "finish", "id": "D2", "severity": "low", "wp": "WP-02", "kind": "implementation",
                    "section": "6", "repro": "r", "fix": "f", "if_skipped": "s"}]},
      {"status": "PASS", "plan": ["contracts"], "gaps": [], "defects": []}
    ],
    "verify": [
      null,
      {"exit_code": 3, "output": {"ok": false, "blocking": ["tests"], "preexisting_failures": [], "suspects": {},
       "zone_suspects": {}, "phases": [{"name": "tests", "passed": false, "status": "regression",
       "failing_lines": ["qa/test_y.py::test_d2_rejects_empty FAILED"]}]}},
      null
    ]
  },
  {
    "name": "an unowned failure after QA names QA's open defects",
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-02", "file": "src/b/x.py", "problem": "STD-PROBLEM", "evidence": "e", "fix": "f",
         "if_skipped": "s", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]}
    ],
    "qa": [
      {"status": "PASS", "plan": ["contracts"], "gaps": [],
       "defects": [{"tier": "finish", "id": "D1", "severity": "low", "wp": "WP-02", "kind": "implementation",
                    "section": "6", "repro": "r", "fix": "f", "if_skipped": "s"}]}
    ],
    "verify": [
      null,
      {"exit_code": 3, "output": {"ok": false, "blocking": ["tests"], "preexisting_failures": [], "suspects": {},
       "zone_suspects": {}, "phases": [{"name": "tests", "passed": false, "status": "regression",
       "failing_lines": ["qa/test_z.py::test_other_check FAILED"]}]}}
    ]
  }
]
```
