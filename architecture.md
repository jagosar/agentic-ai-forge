# Architecture: runner reports and environment errors (agentic-flow 2.15.0)
Type: change · Size: standard

## 1. Goal
A failing test is blamed on the package that owns it, never on a package whose passing tests happen to be printed nearby. The stop gate and the baseline judge the same way. When the manifest names the XML report a test command writes (JUnit, or NUnit 2/3 as Pester writes it), verification, the gate and the baseline read the failing tests from that report, by name. Without a report, the console is still read, but the lines of tests that passed are skipped. A stage that cannot even start because the interpreter crashed gets one retry, recorded as an environment error. PowerShell gets its own rules pack and stack detection. Three prompt gaps found in the field are closed and measured with saved scenarios:
- helpers and test doubles that nothing exercises;
- tests that pin what the plan changes;
- checks the implementer could not run.

Issues 114, 115, 116, 117 and 118, and `docs/roadmap/field-report-2026-11-powershell.md`.

## 2. Scope
### Included
- **`reports` in the manifest (optional).** It maps a verify phase or `acceptance` to the relative path of the XML report its command writes. `validate` checks it. The report files are artefacts, so close-stage never counts them as changes outside ownership.
- **A new module, `.claude/bin/reports.py`.** It reads a JUnit or NUnit (2.x or 3.x) report into the list of failing tests. A missing, stale, oversized or unreadable report gives `None`, and the caller falls back to the console.
- **Verification** (`verify`, `baseline`, the green acceptance check):
  - with a report read, the failure lines are the failing tests, one line each;
  - the baseline compares the failing tests by name;
  - attribution reads only those lines.
  - Without a report, attribution skips the lines that mark a passing test.
