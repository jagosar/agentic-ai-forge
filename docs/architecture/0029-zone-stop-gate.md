# Architecture: the stop gate also holds the test-author and QA to the quality limits of their own files (agentic-flow 2.21.0, issue 134)
Type: feature · Size: standard

## 1. Goal

Since 2.20.1 the test-author and QA are told the quality limits, and a violation in their files stops the run at verification naming their zone. Nobody fixes those files then: review, QA and documentation do not start until a person steps in. The flow already has a mechanism that catches a defect while its author can still fix it: the stop gate, which refuses an implementer's finished report when the acceptance tests of its package fail, at most twice. This release gives the same gate a second check, for the test-author and for QA: when either submits a finished report, the hook measures the files of its own zone against the quality limits and, if one is over, refuses the report with the violation lines. The agent fixes them in the same call, with its context intact, and for the test-author before any code exists. It closes issue 134.

## 2. Scope

### Included

- **A zone check in the stop gate.** For the owner of the acceptance zone (`AT`) and the owner of QA's zone (`QA`): a finished report is refused while a file of that zone is over a quality limit, with the violation lines and the count of denials.
- **The same cap and reset as the package gate.** At most two denials per agent and stage; the third report goes through, and the run then stops at verification as it does today. `open-stage` resets the count.
- **Only the zone is measured.** The check reads the files of the agent's zone, not the project: 0.38 s for an acceptance zone of 155 files and 19,531 lines, measured on a real project (the whole project took 1.08 s).
- **Docs and release 2.21.0**: the guide's line on the stop gate, the notes, the budget, one acceptance file.

### Excluded (non-goals)

- A fix cycle for the test-author or QA after verification (issue 134's own proposal): a new path in both engines, and it would reopen the acceptance tests once the code exists. Discarded with the user in favour of this gate.
- Any change to the engines, their prompts, the plan or the conformance scenarios.
- The denials of `AT` and `QA` in the run's record: the engines read the gate's summary line for packages only. See section 11.
- Changing the package gate: an implementer's report is checked as today.
- The agents' definitions: the denial's own text says what to do.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`
- Bench: `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/bin/core.py                  WP-01  the statuses that count as a finished report, per zone
.claude/bin/verification.py          WP-01  the quality violations of one zone
.claude/bin/stage.py                 WP-01  the zone check of the stop gate
.claude/bin/guardrail.py             WP-01  report_gate asks it for AT and QA
.claude/bin/test_zone_gate.py        WP-01  new: unit cases
docs/how-it-works.md                 WP-02  the glossary's line on the stop gate
.claude-plugin/plugin.json           WP-02  2.21.0
.claude/bin/upgrade.py               WP-02  NOTES["2.21.0"]
.claude/flow-budget.json             WP-02
.claude/bin/test_native_usage.py     WP-02  the classes moved from test_acceptance_v220.py
.claude/bin/test_acceptance_v220.py  WP-02  deleted
.claude/bin/test_acceptance_v221.py  AT
.claude/flow-history.json            by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| The hook hands a `StructuredOutput` call (an agent's report) to `report_gate(owner_id, tinput)`, which today acts only when the owner is a package (`WP_ID_RE`): it asks `gate_check` and, with failing lines, calls `block(...)` with a message that names the owner, the status, "denial N of 2" and the lines | `.claude/bin/guardrail.py:284-296`, `.claude/bin/guardrail.py:346-354` | The function that gains the zone branch; `block` exits 2 and the agent reads the message | read |
| `gate_check(owner_id, status)`: None lets the report through, a list of lines refuses it. It lets through when the status is not a finished one, the denials are used up, or anything goes wrong (it fails open, printing "[agentic guard] gate skipped: …"). On a refusal it adds one to the owner's denials in `gate.json` and keeps the lines shown | `.claude/bin/stage.py:322-348` | The shape to mirror for the zone check: same cap, same counter, same fail-open | read |
| The gate's constants: `GATE_MAX_DENIALS = 2`, `GATE_MAX_LINES = 40`, `GATE_STATUSES = ("DONE", "DONE_WITH_CONCERNS")` | `.claude/bin/core.py:37-41` | The zone statuses go beside them | read |
| The counters: `gate_denials(fn)` reads and writes `gate.json` under a lock; `gate_reset(owners)` drops the counters of the ids given | `.claude/bin/stage.py:296-305` | Reuse both; the zone's key is its id, `AT` or `QA` | read |
| `open-stage` resets the gate of the stage's owners; for the stages `acceptance` and `qa` the owner is the zone's entity, whose id is `AT` or `QA` | `.claude/bin/stage.py:29`, `.claude/bin/stage.py:57-60`, `.claude/bin/stage.py:220-228` | A reopened stage (the test-author's revision, a QA re-check) gets its own two denials with no new code | read |
| The zones: `at_entity(manifest)["files"]` and `qa_entity(manifest)["files"]`; `owns(pattern, path)` tells whether a path is under one | `.claude/bin/core.py:226-233`, `.claude/bin/core.py:261-263` | Unchanged | read |
| The quality baseline and its helpers: `quality_state()` (None without a baseline, `{"unreadable": True}` when broken), `quality_files(state)` (every code file the ratchet measures), `quality_module()` with `measure(root, files, limits)`, `limits_of(state)` and `check(state, current)`, whose result has `violations` and `details`, one of each per violation | `.claude/bin/verification.py:100-140`, `.claude/bin/quality.py:207-262` | `check` only looks at the files it is given: measuring the zone's files gives the zone's violations | read |
| A violation line and its detail: `FAIL file <path> exceeds its <metric> allowance` / `FAIL function <path>::<name> exceeds its <metric> allowance`, then `  <key> <metric>: now N, allowed M` | `.claude/bin/quality.py:238-243` | The lines shown to the agent, in pairs | read |
| The reports' statuses: the test-author answers `DONE` or `BLOCKER`; QA answers `PASS`, `FAIL` or `BLOCKER` | `.claude/workflows/pipeline-spec.json:1-40` | A finished report is `DONE` for `AT`, `PASS` or `FAIL` for `QA` | read |
| The hook's owner comes from the agent's claim or from `AGENTIC_WP`; the tests pass the latter | `.claude/bin/guardrail.py:346-350`, `.claude/bin/test_guardrail.py:203-216` | The tests of the zone gate run the hook with `env={"AGENTIC_WP": "AT"}` | read |
| Tests of the package gate | `.claude/bin/test_guardrail.py:203-260` | They stay green: a package's report takes the same branch as today | read |
| `stage.py` imports from `verification.py` already | `.claude/bin/stage.py:23` | The zone check may import the new helper there; nothing new reaches the hook's start-up, which a test pins | read |
| The guide's line on the stop gate | `docs/how-it-works.md:389` | Line to extend (WP-02) | read |
| The release pattern, and the acceptance file of the last minor release | `.claude/bin/upgrade.py:156-170`, `.claude/bin/test_native_usage.py:1-8` (where the last minor release's acceptance file ends up), `.claude/bin/test_qa_recheck.py:1-8` | Its classes move to a named file | read |

What must not change: the package gate and its messages, the engines, `verify` and `zone_suspects`, what the hook does for every other tool call.

## 5. Data model

```python
# core.py, beside GATE_STATUSES
ZONE_GATE_STATUSES = {"AT": ("DONE",), "QA": ("PASS", "FAIL")}  # a finished report, per zone
```

`gate.json` keeps the zone's counter like a package's: `{"AT": {"denials": 1, "last": [<the lines shown>]}}`.

The denial the agent reads (one message, `block`):

```
{owner}: the report says {status} but files of your zone are over the quality limits (denial {n} of 2):
  FAIL file acceptance/test_money.py exceeds its long_lines allowance
    acceptance/test_money.py long_lines: now 3, allowed 0
Bring those files within the limits (shorter lines, smaller functions, a large file split in two) without changing what they check, and submit the report again.
```

## 6. Contracts between modules

**`verification.py`:**

```python
def zone_quality_lines(manifest, owner_id)
    """The quality violations of the files of that owner's zone ("AT" or "QA"): each violation line followed by its
    detail line, as quality_check prints them; [] when the zone is within the limits. Measures only the zone's
    files. [] without a quality baseline, with an unreadable one, or for any other owner."""
```

**`stage.py`:**

```python
def zone_gate_check(owner_id, status)
    """The stop gate for the owner of a zone. None lets the report through; a list of lines refuses it. Lets
    through when the owner is not "AT" or "QA", the status is not one of ZONE_GATE_STATUSES[owner_id], the owner
    used up its denials, the zone is within the limits, or anything at all goes wrong: it catches Exception (with
    `# noqa: BLE001`, as the hook's entry point does) and prints the same "[agentic guard] gate skipped: ..." line
    as gate_check. On a refusal it adds one to the owner's denials and
    stores the lines shown: the first GATE_MAX_LINES lines, violations and their details counted together."""
```

**`guardrail.report_gate(owner_id, tinput)`:** unchanged for a package. For any other owner it asks `zone_gate_check(owner_id, tinput.get("status"))` and, with lines, calls `block` with the message of section 5 (the count read from `gate_denials` after the refusal, as the package branch does).

The order of the checks inside `zone_gate_check` is the package gate's: status, then the cap, then the measurement. A report that is not finished costs no measurement.

Why every exception is caught here, and not only the three `gate_check` catches: the zone check runs the quality code over a baseline a person may have edited (`{"files": "x"}` raises `AttributeError` in `check`, `{"limits": {"line_chars": "x"}}` raises `TypeError` in `measure`), and the hook turns an uncaught exception of a zoned agent into a refusal with no count (`.claude/bin/guardrail.py:630-644`): every report would be refused, with no cap.

## 7. Conventions

- English everywhere; usage errors keep the `Uso:` prefix (design 0016).
- No type annotations in signatures (Python 3.9), as in the rest of `.claude/bin`. This overrides the python rules' "type annotations on every public signature": it is the existing code's style, not a finding.
- Every `open` and `read_text` names `encoding="utf-8"`.
- The gate fails open: no error of its own may refuse a report. In `zone_gate_check` that means `except Exception`, the one place this design allows it.
- This repository's own quality phase measures `.claude/bin`, the tests of this design included: no line over 120 characters, no new function over 60 lines (100 in a test), no new file over 800 lines.
- The guides do not cite flow version numbers. Commit format `type: summary`; the flow history is regenerated as the last commit.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · The test-author's finished report is refused while a file of its zone is over a limit
  - Scenario: a temporary repo built by the tests' `Repo` helper (`.claude/bin/test_agentic.py:45-76`) with its default manifest, a file `src/a.py` holding `x = 1`, and a quality baseline created by `agentic.py quality --init`. After the baseline, `acceptance/test_money.py` is written with one line of 130 characters.
  - Action: the hook receives a `StructuredOutput` call whose input has `"status": "DONE"`, with `AGENTIC_WP=AT`.
  - Expected: exit 2. The message on stderr contains `AT: the report says DONE`, `over the quality limits`, `denial 1 of 2`, `FAIL file acceptance/test_money.py exceeds its long_lines allowance` and `without changing what they check`. `.claude/state/gate.json` holds `AT` with `"denials": 1`.
  - Must not: exit 0 while the file is over the limit and denials remain.
  - Check: `test_acceptance_v221.py`
  - WP: WP-01

- AC-002 · A zone within the limits, a report that is not finished, and other people's files do not refuse
  - Scenario: as AC-001.
  - Action: the same call (a) after the long line is shortened; (b) with the long line and `"status": "BLOCKER"`; (c) with the acceptance file clean and a line of 130 characters in `src/a.py` and in `qa/test_qa.py`.
  - Expected: exit 0 in the three cases; no `AT` entry is added to `gate.json` by any of them.
  - Must not: a violation outside the acceptance zone refusing the test-author.
  - Check: `test_acceptance_v221.py`
  - WP: WP-01

- AC-003 · Two denials at most, and a stage that opens starts again
  - Scenario: as AC-001, the file left over the limit.
  - Action: the same `DONE` call three times; then `agentic.py open-stage acceptance`; then the call once more.
  - Expected: exits 2, 2, 0 (`denial 1 of 2`, `denial 2 of 2`, then let through); after `open-stage`, exit 2 with `denial 1 of 2`.
  - Must not: a third denial without a reset.
  - Check: `test_acceptance_v221.py`
  - WP: WP-01

- AC-004 · QA is held to its own zone
  - Scenario: as AC-001, with `qa/test_qa.py` holding one line of 130 characters and the acceptance zone clean.
  - Action: the hook receives a report with `AGENTIC_WP=QA` and status `PASS`, then `FAIL`, then (after `open-stage qa`) `BLOCKER`.
  - Expected: exit 2 for `PASS` (`QA: the report says PASS`, `denial 1 of 2`, the file named) and for `FAIL` (`denial 2 of 2`); exit 0 for `BLOCKER`. In a fresh repo with the QA file clean and `acceptance/test_money.py` over the limit, a `PASS` report exits 0.
  - Must not: QA refused for a file of the acceptance zone.
  - Check: `test_acceptance_v221.py`
  - WP: WP-01

- AC-005 · Without a baseline, or with what the baseline already allows, nothing is refused
  - Scenario: four repos like AC-001's: one whose baseline is deleted; one whose baseline file holds `[1]`; one whose baseline file holds `{"limits": {"line_chars": "x"}}` (an object of the wrong shape: comparing a line's length with it raises `TypeError`); one where the acceptance file with the long line exists before `quality --init`, so the baseline records its allowance.
  - Action: the `DONE` call with `AGENTIC_WP=AT` in each.
  - Expected: exit 0 in the four; no `Traceback` on stderr; `gate.json` gains no `AT` entry.
  - Must not: a refusal the agent cannot fix by editing its files.
  - Check: `test_acceptance_v221.py`
  - WP: WP-01

- AC-006 · A package's report is checked as before
  - Scenario: the repo of AC-001 with the acceptance file over the limit and an acceptance command that passes.
  - Action: the hook receives an implementer's report with status `DONE` and `AGENTIC_WP=WP-01`; and a report with status `PASS` and `AGENTIC_WP=REVIEW`. The test writes `acc.py` with `raise SystemExit(0)`: the default manifest's acceptance command runs it.
  - Expected: exit 0 in both; `gate.json` gains no entry.
  - Must not: a package or the reviewer refused for the quality of a zone.
  - Check: `test_acceptance_v221.py`
  - WP: WP-01

- AC-007 · Docs and release 2.21.0
  - Scenario: this repository.
  - Action: read `plugin.json`, `upgrade.NOTES`, `docs/how-it-works.md`, the test files.
  - Expected: version `2.21.0`; `NOTES["2.21.0"]` has at least one note that contains `stop gate` and `test-author`, and it is the key right above `"2.20.2"`; the guide's line that starts `- **Stop gate:**` contains `test-author` and `QA`; the only `test_acceptance*.py` is `test_acceptance_v221.py`; `test_native_usage.py` holds the classes `UsageOfARunTests`, `SaveResultTests`, `NativeRulesTests` and `DefinitionTests`.
  - Must not: `2.21.0` anywhere in `docs/how-it-works.md`.
  - Check: `test_acceptance_v221.py`
  - WP: WP-02

### Work packages

#### WP-01 · The zone check of the stop gate
- Wave 1.
- Files: `.claude/bin/core.py`, `.claude/bin/verification.py`, `.claude/bin/stage.py`, `.claude/bin/guardrail.py`, `.claude/bin/test_zone_gate.py`.
- Implements sections 5 and 6 whole.
- ACs: AC-001, AC-002, AC-003, AC-004, AC-005, AC-006.
- **Patterns to mirror:** `.claude/bin/stage.py:322-348` (`gate_check`: the order of its checks, its counter, its fail-open); `.claude/bin/guardrail.py:284-296` (how a refusal is turned into the message); `.claude/bin/verification.py:116-140` (how the files are listed, measured and checked); `.claude/bin/test_guardrail.py:203-260` (how the gate's tests call the hook and read `gate.json`); `.claude/bin/test_zone_attribution.py:55-70` (how a unit case patches the baseline).
- **Gotchas:**
  - Measure only the zone: `[f for f in quality_files(state) if any(owns(z, f) for z in zone)]`, then `measure` and `check`. `check` over those files alone yields only their violations. Pair each violation with its detail as `quality_check` does (`.claude/bin/verification.py:137`).
  - `verification.py` already has `ZONES = (("AT", at_entity), ("QA", qa_entity))` (`.claude/bin/verification.py:269-281`, design 0028): take the zone's entity from it instead of branching on the ids again.
  - Unit cases: `core.ROOT` is fixed when the module is imported, so `test_zone_gate.py` cannot point the in-process functions at a temporary repo. Go through the tests' `Repo.run` for anything that measures files (patching `quality_state` and `quality_files` alone would still read this repository's files); `mock.patch.object`, as `.claude/bin/test_zone_attribution.py:55-70` uses it, is for the cases that never reach the measurement (no baseline, an unreadable one, an error raised inside).
  - `quality_state()` returns `{"unreadable": True}` for a broken baseline: return `[]` before measuring.
  - `zone_gate_check` catches `Exception` and lets the report through (section 6 says why).
  - `report_gate` keeps `WP_ID_RE.fullmatch(owner_id)` for the package branch; the zone branch is the `else`, and `zone_gate_check` itself returns None for any owner that is not `AT` or `QA` (the reviewer, the doc-updater, no owner at all).
  - `guardrail.py` is 644 lines and `stage.py` 348, under the quality ratchet (a file of at most 800 lines, a function of at most 60).
  - `test_agentic.py` and `test_guardrail.py` are not to grow: the unit cases go in `test_zone_gate.py`.
  - `test_lean.py`'s budget check is red until WP-02 raises the budget, so the whole `.claude/bin` suite is red for that one test in wave 1: expected.
  - `test_acceptance_v220.py`'s `ReleaseTests` ("the only acceptance file") is red from wave 0, as soon as `test_acceptance_v221.py` exists, until WP-02 moves that file: expected, not a regression.
- **Exact imports and APIs:** `from verification import zone_quality_lines` in `stage.py` (it imports from there already); `ZONE_GATE_STATUSES`, `GATE_MAX_DENIALS`, `GATE_MAX_LINES` from `core`; `zone_gate_check` beside `gate_check` in `guardrail.py`'s import from `stage`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_zone_gate.py"`; `python3 -m unittest discover -s .claude/bin -p "test_guardrail.py"`; `python3 -m unittest discover -s .claude/bin -p "test_hook_path.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · Docs, notes, release and the moved tests
- Wave 2 (it moves the previous acceptance file and raises the budget, after the code).
- Files: `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_native_usage.py`, `.claude/bin/test_acceptance_v220.py`.
- ACs: AC-007.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-170`; `.claude/bin/test_qa_recheck.py:1-8` (the header of a file of moved tests); `docs/how-it-works.md:389` (the line to extend).
- **Gotchas:**
  - Move the classes of `test_acceptance_v220.py` with their helpers and constants (`RulesRepo` included). Drop its `ReleaseTests`: it pins the version and "the only acceptance file".
  - `NOTES["2.21.0"]` goes right above `"2.20.2"` in the dictionary.
  - `flow-budget.json`: raise only what is exceeded, with its why.
  - `.claude/flow-history.json` is regenerated by the maintainer as the last commit, not by this package.
- **WP validation:** the five commands of section 3 and `python3 -m unittest discover -s acceptance`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v221.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v221.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/core.py", ".claude/bin/verification.py", ".claude/bin/stage.py", ".claude/bin/guardrail.py", ".claude/bin/test_zone_gate.py"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-005", "AC-006"], "mirror": [".claude/bin/stage.py:322-348", ".claude/bin/guardrail.py:284-296", ".claude/bin/verification.py:116-140", ".claude/bin/test_guardrail.py:203-260", ".claude/bin/test_zone_attribution.py:55-70"]},
    {"id": "WP-02", "wave": 2, "depends_on": ["WP-01"], "files": ["docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_native_usage.py", ".claude/bin/test_acceptance_v220.py"],
     "acs": ["AC-007"], "mirror": [".claude/bin/upgrade.py:156-170", ".claude/bin/test_qa_recheck.py:1-8", "docs/how-it-works.md:389"]}
  ]
}
```

## 9. Test strategy

- **Acceptance** (`test_acceptance_v221.py`, written first and red): AC-001 to AC-006 run the real hook (`agentic.py hook`, the report on stdin) in temporary repos with a real quality baseline, and read its exit code, its message and `gate.json`. AC-007 reads files. Nothing is spent.
- **Unit:** `test_zone_gate.py` covers `zone_quality_lines` and `zone_gate_check` directly: a function over its limit, a zone declared as one file, more than `GATE_MAX_LINES` lines, an error inside the check.
- **Teeth:** each behaviour is broken once by hand (the whole project measured instead of the zone, the cap ignored, `BLOCKER` gated, a package sent to the zone check) and the acceptance test must fail.
- **By hand, before the pull request:** the time of the zone check on a real project's acceptance zone, reported in the pull request; `acceptance/`, `qa/`, the installed-project job, and `agentic.py flow-history` as the last commit with its `--check`.

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| The stop gate checks the zone when its owner submits a finished report | A fix cycle for the test-author after verification (issue 134's proposal) | The gate catches the violation while the agent still has its context and, for the test-author, before any code exists: nobody reopens the acceptance tests once code is written against them. It is deterministic, needs no engine change (the workflow script is 30 lines from its recorded size limit) and no extra agent call. Chosen by the user |
| Only the zone's files are measured | The project's whole quality check, filtered | 0.38 s against 1.08 s on a real project, in a hook call; and a violation elsewhere is not this agent's to fix |
| The same cap, counter and reset as the package gate | A separate counter or no cap | One mechanism to understand. A gate with no cap can stall a run; after two denials the report goes through and verification names the zone, as since 2.20.1 |
| QA is gated on `PASS` and on `FAIL` | Only on `PASS` | A report that found defects is as finished as one that found none, and its test files are just as measured |
| `BLOCKER` is never gated | Gate every report | An agent that cannot go on must be able to say so |
| The denial tells the agent not to change what the files check | Only list the violations | The cheapest way to shorten a test is to delete an assertion; the test-auditor still reviews the tests afterwards, but the instruction costs one clause |
| The zones' denials are not in the run's record | A `GATE:` line for `AT` and `QA` | The engines parse that line for packages only; reporting them needs an engine change, which this design avoids. They are in `gate.json` |
| A minor release, 2.21.0, with its own acceptance file | A fix release | It adds a behaviour to the hook; the 2.20.x fixes repaired behaviour the flow already claimed |
| Two waves of one package each | One package | The release moves the previous acceptance file and raises the budget, which depend on the code's final size |
| Written with Fable 5.2 | Pause to switch model | The user chose it at the model gate |

## 11. Risks and open questions

- **The agent may fix the limit by weakening a test.** The denial says not to, and the test-auditor reviews the acceptance tests after the test-author; QA's tests have no later reviewer. Not measured.
- **Two denials may not be enough** for a file far over a limit (1,025 lines against 800 was seen once). Then the report goes through and the run stops at verification, naming the zone: the state before this release.
- **The time the check adds** to the one hook call that carries a report: 0.38 s for 155 files and 19,531 lines, measured once on one project. Not measured on larger zones or on Windows.
- **The denials of `AT` and `QA` are not shown by `/implement`.** They are in `.claude/state/gate.json` until the next stage opens.
- **Whether a `claude -p` agent's report reaches the hook as a `StructuredOutput` call** in the fallback engine is what the package gate already relies on; it is not re-verified here.