- **The stop gate** (`stage.gate_check`): the same report or the same console filter for the acceptance run.
- **Both engines:** one retry of a standalone `open-stage` call, and of the prepare call (`hooks-check + pipeline-plan + briefs`), when the reply is lost or its failing step exited with a code other than 0, 1 and 3 and printed no JSON line (agentic.py's own refusals exit 1 or 3). The retry is recorded in `run.environment_retries`. No other call is retried.
- **Both engines:** an implementer check reported as `passed: false` with a detail starting `not run:` becomes a pending item of type `needs validation`, kind `tests not run`.
- **PowerShell:** `.claude/rules-library/powershell.md` and stack detection (`.ps1`, `.psm1`, `.psd1`). No code-map symbols: adding the extensions to `SYMBOL_RES` would also put PowerShell files under the ratchet, which measures them with a brace heuristic that does not know `#` or `<# #>` comments.
- **Prompts:**
  - test-author: every helper or test double gets a test of its own;
  - test-auditor: flags a helper or double that no test exercises;
  - plan-reviewer: tests that pin a literal or file the plan changes;
  - `/architect`: grep the tests for what the plan changes, list the hits in 4b, and document the `reports` field;
  - implementer: how to report a check that could not run.
- **Two new saved scenarios** for the prompt changes, run old definition against new, 5 runs each, by hand after the implementation.
- **Release 2.15.0:**
  - version, upgrade notes and docs;
  - `test_acceptance_v214.py` retired, its classes moved to `.claude/bin/test_fix_cycles.py`;
  - `reports.py` added to what `install` copies;
  - the fixes already merged in pull request 113 (summary counts, prepare messages, the concurrent-commit warning) ship with this release.

### Excluded (non-goals)
- No TRX, TAP or JSON report formats. No reports for the build, types or lint phases beyond what the same JUnit/NUnit reader can parse.
- No parsing of a runner's console format beyond the passing-line filter (no per-framework console parser).
- No retry of `close-stage`, `verify`, `baseline`, any batched call, or any agent.
- No change to `sync-permissions` for issue 118 (not reproduced). No `BLOCKED` for checks that could not run.
- No git worktree per cycle (field report item 11).
- No new dependency: `xml.etree.ElementTree` from the standard library.

## 3. Stack
Python 3.9+ (the standard library only; CI runs 3.9 on ubuntu-24.04, and 3.12 and 3.14) and Node 20+ for the native workflow's test harness. Commands, as in CI:
- `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- `node .claude/bin/test_workflow.mjs`
- `python3 -m unittest discover -s bench -p "test_*.py"`
- `python3 -m unittest discover -s bench/acceptance`
- `python3 -m unittest discover -s acceptance`
- `python3 -m unittest discover -s qa`
- `python3 .claude/bin/agentic.py quality` (the ratchet: functions ≤60 lines, ≤100 in tests, nesting ≤4, lines ≤120 characters, files ≤800 lines)
- `python3 .claude/bin/agentic.py docs-check`
- `python3 .claude/bin/agentic.py flow-history --check`

Before any of them: `export CLAUDE_PROJECT_DIR=$PWD`.

## 4. Repository structure
```
.claude/bin/reports.py                         WP-01 (new)
.claude/bin/test_reports.py                    WP-01 (new)
.claude/bin/fixtures/reports/                  WP-01 (new: junit-pytest.xml, nunit2-pester.xml, nunit3.xml, broken.xml)
.claude/bin/manifest_check.py                  WP-01
.claude/bin/test_manifest_check.py             WP-01
.claude/bin/installer.py                       WP-01
.claude/bin/verification.py                    WP-02
.claude/bin/stage.py                           WP-02
.claude/bin/test_agentic.py                    WP-02
.claude/bin/test_guardrail.py                  WP-02
.claude/bin/pipeline.py                        WP-03
.claude/workflows/agentic-implement.js         WP-03
.claude/bin/conformance.json                   WP-03
.claude/bin/test_pipeline.py                   WP-03
.claude/bin/test_workflow.mjs                  WP-03
.claude/rules-library/powershell.md            WP-04 (new)
.claude/bin/repo_scan.py                       WP-04
.claude/bin/test_repo_scan.py                  WP-04
.claude/bin/test_definitions.py                WP-04
.claude/agents/test-author.md                  WP-04
.claude/agents/test-auditor.md                 WP-04
.claude/agents/plan-reviewer.md                WP-04
.claude/agents/implementer.md                  WP-04
.claude/commands/architect.md                  WP-04
.claude/commands/implement.md                  WP-04
bench/scenarios/auditor-untested-double/       WP-05 (new)
bench/scenarios/plan-pinned-literal/           WP-05 (new)
docs/how-to/bench.md                           WP-05
.claude-plugin/plugin.json                     WP-06
.claude/bin/upgrade.py                         WP-06
.claude/bin/test_fix_cycles.py                 WP-06 (new: test_acceptance_v214.py's classes)
.claude/bin/test_acceptance_v214.py            WP-06 (deleted)
README.md                                      WP-06
docs/how-to/README.md                          WP-06
docs/how-it-works.md                           WP-06
docs/roadmap/field-report-2026-11-powershell.md WP-06
.claude/bin/test_acceptance_v215.py            AT (new)
.claude/flow-history.json                      regenerated by hand as the PR's last commit (agentic.py flow-history)
```

## 4b. Existing code context
| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| A manifest command runs without a shell; `scan` receives the last 200 output lines; exit 124, 126 and 127 mean it could not run | `.claude/bin/verification.py:39-59` | `run_command(cmd, timeout, scan)` returns `(code, last 8 lines)`; keep its signature | read |
| The acceptance check fills `scan` from the same `run_command`; red or green comes only from the exit code | `.claude/bin/verification.py:61-81` | The report changes what goes into `scan`, never the verdict | read |
| Failure lines: `FAILURE_LINE_RE` (the words fail/error, ✕✗×❌, Pester's `[-]`), with durations, addresses and summary counts normalised (merged in PR 113) | `.claude/bin/verification.py:18-30`, `.claude/bin/verification.py:205-212` | The baseline compares `failure_lines`; a line not seen at baseline is a regression | read |
| Each verify phase records `_scan`, popped before the JSON is printed | `.claude/bin/verification.py:214-228` | `_scan` never reaches the output; new phase keys must be JSON-safe | read |
| `attribute(manifest, lines)` finds owned paths and `AC-NNN` (also `AC_313`, `ac 313`) in the joined lines | `.claude/bin/verification.py:230-247` | It receives lines; this design changes which lines, not the matching | read |
| The baseline saves `failures` only for failing phases; verify compares them, and a baseline without `failures` (an older version) falls back to phase-level comparison | `.claude/bin/verification.py:249-313` | Keep that fall-back; a baseline saved with a report stores the failing tests' lines in the same `failures` key | read |
| The stop gate runs the acceptance command; `own_failure` keeps the lines naming the package's files or the criteria only it owns, or the last 3 lines | `.claude/bin/stage.py:301-340` | The gate fails open on its own errors and never blocks on a command that cannot run | read |
| Stage snapshots hash `git ls-files -co --exclude-standard` minus `.claude/state/` | `.claude/bin/stage.py:35-46` | Report paths must be dropped here, or a run that writes one reads as a change outside ownership | read |
| `ignored(path, patterns)`: a folder pattern ends in `/`, otherwise fnmatch on the path or its name | `.claude/bin/core.py:270-279` | Not for report paths: it matches by file name too; report paths match exactly | read |
| `at_entity` gives the acceptance command; `VERIFY_PHASES = ("build", "types", "lint", "tests")` | `.claude/bin/core.py:73`, `.claude/bin/core.py:232-235` | `reports` keys are `VERIFY_PHASES` plus `acceptance` | read |
| Manifest checks are lists of error strings joined by `validate`; shapes in `shape_errors` | `.claude/bin/manifest_check.py:186-213` | Add `report_errors(manifest)` beside `shape_errors` and call it where `shape_errors` is called (`.claude/bin/manifest_check.py:68`) | read |
| `install` copies an explicit list of files | `.claude/bin/installer.py:18-40` | `reports.py` must be added, or installed projects break on import | read |
| Stack detection: `STACK_SIGNALS` maps a pack to (project files, extensions); a test requires the detectable packs and the library's files to match | `.claude/bin/repo_scan.py:19-30`, `.claude/bin/test_definitions.py:303-325` | Add `"powershell": ((), (".ps1", ".psm1", ".psd1"))` and the pack file together | read |
| Every rules pack: a `paths:` header, a link to `common.md`, ECC's MIT attribution, five sections in order and a verify table | `.claude/bin/test_definitions.py:303-325`, `.claude/rules-library/csharp.md:1-42` | PowerShell has no ECC source: the test accepts either ECC's attribution or the line `<!-- Written for agentic-flow. -->` | read |
| Code-map symbols by extension; the ratchet measures only files with a symbol regex | `.claude/bin/core.py:61-72` | Do not add PowerShell here (see section 2) | read |
| Python engine: `seq` returns `None` on a lost or unusable reply; `step(res, i)`; standalone `open-stage` calls | `.claude/bin/pipeline.py:167-178`, `.claude/bin/pipeline.py:326`, `.claude/bin/pipeline.py:359`, `.claude/bin/pipeline.py:429` | A retrying `seq` replaces exactly these calls and the prepare call (`.claude/bin/pipeline.py:274`) | read |
| JS engine: `seq` never retries; standalone `open-stage` and prepare calls | `.claude/workflows/agentic-implement.js:183-200`, `.claude/workflows/agentic-implement.js:450`, `.claude/workflows/agentic-implement.js:527`, `.claude/workflows/agentic-implement.js:686`, `.claude/workflows/agentic-implement.js:708` | The comment at line 193 changes to say which calls are retried and why | read |
| Concern items are kept across cycles and handed to every review | `.claude/bin/pipeline.py:99-101`, `.claude/bin/pipeline.py:385-392`, `.claude/workflows/agentic-implement.js:278-283`, `.claude/workflows/agentic-implement.js:413` | `tests not run` items go to the same lists, deduplicated with `pending_key` / `pendingKey` | read |
| Conformance: each scenario runs in both engines and the summaries must be equal; `gate_fail` entries force a reply by command prefix | `.claude/bin/test_pipeline.py:29-80`, `.claude/bin/test_pipeline.py:181-205`, `.claude/bin/test_workflow.mjs:490-510` | A `gate_fail` entry gains an optional `times`, and `gate_lost` accepts `{"prefix", "times"}` beside plain strings (section 6); both harnesses implement them | read |
| Saved scenarios: a folder with the agent's files and a scenario JSON naming agent, prompt and expectation; the set test needs ≥8 files | `bench/scenarios/plan-inferred-row/scenario.json`, `bench/scenarios/auditor-wrong-expected/scenario.json`, `bench/test_scenario.py:201-215` | New folders only; no code change in `bench/scenario.py` | read |
| Upgrade notes per version, a list of sentences | `.claude/bin/upgrade.py:156-167` | `"2.15.0"` with one entry per user-visible change | read |
| Pester 3.4 writes NUnit 2.5 XML with `-OutputFile <path> -OutputFormat NUnitXml`: a `test-suite` per `Describe` (its `name` the Describe text), a `test-case` per `It` with `result` (`Success`, `Failure`, `Ignored`…) and `success`; a failure has `failure/message` | not in this repo | The parser reads `result`/`success` and the ancestors' `name`s; the fixture is written from this description | inferred |
| pytest's `--junitxml` writes `testsuite/testcase` with `classname`, `name`, optional `file`, and `failure` or `error` children | not in this repo | Same | inferred |

What must not change: `run_command`'s and `attribute`'s signatures, the green/red verdicts, the baseline file's `phases[].failures` key, the gate's fail-open behaviour, the never-retry rule for every call not named in section 6, and the output of a run whose manifest has no `reports`, apart from the passing-line filter.

## 5. Data model
```python
# reports.py
REPORT_KEYS = VERIFY_PHASES + ("acceptance",)
MAX_REPORT_BYTES = 10_000_000       # a larger file is not read (fall-back to the console)
MAX_MESSAGE = 200                   # characters of a failure message kept
FailedTest = dict  # {"name": str, "file": str | None, "message": str}
# name: JUnit "<classname>::<name>" (or <name> alone); NUnit the ancestors' test-suite names and the case's name,
#       joined with " > ", e.g. "AC-313 panel > keeps the title"; whitespace collapsed.
# file: JUnit "file" attribute if present, else None; NUnit None.
# message: the first line of failure/@message (or the failure/error text), stripped, cut to MAX_MESSAGE.
```
Manifest (optional):
```json
"reports": {"tests": "test-results.xml", "acceptance": ".pester/acceptance.xml"}
```
Run record (both engines): `run["environment_retries"] = [{"label": str, "cmd": str, "exit_code": int | None, "output": str}]`. `output` holds the first 300 characters, and the list is empty when nothing was retried.

Verify and baseline JSON: each phase that has a declared report gains `"report": "read" | "unread"`. The acceptance phase in `verify` output does too.

Pending item for a check that could not run:
```json
{"type": "needs validation", "source": "WP-01", "wp": "WP-01", "file": null, "kind": "tests not run",
 "problem": "<check.command>", "claim": "<check.command>", "fact": "<check.detail>", "how_to_check": "run <check.command>"}
```
`problem` is there for `pending_key` / `pendingKey` (`.claude/bin/pipeline.py:112`, `.claude/workflows/agentic-implement.js:318`), which key on wp, source, file and `problem` or `repro`: without it, two different checks of one package would collapse into one item.

## 6. Contracts between modules
```python
# .claude/bin/reports.py  (WP-01)
def report_path(manifest: dict, key: str) -> str | None
    """The declared report of a verify phase or "acceptance", or None. Never raises on a malformed manifest."""
def report_paths(manifest: dict) -> list[str]
    """Every declared report path (for the stage snapshot). [] when there is none or the field is malformed."""
def clear_report(manifest: dict, key: str) -> None
    """Deletes the declared report before its command runs (missing_ok), so a stale file is never read. It never
    deletes a path that resolves outside ROOT, even in a manifest that was never validated."""
def failed_tests(path: Path) -> list[dict] | None
    """The failing tests of a JUnit or NUnit 2/3 report. [] when it parsed and nothing failed. None when the file is
    missing, larger than MAX_REPORT_BYTES, unreadable, not XML, or neither format."""
def failure_text(tests: list[dict]) -> list[str]
    """One line per failing test: "FAILED <name> [<file>] <message>", without " [<file>]" when file is None and
    without " <message>" when it is empty. Lines pass through verification.FAILURE_LINE_RE."""

# .claude/bin/manifest_check.py  (WP-01)
def report_errors(manifest: dict) -> list[str]
    # 'reports' absent: []. Not an object, a key outside REPORT_KEYS, a value that is not a non-empty string, an
    # absolute path, a path with a ".." part or a backslash, or a path a work package owns: one error each, naming
    # the key, starting "reports:".

# .claude/bin/verification.py  (WP-02)
PASS_LINE_RE  # r"\bPASSED\b|^\s*\[\+\]|[✓✔√]|^\s*--- PASS\b|^ok\s" (case-sensitive): a line that marks a
              # passing test. A line that FAILURE_LINE_RE matches is never dropped, even if it also matches this.
def scan_lines(manifest: dict, key: str, console: list[str]) -> tuple[list[str], str | None]
    """The lines failure comparison and attribution read for one command, and the report state ("read",
    "unread", or None when no report is declared). With the report read: failure_text(failed_tests(...)).
    Otherwise: the console lines without those matching PASS_LINE_RE."""
# The baseline saves each failing phase's report state next to its failures ("report": "read"|"unread"|None).
# verify compares failure by failure only when the saved state equals the current one; when they differ (a report
# read on one side only), it compares phase by phase, as it already does for a baseline without "failures".
# run_phases, baseline, verify and acceptance_check call clear_report before and scan_lines after each command.
# attribute(manifest, lines) and run_command(cmd, timeout, scan) keep their signatures.

# .claude/bin/stage.py  (WP-02)
# tracked_files() drops every path equal to one of report_paths(manifest) (exact match, not ignored(): a report
# named results.xml must not hide every results.xml); a manifest that cannot be loaded drops nothing. gate_check reads scan_lines(manifest, "acceptance", lines) before own_failure.

# .claude/bin/pipeline.py and .claude/workflows/agentic-implement.js  (WP-03)
RETRIED = prepare call ["hooks-check", "pipeline-plan", "briefs"] and a call made of one "open-stage <label>" only
def seq_retry(cmds, label) / const seqRetry = async (cmds, label)
    # Calls seq; if the result is None/null, or its last step has an exit_code other than 0, 1 and 3 and no line of
    # its output parses as a JSON object (agentic.py exits 1 through die() and 3 on a refusal, both deliberate), records {label, cmd: cmds joined with " + ", exit_code, output[:300]} in
    # run.environment_retries and calls seq once more, returning the second result as it is.
def untested_item(wp, check) / const untestedItem = (wp, check)
    # The pending item of section 5 for a check with passed === false and detail matching /^\s*not run:/i.
# The summary compared by conformance (test_pipeline.summarize and its JS twin) gains two keys, filled by both
# engines and compared like the others:
#   "environment_retries": [{"cmd": str, "exit_code": int | None}]   (in order; [] when none)
#   "untested": [{"wp": str, "claim": str, "fact": str}]          (the pending items of kind "tests not run")
# Conformance declarations: a gate_fail entry may carry "times": N (the reply is forced on the first N matching calls
# only; absent means every call), and gate_lost becomes a list of str | {"prefix": str, "times": int} (a bare
# string keeps today's meaning: every matching call is lost).
```

## 7. Conventions
- Python 3.9 is supported: no `X | None` or `list[...]` in runtime annotations (they raise at import on 3.9). Write plain signatures with the types in the docstring, as `.claude/bin` does. This overrides the `X | None` line of the Python rules; section 6 uses the notation only to describe types.
- The repository's style: English, small pure functions, docstrings that state the contract, constants named at module level, no new dependency.
- The ratchet applies to every file you touch: functions of 60 lines or fewer (100 in tests), nesting of 4 or fewer, lines of 120 characters or fewer, files of 800 lines or fewer. `pipeline.py` is at 719 lines and `agentic-implement.js` at 795. Keep the JS under 800: compact rather than add.
- Fixtures write non-ASCII as escapes. Tests never record personal paths (`/home/<user>/`, `/tmp/claude-N`).
- XML is untrusted input: parse with `xml.etree.ElementTree.parse` only after the size check, catch `ET.ParseError` and `OSError`, and never follow a DTD or an external entity. The standard library parser does not fetch them.
- A user-visible message names the file and the field, never a traceback.
- Both engines change together. Every engine behaviour of this design has a conformance scenario.
- The agents' Markdown keeps its sections and order. A prompt line says what to do and why, in one or two sentences.
- Commits are made by the maintainer after approval, with the session's attribution lines. No model names.

## 8. Work packages and acceptance criteria
### Acceptance criteria
- AC-001 · A JUnit report gives its failing tests
  - Scenario: `fixtures/reports/junit-pytest.xml` with three `testcase`s: `test_ac_001_total` passed, `test_ac_002_rounding` with a `failure message="assert 3 == 4"`, and `test_ac_003_empty` with an `error`. All have classname `acceptance.test_cart` and file `acceptance/test_cart.py`.
  - Action: `reports.failed_tests(path)`, then `reports.failure_text(...)`.
  - Expected: two records, in document order. The first is `{"name": "acceptance.test_cart::test_ac_002_rounding", "file": "acceptance/test_cart.py", "message": "assert 3 == 4"}`. The first line of `failure_text` is `FAILED acceptance.test_cart::test_ac_002_rounding [acceptance/test_cart.py] assert 3 == 4`.
  - Must not: a passed or skipped `testcase` among the records.
  - Check: `test_acceptance_v215.py::ReportTests.test_ac_001_*`
  - WP: WP-01
- AC-002 · An NUnit report keeps the Describe it failed in
  - Scenario: `fixtures/reports/nunit2-pester.xml`. A `test-suite name="AC-313 panel"` holds one passing and one failing `test-case`; a `test-suite name="AC-314 launcher"` holds only passing cases. Also `fixtures/reports/nunit3.xml`, with one `test-case result="Failed"`.
  - Action: `failed_tests` on each.
  - Expected: one record per file. The NUnit 2 name contains `AC-313 panel` and the case's name joined by ` > `, and no record contains `AC-314`. The NUnit 3 record has the case's name.
  - Must not: a record for a case whose `result` is `Success`/`Passed`/`Ignored`/`Skipped`, or for a suite.
  - Check: `ReportTests.test_ac_002_*`
  - WP: WP-01
- AC-003 · An unusable report gives None, never an exception
  - Scenario: a missing path; `fixtures/reports/broken.xml` (not well formed); a well-formed XML that is neither format (`<root/>`); a file larger than `MAX_REPORT_BYTES` (sparse temporary file).
  - Action: `failed_tests` on each.
  - Expected: `None` four times. A JUnit report with no failures gives `[]`.
  - Must not: raise, or return `[]` for the unusable cases.
  - Check: `ReportTests.test_ac_003_*`
  - WP: WP-01
- AC-004 · validate checks `reports`
  - Scenario: valid manifests with `reports` set to:
    1. `{"tests": "out/r.xml"}`
    2. `{"lint": "r.xml", "acceptance": "a.xml"}`
    3. `{"unit": "r.xml"}`
    4. `{"tests": "/abs/r.xml"}`
    5. `{"tests": "../r.xml"}`
    6. `{"tests": ""}`
    7. `["r.xml"]`
  - Action: `agentic.py validate` in a temporary project.
  - Expected: 1 and 2 print "Manifest valid". Each of 3 to 7 exits non-zero, with an error line starting `reports:` that names the key or the field.
  - Must not: accept 3 to 7, or reject a manifest without `reports`.
  - Check: `ManifestTests.test_ac_004_*`
  - WP: WP-01
- AC-005 · With a report, verify blames only the package that failed
  - Scenario: a temporary project. WP-01 owns `AC-001` and `src/a.py`; WP-02 owns `AC-002` and `src/b.py`. `verify.tests` runs a script that prints `Describing AC-001 totals`, `[+] adds 3ms`, `Describing AC-002 rounding`, `[-] rounds 5ms` and exits 1, and writes a JUnit report with one failing `testcase` named `test_ac_002_rounds`. `reports.tests` names that report.
  - Action: `agentic.py verify`.
  - Expected: exit 3. The `tests` phase has `"report": "read"`, and `suspects` has the single key `WP-02`.
  - Must not: `WP-01` in `suspects`.
  - Check: `VerifyReportTests.test_ac_005_*`
  - WP: WP-02
- AC-006 · Without a report, the lines of passing tests are not read
  - Scenario: the same project without `reports`. The script prints `PASSED acceptance/test_x.py::test_ac_001_total` and `FAILED acceptance/test_x.py::test_ac_002_rounding - assert 3 == 4`, and exits 1.
  - Action: `agentic.py verify`.
  - Expected: `suspects` has the single key `WP-02`, and the phase has no `report` key.
  - Must not: `WP-01` in `suspects`.
  - Check: `VerifyReportTests.test_ac_006_*`
  - WP: WP-02
- AC-007 · With a report, the baseline compares failing tests by name
  - Scenario: the script's report has `test_ac_001_old` failing at baseline. Run 2: the same failure, plus three new passing cases and a different console summary. Run 3: `test_ac_002_new` also fails.
  - Action: `agentic.py baseline`, then `verify` after run 2 and after run 3.
  - Expected:
    - after run 2: `ok` true and `preexisting_failures == ["tests"]`;
    - after run 3: exit 3, the `tests` phase has `status == "regression"`, its `new_failures` has one line containing `test_ac_002_new`, and `suspects` has the single key `WP-02`.
  - Also: a baseline whose report was read, then a verify whose report is `unread` (the command wrote none) with the same old failure on the console: phase-level comparison, `ok` true.
  - Must not: run 2 reported as a regression; a false regression when only one side read a report.
  - Check: `VerifyReportTests.test_ac_007_*`
  - WP: WP-02
- AC-008 · A stale report is never read
  - Scenario: a report from an earlier run is on disk and names `test_ac_001_old` failing. The command now prints `FAILED acceptance/test_x.py::test_ac_002_rounding` to the console and exits 1 without writing a report.
  - Action: `agentic.py verify`.
  - Expected: `"report": "unread"`, `suspects` has the single key `WP-02`, and the report file no longer exists.
  - Must not: `WP-01` in `suspects` (the stale record).
  - Check: `VerifyReportTests.test_ac_008_*`
  - WP: WP-02
- AC-009 · The stop gate reads the report too
  - Scenario: WP-01 owns `AC-001`. The acceptance command writes a NUnit report in which `Describe AC-001 …` passes and `Describe AC-002 …` fails, prints both headings, and exits 1. `reports.acceptance` names the report.
  - Action: `stage.gate_check("WP-01", "DONE")`, then `gate_check("WP-02", "DONE")` with WP-02 owning `AC-002`.
  - Expected: WP-01 gets `None`. WP-02 gets a list whose lines contain `AC-002`.
  - Must not: deny WP-01.
  - Check: `GateReportTests.test_ac_009_*`
  - WP: WP-02
- AC-010 · Report files are not changes outside ownership
  - Scenario: an open stage 1. The acceptance command run by the gate writes `out/acc.xml`, which nobody owns, while `reports.acceptance` is `out/acc.xml`.
  - Action: `close-stage 1 WP-01=done`.
  - Expected: no `OUTSIDE OWNERSHIP` line, and the close is not refused for `out/acc.xml`.
  - Must not: the same file accepted when `reports` does not name it (control: that close prints `OUTSIDE OWNERSHIP`).
  - Check: `GateReportTests.test_ac_010_*`
  - WP: WP-02
- AC-011 · An open-stage that crashes before agentic.py answers is retried once
  - Scenario (conformance, both engines): the first `open-stage 1` reply is `exit_code: 5`, output `bash.exe: *** fatal error - add_item failed, errno 1` (`gate_fail` with `times: 1`).
  - Action: the run.
  - Expected:
    - the run goes on and ends `OK`;
    - the summary's `environment_retries` is `[{"cmd": "open-stage 1", "exit_code": 5}]`;
    - both engines give the same summary.
    - With `times: 2`, the run stops at `wave 1` with today's detail, and `environment_retries` holds one record.
    - An `open-stage 1` that exits 1 with plain text (agentic.py's `die`) is not retried: `environment_retries` is `[]`.
  - Must not: a third attempt; a retry of `close-stage 1` given the same crash (scenario: one gatekeeper call for it, the run stops); a retry of an `open-stage` whose output has JSON (`{"stage": "1", "owners": []}`, exit 3).
  - Check: `RetryTests.test_ac_011_*` (conformance) and `node test_workflow.mjs`
  - WP: WP-03
- AC-012 · A lost prepare reply is retried once
  - Scenario (conformance): the prepare call is lost once (`gate_lost` with `times: 1`), then the same with `times: 2`.
  - Action: the run.
  - Expected:
    - with `times: 1`: ends `OK` and the summary's `environment_retries` is `[{"cmd": "hooks-check + pipeline-plan + briefs", "exit_code": null}]`;
    - with `times: 2`: stops at `prepare` with the detail starting `the gatekeeper returned no usable result`.
  - Must not: more than two prepare calls.
  - Check: `RetryTests.test_ac_012_*`
  - WP: WP-03
- AC-013 · A check the implementer could not run is pending
  - Scenario (conformance): WP-01's report is `DONE`, with `checks: [{"command": "powershell -Command Invoke-Pester", "passed": false, "detail": "not run: permission denied by auto mode"}]`. A second scenario has the same check with detail `2 failed`.
  - Action: the run.
  - Expected:
    - the summary's `untested` is `[{"wp": "WP-01", "claim": "powershell -Command Invoke-Pester", "fact": "not run: permission denied by auto mode"}]` and its `pending` types include `needs validation`;
    - the package is still `done`;
    - the second scenario's `untested` is `[]`;
    - both engines agree.
  - Also: a report with two different not-run checks gives two `untested` entries.
  - Must not: the package marked `blocker`; a duplicate item when the same check comes back in a fix attempt; two different checks collapsed into one.
  - Check: `PendingTests.test_ac_013_*`
  - WP: WP-03
- AC-014 · PowerShell is detected and gets its rules
  - Scenario: a temporary project with `tools/Get-Thing.ps1` (`function Get-Thing { }`) and `tools/Mod.psm1`.
  - Action: `agentic.py stack`, and `validate` with `"stack": ["powershell"]`, then `rules-sync`.
  - Expected:
    - `detected.powershell.files == 2`;
    - `validate` prints "Manifest valid";
    - `.claude/rules/agentic/powershell.md` exists after `rules-sync`.
  - Must not: `.ps1` files counted under another pack, or measured by `agentic.py quality`.
  - Check: `RulesTests.test_ac_014_*`
  - WP: WP-04
- AC-015 · The PowerShell rules hold the field's traps
  - Scenario: `.claude/rules-library/powershell.md`.
  - Action: read it.
  - Expected:
    - the pack skeleton the library test requires (with `<!-- Written for agentic-flow. -->` instead of ECC's attribution);
    - `paths:` with `**/*.ps1`, `**/*.psm1`, `**/*.psd1`;
    - under `## Tests`: `-ModuleName` and `Assert-MockCalled` (call history kept across `It`s; one `Describe` per case), `Import-Module -Force` inside an `It`, array unrolling with `.Count` and `List[object]`, `$script:` scope;
    - the `-OutputFormat NUnitXml` flag and the manifest's `reports` field.
  - Must not: the ECC attribution line (it is not from ECC).
  - Check: `RulesTests.test_ac_015_*`
  - WP: WP-04
- AC-016 · The prompts carry the new duties
  - Scenario: the definitions in `.claude/agents/` and `.claude/commands/architect.md`.
  - Action: read them.
  - Expected:
    - `test-author.md` requires a test of its own for every helper or test double;
    - `test-auditor.md`'s checklist flags a helper or double that no test exercises, as high;
    - `plan-reviewer.md` has a checklist item on existing tests that pin a file or literal the plan changes, critical when 4b does not list them;
    - `architect.md`:
      - asks to grep `acceptance/`, `qa/` and the test folders for every file and literal the plan changes, and to list each hit in 4b;
      - documents `reports` in the manifest fields;
    - `implementer.md` says a check that could not run goes in `checks` with `passed: false` and a detail starting `not run:`, and in `not_checked`, and is no reason for `BLOCKED`.
  - Must not: a definition losing a section it had (the existing definition tests stay green).
  - Check: `PromptTests.test_ac_016_*`
  - WP: WP-04
- AC-017 · The two new scenarios are well formed
  - Scenario: `bench/scenarios/auditor-untested-double/scenario.json` (agent `test-auditor`, prompt `test_auditor`) and `bench/scenarios/plan-pinned-literal/scenario.json` (agent `plan-reviewer`, `prompt_text` "Review architecture.md.", `schema: false`, model `opus`).
  - Action: `bench/test_scenario.py`'s set test, and `scenario.met` on a hand-written report that meets each expectation and one that does not.
  - Expected:
    - the set test passes;
    - the auditor scenario expects `status: FAIL` with a blocking finding mentioning the double's name;
    - the plan scenario expects `text_mentions` `FIX` and the pinning test's file name;
    - the met/unmet reports give `True`/`False`.
  - Must not: an expectation the old definition can meet only by echoing the scenario's own comment (the comment never reaches the agent).
  - Check: `ScenarioTests.test_ac_017_*`
  - WP: WP-05
- AC-018 · Release 2.15.0
  - Scenario: the checkout.
  - Action: read `plugin.json`, `upgrade.NOTES`, `installer.INSTALL_GLOBS`, the test files.
  - Expected:
    - version `2.15.0`;
    - `NOTES["2.15.0"]` has at least 4 entries, among them `reports`, `PowerShell` and `retr`;
    - `.claude/bin/reports.py` is in `INSTALL_GLOBS`;
    - `test_acceptance_v214.py` is absent and `test_fix_cycles.py` defines its classes (`FingerprintTests`, `ReReviewTests`, `EscalationTests`, `BudgetTests`, `ConfigTests`, `AdvisorTests`, `BenchTests`);
    - the hub `docs/how-to/README.md` has at most 260 lines and names eleven languages.
  - Must not: two acceptance files of releases at once.
  - Check: `ReleaseTests.test_ac_018_*`
  - WP: WP-06

### Work packages

#### WP-01 · Runner reports: the reader, the manifest field and install
- Wave 1.
- Files: `.claude/bin/reports.py`, `.claude/bin/test_reports.py`, `.claude/bin/fixtures/reports/`, `.claude/bin/manifest_check.py`, `.claude/bin/test_manifest_check.py`, `.claude/bin/installer.py`.
- Implements: `reports.*` and `manifest_check.report_errors` (section 6). Consumes `core.VERIFY_PHASES`, `core.ROOT`.
- ACs: AC-001, AC-002, AC-003, AC-004, AC-018 (the install line).
- **Patterns to mirror:**
  - `findings.py:1-40`: a small pure module with its constants named at the top and docstrings.
  - `manifest_check.py:204-213`: shape errors as strings.
  - `installer.py:18-40`: the install list.
  - `test_manifest_check.py:150-175`: validate in a temporary project.
- **Gotchas:**
  - JUnit roots are `testsuites` or `testsuite`. Walk with `iter("testcase")`.
  - NUnit 2 and 3 both use `test-case`:
    - NUnit 2 has `result` (`Success`, `Failure`, `Error`, `Ignored`, `Inconclusive`…) and `success="False"`;
    - NUnit 3 has `result` (`Passed`, `Failed`, `Skipped`…);
    - a case fails when `result` is `Failure`, `Error` or `Failed`.
  - The ancestors of a NUnit case: keep a stack while walking. ElementTree has no parent pointers, so use a recursive walk over `test-suite`.
  - The NUnit 2 schema (Pester) is inferred (4b). Write the fixture from the section 5 description, and keep the reader tolerant: unknown attributes are ignored.
  - Install order matters: `verification.py` imports `reports` from WP-02 on.
- **Imports:** `xml.etree.ElementTree as ET`, `pathlib.Path`, `from core import VERIFY_PHASES`.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_reports.py"`, `... -p "test_manifest_check.py"`, `... -p "test_install.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-02 · Verification and the stop gate read the reports
- Wave 2, depends on WP-01 (by implementation: the tests run the real reader).
- Files: `.claude/bin/verification.py`, `.claude/bin/stage.py`, `.claude/bin/test_agentic.py`, `.claude/bin/test_guardrail.py`.
- Implements: `PASS_LINE_RE` and `scan_lines`, and the changes to `run_phases`, `baseline`, `verify`, `acceptance_check`, `tracked_files` and `gate_check`. Consumes `reports.*`.
- ACs: AC-005, AC-006, AC-007, AC-008, AC-009, AC-010.
- **Patterns to mirror:**
  - `verification.py:214-228` and `verification.py:249-313`: where `_scan` is filled and compared;
  - `stage.py:301-340`: the gate;
  - `test_agentic.py:660-735`: the baseline tests with `suite()`, which write a script that prints lines and exits.
- **Gotchas:**
  - `scan_lines` runs after `run_command` and replaces `_scan` (verify) or the gate's `lines`. The acceptance phase of `verify` and `acceptance_check(scan=…)` fill `scan` too.
  - The baseline's `failures` come from `failure_lines(scan_lines(...)[0])`. `failure_text` lines start with `FAILED`, so `FAILURE_LINE_RE` keeps them.
  - `clear_report` must run before every command that has a declared report, including the gate's acceptance run.
  - `tracked_files` is called while a stage is open. It must not die on a broken manifest: `load_manifest` raises `ManifestError`.
  - `"report"` goes into the phase dict only when a report is declared.
  - `verification.py` is at 313 lines; keep each function under 60 lines (`verify` is near it): put the new code in `scan_lines`.
- **Imports:** `from reports import clear_report, failed_tests, failure_text, report_path, report_paths`. For `stage.py`, use the same with `from core import ignored, load_manifest, ManifestError`.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_agentic.py"`, `... -p "test_guardrail.py"`, `python3 -m unittest test_acceptance_v215.VerifyReportTests test_acceptance_v215.GateReportTests` (run from `.claude/bin`), `python3 .claude/bin/agentic.py quality`.

#### WP-03 · Both engines: one retry at open, and checks that could not run
- Wave 1.
- Files: `.claude/bin/pipeline.py`, `.claude/workflows/agentic-implement.js`, `.claude/bin/conformance.json`, `.claude/bin/test_pipeline.py`, `.claude/bin/test_workflow.mjs`.
- Implements: `seq_retry`/`seqRetry`, `untested_item`/`untestedItem`, `environment_retries`, and the `times` field of `gate_fail`/`gate_lost` in both test harnesses.
- ACs: AC-011, AC-012, AC-013.
- **Patterns to mirror:**
  - `pipeline.py:167-178`: `seq`;
  - `pipeline.py:385-392`: concern items;
  - `agentic-implement.js:183-200`: `seq`;
  - `agentic-implement.js:405-415`;
  - `test_pipeline.py:29-80`: the harness;
  - `test_workflow.mjs:490-510`.
- **Gotchas:**
  - Only the three standalone `open-stage` calls per engine (Python `pipeline.py:326`, `:359`, `:429`; JS `agentic-implement.js:450`, `:686`, `:708`) and the prepare call use the retry. The batched `close-stage …  + open-stage …` calls never do.
  - "No JSON" means no line of the step's output parses as a JSON object (reuse `lastJson`/`lines_json`).
  - The existing test "a garbled gatekeeper reply is never retried and stops the run" asserts one gatekeeper call at prepare. Rewrite it to the new rule (two prepare calls, then the stop) and keep a test that a garbled `close-stage` reply is not retried.
  - `untested_item` items dedupe with `pending_key`/`pendingKey` across fix attempts.
  - Conformance `summarize` gains `environment_retries`, so both engines must fill it, even as `[]`.
  - The JS is at 795 lines and the limit is 800: compact the comment block at `agentic-implement.js:190-193` and similar comments to make room.
- **Imports:** none new.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_pipeline.py"`, `node .claude/bin/test_workflow.mjs`, `python3 .claude/bin/agentic.py quality`.

#### WP-04 · PowerShell rules, stack detection and the prompts
- Wave 1.
- Files: `.claude/rules-library/powershell.md`, `.claude/bin/repo_scan.py`, `.claude/bin/test_repo_scan.py`, `.claude/bin/test_definitions.py`, `.claude/agents/test-author.md`, `.claude/agents/test-auditor.md`, `.claude/agents/plan-reviewer.md`, `.claude/agents/implementer.md`, `.claude/commands/architect.md`, `.claude/commands/implement.md`.
- Implements: the `powershell` pack and its signals; the prompt lines of AC-016.
- ACs: AC-014, AC-015, AC-016.
- **Patterns to mirror:**
  - `.claude/rules-library/csharp.md:1-42`: the pack skeleton;
  - `repo_scan.py:19-30`;
  - `test_definitions.py:303-325`;
  - `.claude/agents/test-auditor.md:20-35`: checklist and severity wording;
  - `.claude/agents/plan-reviewer.md:16-32`.
- **Gotchas:**
  - `RulesLibraryTests` requires ECC's `MIT License`. Change it to accept either that or `<!-- Written for agentic-flow. -->`, and assert powershell.md has the second.
  - The verify table needs build, types, lint and tests rows:
    - build: not applicable;
    - types: not applicable;
    - lint: `Invoke-ScriptAnalyzer -Recurse -EnableExit`;
    - tests: `powershell -NoProfile -NonInteractive -Command "Invoke-Pester -EnableExit -OutputFile test-results.xml -OutputFormat NUnitXml"`.
  - `MANIFEST_FIELDS` (`.claude/bin/test_definitions.py:49`) lists the manifest fields `architect.md` must document: add `reports`.
  - The test-auditor is read-only (Read, Glob, Grep). It cannot run a double, so it flags one that no test runs on its own; the test-author writes that test.
  - `architect.md`'s manifest field list is user documentation: add `reports` after `ignore`, and `powershell` to the pack list at `.claude/commands/architect.md:211`.
  - `implement.md` documents the run's fields when presenting a result: add `environment_retries` (the environment retries, per call) beside the gate denials.
- **Imports:** none new.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_definitions.py"`, `... -p "test_repo_scan.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-05 · Two saved scenarios for the prompt changes
- Wave 1. The scenario files consume the prompts by name; the runs are done by hand after integration.
- Files: `bench/scenarios/auditor-untested-double/`, `bench/scenarios/plan-pinned-literal/`, `docs/how-to/bench.md`.
- Implements: two scenario folders and a paragraph in the bench guide naming them.
- ACs: AC-017.
- **Patterns to mirror:**
  - `bench/scenarios/auditor-wrong-expected/scenario.json`;
  - `bench/scenarios/plan-inferred-row/scenario.json`;
  - `docs/how-to/bench.md:81-88`.
- **Gotchas:**
  - **auditor-untested-double:** a brief and an acceptance suite, correct except for a fake clock helper in `acceptance/fakes.py`. It always returns the same instant, so the timeout criterion's test passes against a stub. No test exercises the fake alone. The scenario expects a blocking finding mentioning the fake's name.
  - **plan-pinned-literal:** a tiny library and an `architecture.md`. The plan changes the message `Total: 3 items` and lists no test to update, while `tests/test_report.py` asserts the old message. The scenario expects `FIX` and `test_report`.
  - The `_comment` never reaches the agent, and expectations must not be guessable from the file names alone.
  - Non-ASCII as escapes.
  - No `__init__.py` anywhere under `bench/scenarios/` (the set test fails on one), and the only `.json` files at a scenario folder's top are scenario files: every one is read as scenario metadata.
- **Validation:** `python3 -m unittest discover -s bench -p "test_scenario.py"`, `python3 .claude/bin/agentic.py docs-check`.

#### WP-06 · Release 2.15.0
- Wave 3, depends on WP-01 to WP-05 (by signature: the notes and docs describe them).
- Files: `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/bin/test_fix_cycles.py`, `.claude/bin/test_acceptance_v214.py` (deleted), `README.md`, `docs/how-to/README.md`, `docs/how-it-works.md`, `docs/roadmap/field-report-2026-11-powershell.md`.
- ACs: AC-018.
- **Patterns to mirror:**
  - `upgrade.py:156-167`: notes;
  - `.claude/bin/test_acceptance_v214.py`: the classes to move, verbatim except the module docstring and `ReleaseTests`;
  - `docs/how-to/README.md:130-140`: the languages line.
- **Gotchas:**
  - The hub is capped at 260 lines.
  - Lines that become false: `README.md:90` ("ten language families"), `docs/how-it-works.md:261` ("never retried"), `docs/how-it-works.md:313` ("10 languages"); its module tree gains `reports.py`.
  - The moved classes import `test_agentic`, `testutil` and `test_pipeline` exactly as before.
  - The notes also cover what pull request 113 merged:
    - summary counts no longer read as new failures;
    - Pester's `[-]` marks a failure;
    - prepare messages;
    - the launch warning.
  - In the field report, mark items 2, 4, 5, 6, 7–9 and 10 as shipped in 2.15.0, and item 11's worktree as still excluded.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_fix_cycles.py"`, `python3 -m unittest discover -s .claude/bin -p "test_release.py"`, `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`, `python3 .claude/bin/agentic.py docs-check`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v215.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v215.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/reports.py", ".claude/bin/test_reports.py", ".claude/bin/fixtures/reports/", ".claude/bin/manifest_check.py", ".claude/bin/test_manifest_check.py", ".claude/bin/installer.py"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-018"], "mirror": [".claude/bin/findings.py:1-40", ".claude/bin/manifest_check.py:204-213", ".claude/bin/installer.py:18-40", ".claude/bin/test_manifest_check.py:150-175"]},
    {"id": "WP-02", "wave": 2, "depends_on": ["WP-01"], "files": [".claude/bin/verification.py", ".claude/bin/stage.py", ".claude/bin/test_agentic.py", ".claude/bin/test_guardrail.py"],
     "acs": ["AC-005", "AC-006", "AC-007", "AC-008", "AC-009", "AC-010"], "mirror": [".claude/bin/verification.py:214-228", ".claude/bin/verification.py:249-313", ".claude/bin/stage.py:301-340", ".claude/bin/test_agentic.py:660-735"]},
    {"id": "WP-03", "wave": 1, "depends_on": [], "files": [".claude/bin/pipeline.py", ".claude/workflows/agentic-implement.js", ".claude/bin/conformance.json", ".claude/bin/test_pipeline.py", ".claude/bin/test_workflow.mjs"],
     "acs": ["AC-011", "AC-012", "AC-013"], "mirror": [".claude/bin/pipeline.py:167-178", ".claude/bin/pipeline.py:385-392", ".claude/workflows/agentic-implement.js:183-200", ".claude/workflows/agentic-implement.js:405-415", ".claude/bin/test_pipeline.py:29-80", ".claude/bin/test_workflow.mjs:490-510"]},
    {"id": "WP-04", "wave": 1, "depends_on": [], "files": [".claude/rules-library/powershell.md", ".claude/bin/repo_scan.py", ".claude/bin/test_repo_scan.py", ".claude/bin/test_definitions.py", ".claude/agents/test-author.md", ".claude/agents/test-auditor.md", ".claude/agents/plan-reviewer.md", ".claude/agents/implementer.md", ".claude/commands/architect.md", ".claude/commands/implement.md"],
     "acs": ["AC-014", "AC-015", "AC-016"], "mirror": [".claude/rules-library/csharp.md:1-42", ".claude/bin/repo_scan.py:19-30", ".claude/bin/test_definitions.py:303-325", ".claude/agents/test-auditor.md:20-35", ".claude/agents/plan-reviewer.md:16-32"]},
    {"id": "WP-05", "wave": 1, "depends_on": [], "files": ["bench/scenarios/auditor-untested-double/", "bench/scenarios/plan-pinned-literal/", "docs/how-to/bench.md"],
     "acs": ["AC-017"], "mirror": ["bench/scenarios/auditor-wrong-expected/scenario.json", "bench/scenarios/plan-inferred-row/scenario.json", "docs/how-to/bench.md:81-88"]},
    {"id": "WP-06", "wave": 3, "depends_on": ["WP-01", "WP-02", "WP-03", "WP-04", "WP-05"], "files": [".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/bin/test_fix_cycles.py", ".claude/bin/test_acceptance_v214.py", "README.md", "docs/how-to/README.md", "docs/how-it-works.md", "docs/roadmap/field-report-2026-11-powershell.md"],
     "acs": ["AC-018"], "mirror": [".claude/bin/upgrade.py:156-167", ".claude/bin/test_fix_cycles.py", "docs/how-to/README.md:130-140"]}
  ]
}
```

## 9. Test strategy
- **Unit:** each WP writes its own, with the stdlib `unittest`, in its files:
  - `test_reports.py` reads the fixtures;
  - `test_agentic.py` and `test_guardrail.py` use temporary projects (`Repo` from `test_agentic`) with scripts that print lines, write a report and exit;
  - conformance scenarios run both engines.
- **Acceptance:** `.claude/bin/test_acceptance_v215.py`, written first from AC-001 to AC-018. It must be red before the code (missing `reports` module, missing pack, missing scenario folders, version 2.14.0). The classes are `ReportTests`, `ManifestTests`, `VerifyReportTests`, `GateReportTests`, `RetryTests`, `PendingTests`, `RulesTests`, `PromptTests`, `ScenarioTests` and `ReleaseTests`. Engine criteria use `test_pipeline.run_scenario` on named conformance scenarios and `node test_workflow.mjs`, as `test_acceptance_v214.py` does. Nothing spends a session.
- **QA, by hand after integration:**
  - all CI suites locally, including `acceptance/`, `qa/` and `docs-check`, which `verify` does not run;
  - mutations: at least one per behaviour, among them:
    - passing lines read again;
    - a stale report read;
    - report paths not ignored;
    - a second retry;
    - `close-stage` retried;
    - an open-stage with JSON retried;
    - `not run` ignored;
    - the NUnit ancestors dropped;
    - `.ps1` not detected;
  - a simulated installed project;
  - the two new scenarios run against the 2.14.0 definitions with `bench/scenario.py --against <old> --repeat 5 --save` (real sessions; cost not measured in advance);
  - a quick A/B is not required: no engine cost change is expected.

## 10. Decisions
| Decision | Discarded | Why |
|---|---|---|
| Read the failing tests from the runner's XML report when the manifest names it; fall back to the console with passing lines skipped (user's choice) | Report only; console filter only | The console cannot tell which `Describe` a Pester `[-]` belongs to; the report can. The filter still helps every run without a report. |
| JUnit and NUnit 2/3 only | TRX, TAP, JSON | Those two cover pytest, jest (with jest-junit), Pester, NUnit and most CI runners; more formats can be added to the same function. |
| `xml.etree.ElementTree` with a size cap | `defusedxml` | No new dependency. The standard parser does not resolve external entities, and the size cap bounds the rest. Reports are local files the project's own command writes. |
| Delete a declared report before its command runs | Compare modification times | Simpler and exact; the file is declared as the flow's artefact. |
| Report paths ignored by the stage snapshot automatically | Require them in `ignore` | One declaration, not two that can drift. |
| One retry for prepare and standalone `open-stage` calls only, in both engines (user's choice); the never-retry rule stays for every other call | No retry, clearer message only | Both can be repeated safely: `open-stage` resets the gate counters and retakes the snapshot, and prepare only reads and writes the briefs again. `close-stage` and verify change state or cost minutes. |
| A check that could not run becomes `needs validation` pending (user's choice) | `BLOCKED`; nothing until reproduced | Verification runs the whole suite after the wave anyway; the person sees what was not run, and nothing stops. |
| PowerShell pack written for the flow, with its own attribution line | Wait for an upstream pack | No upstream PowerShell rules in ECC are known here (not checked online); the traps are first-hand. |
| Prompt changes measured with two saved scenarios, old against new, 5 runs each (user's choice) | Ship unmeasured | The repository's rule since 2.13.0: a prompt is tested like code. |
| Release 2.15.0 also ships pull request 113's merged fixes | A 2.14.1 first | One release, one acceptance file, one note list. |
| `test_acceptance_v214.py`'s classes move as they are to `test_fix_cycles.py` | Spread them across suites by module | It avoids ownership conflicts with WP-03's files; a suite by domain, as in 0017. |
| No worktree per cycle | Run each cycle in a worktree | The guard, the ledger and `.claude/state` assume the repository root; a design of its own if it is ever needed. |

## 11. Risks and open questions
- **The NUnit 2 (Pester 3.4) and JUnit shapes are inferred.** No Pester or pytest report was read here. The fixtures are written from the formats' documented structure, and the reader ignores what it does not know. If a real Pester report differs, `failed_tests` returns `[]` or `None`, and verification falls back to the console: no worse than today. The next PowerShell run should declare `reports` and confirm.
- **A report from a command that wrote it partway** (crashed mid-write) is not well formed and gives `None`, so the console is used.
- **`PASS_LINE_RE` may drop a failure line containing `ok `** at the line's start. It is anchored to Go's `ok  pkg` form, and a failing Go package prints `FAIL` lines, which are kept.
- **The scenario runs are real sessions,** and their cost was not measured in advance. If the old definition also passes a scenario, that scenario does not show the change: it is reported as such, never tuned until it passes.
- **Parallel stop gates share one report file.** Two packages finishing at once both run the acceptance command; one gate's `clear_report` can delete the other's fresh report. That gate then falls back to the console filter, so it is no worse than today. Not measured.
- **The old acceptance file fails from wave 0 on.** `test_acceptance_v214.py` asserts it is the only acceptance file, and so does `test_layout.py` (`test_this_repository_keeps_at_most_one`), so `test_*.py` runs in waves 1-2 show that one failure until WP-06 deletes the file. It is expected, not a regression of the package that ran them.
- **Issue 118 stays open** after this release. Its cause is not reproduced; this design only makes the effect visible.
