# Architecture: whoever writes code is told the quality limits, and a quality failure names the zone that owns it (agentic-flow 2.20.1, issue 134)
Type: fix · Size: standard

## 1. Goal

The verification's quality phase checks every file of the project, the acceptance tests and QA's tests included, against limits that no agent is ever told: a line of at most 120 characters, a new file of at most 800 lines, a new function of at most 60. In a real project the test-author wrote acceptance files over those limits twice; the failures went to implementation packages that cannot edit that zone, both fix cycles were spent on them, and the run ended in REVIEW with review, QA and documentation never started. When the limit was written into the plan by hand, the same project's next run ended OK with no fix cycle. This release prints the active limits for the agents that write code, and stops a quality failure from being attributed to a package that does not own the file.

## 2. Scope

### Included

- **The limits in the prompt.** The plan's rules text, which already reaches the implementer, the test-author, the standards reviewer and QA, ends with one sentence stating the limits the project's quality baseline enforces. The one-off commands print it too. No baseline, no sentence.
- **Quality failures attributed by path only.** In the quality phase a violation names a file, so the package that owns that file is the suspect. A criterion's number in a file or function name (`test_ac_001_…`) no longer makes the package that answers for that criterion a suspect.
- **The owning zone is named.** When a quality violation is in the acceptance zone or in QA's zone, `verify`'s result says so in a new key, `zone_suspects`, and `/implement` presents it.
- **Release 2.20.1**: notes, the budget.

### Excluded (non-goals)

- Sending the test-author (or QA) to a fix cycle for its own files: a new path in both engines, and the workflow script is 30 lines from its recorded size limit. With the limits printed the case should be rare; issue 134 keeps the proposal.
- A `validate` warning about section 7.
- Any change to the engines, their prompts or the conformance scenarios.
- Attribution in the other phases: a failing test still names the package through its criterion.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`
- Bench: `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/bin/verification.py         WP-01  attribution of the quality phase, zone_suspects, the limits' sentence
.claude/bin/test_zone_attribution.py WP-01  new: unit cases of the quality phase's attribution
.claude/bin/launch.py               WP-02  the plan and the one-off prompts end with the limits
.claude/commands/implement.md       WP-02  how to present zone_suspects
.claude/bin/test_launcher.py        WP-02
.claude-plugin/plugin.json          WP-03  2.20.1
.claude/bin/upgrade.py              WP-03  NOTES["2.20.1"]
.claude/flow-budget.json            WP-03
.claude/bin/test_acceptance_v220.py WP-03  the version it pins
docs/how-it-works.md                WP-03  the glossary's line on failed verifications
.claude/bin/test_quality_limits.py  AT     the acceptance tests of this fix
.claude/flow-history.json           by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| `attribute(manifest, lines)` maps a failure's output to packages: by a file path of theirs, or by an `AC-NNN` found in the text (case-insensitive, `AC`, `ac_`, `AC-`) through the package's `acs` | `.claude/bin/verification.py:249-266` | The function to change: the criteria route is wrong for the quality phase | read |
| `verify` builds `suspects` from every failing phase's output with `attribute`, and prints `{"ok", "blocking", "preexisting_failures", "suspects", "phases"}` | `.claude/bin/verification.py:288-336` | Where the quality phase is told apart and `zone_suspects` is added | read |
| The quality phase: name `quality`, its output is, per violation, `FAIL file <path> exceeds its <metric> allowance` or `FAIL function <path>::<name> exceeds its <metric> allowance`, then a detail line `  <key> <metric>: now N, allowed M` | `.claude/bin/verification.py:142-149`, `.claude/bin/quality.py:238-243` | The lines that are attributed; a function's name can carry a criterion's number | read |
| The baseline: `quality_state()` is None without `.claude/quality-baseline.json`, `{"unreadable": True}` when it is not a JSON object | `.claude/bin/verification.py:100-114` | No baseline or an unreadable one: no limits are printed | read |
| The limits: `quality.limits_of(baseline)` is the defaults (`function_lines` 60, `test_function_lines` 100, `nesting` 4, `file_lines` 800, `file_growth` 30, `line_chars` 120) overridden by the baseline's `limits` | `.claude/bin/quality.py:18-19`, `.claude/bin/quality.py:58-59` | Reuse it; `quality_module()` is how `verification.py` reaches `quality.py` | read |
| The acceptance zone and QA's zone: `at_entity(manifest)["files"]` and `qa_entity(manifest)["files"]` | `.claude/bin/core.py:226-233` | A path ending in `/` owns the folder | read |
| The engines turn `suspects` into defects only for ids that are packages; with none they stop with "a verification phase fails and no work package owns the failure (see verification)" and the whole `verify` output is in the result's `verification` | `.claude/bin/pipeline.py:280-293`, `.claude/bin/pipeline.py:668-676` | Unchanged: a new key of `verify`'s output reaches the result as it is | read |
| `pipeline_plan` puts `rules_text` and its checksum in the plan; `render_prompt` builds the one-off commands' prompts | `.claude/bin/launch.py:302-307`, `.claude/bin/launch.py:661-675` | The two places that print rules | read |
| `launch.py` reaches `verification.py` through `stage.py` already | `.claude/bin/stage.py:23` | `from verification import quality_limits_text` in `launch.py` adds no cycle | read |
| The stop gate also calls `attribute`, for a package's own failing tests | `.claude/bin/stage.py:308-312` | Unchanged: it keeps the default (criteria on) | read |
| Tests of `attribute` | `.claude/bin/test_agentic.py:524-563` | They call it with two arguments: they stay green. That file is 3 lines from its quality allowance (1,876 of 1,879): new cases go in a new file, not there | read |
| `agentic.py` imports `launch` when it starts, so every command, the hook included, fails if `launch.py` imports a name that does not exist yet | `.claude/bin/agentic.py:100-110` | Why WP-02 comes after WP-01 | read |
| Tests that read the plan's rules text | `.claude/bin/test_launcher.py:213-230` | Their temporary repo has no quality baseline: the text is unchanged there | read |
| `/implement` presents failed verifications and their suspects | `.claude/commands/implement.md:59-73` | The bullet that gains `zone_suspects` | read |
| The release pattern for a fix: the notes, the version, and the version the current acceptance file pins | `.claude/bin/upgrade.py:156-170`, `.claude/bin/test_acceptance_v220.py:250-256` | As 2.18.1 did | read |

What must not change: the engines, the conformance scenarios, attribution outside the quality phase, the plan's other keys, the text of a project without a quality baseline.

## 5. Data model

`verify`'s output gains one key, always present:

```python
"zone_suspects": {  # {} when the quality phase passes or names no file of those zones
    "AT": {"phases": ["quality"], "files": ["acceptance/test_ac_001_money.py"]},
    "QA": {"phases": ["quality"], "files": ["qa/test_qa.py"]},
}
```

`files` are the zone's files the violations name, sorted, as the violation prints them (repo-relative).

The limits' sentence, with the values of `limits_of`. It starts and ends with a newline character (written `\n` below), which are part of it:

```
\nQuality limits, checked on every file you write, tests included: no line over {line_chars} characters; no new file over {file_lines} lines; no new function over {function_lines} lines ({test_function_lines} in a test) or nested deeper than {nesting}. What is already over a limit has its own allowance in .claude/quality-baseline.json.\n
```

## 6. Contracts between modules

**`verification.py`:**

```python
def attribute(manifest, lines, by_criteria=True)
    """As today. by_criteria=False: only a file path of the package makes it a suspect; an AC-NNN in the text
    does not, and "acs" is [] in every entry."""

def zone_files(manifest, lines)
    """{"AT": [paths], "QA": [paths]}, without the empty ones: the files of the acceptance zone and of QA's zone
    that these lines name. A path is taken from a line of the quality phase: the text after "FAIL file " or
    "FAIL function " up to the first " exceeds" (and, for a function, up to "::"). Sorted, each once."""

def quality_limits_text()
    """The sentence of section 5 for this project's baseline; "" without a baseline or with an unreadable one."""
```

- In `verify`, the phase named `quality` is attributed with `by_criteria=False`; every other phase as today. Only when the quality phase's status is `regression` or `fails` (a `pre-existing failure` does not count), `zone_files` of the lines `verify` attributes for it (its scan, already reduced to the new failures in a regression) gives `zone_suspects`, each zone with `"phases": ["quality"]`. The key is in the printed JSON in every case, `{}` otherwise. The loop that builds `suspects` removes each phase's scan (`ph.pop("_scan", [])`): the zones are read from the quality phase's scan inside that loop, never after it.
- A file under a zone is told by `owns(zone_path, file)` semantics: equal, or inside a path that ends in `/` (`core.owns`).

**`launch.py`:**

- `pipeline_plan`: `printed = rules_text(manifest, native=injected_by_claude_code()) + quality_limits_text()`, used for `rules_text` and its checksum.
- `render_prompt`: `rules = "" if silent else rules_text(manifest) + quality_limits_text()`. The guard stays where it is: an implementer the spec keeps the rules away from gets no limits either.
- A project with a baseline and no rule files gets the limits alone. That is intended: its agents still write code under those limits. The engines then report `rules` as `printed`, which is true of what the prompt carries.

**`/implement`:** when the saved result's `verification.zone_suspects` is not empty, the Verification part says that the quality failure is in the acceptance tests (`AT`) or QA's tests (`QA`), names the files, and says no package can fix them: the person fixes those files or relaunches that agent.

## 7. Conventions

- English everywhere; usage errors keep the `Uso:` prefix (design 0016).
- No type annotations in signatures (Python 3.9), as in the rest of `.claude/bin`. This overrides the python rules' "type annotations on every public signature": it is the existing code's style, not a finding.
- Every `open` and `read_text` names `encoding="utf-8"`.
- This repository's own quality phase measures `.claude/bin`, the acceptance tests of this fix included: no line over 120 characters, no new function over 60 lines (100 in a test), no new file over 800 lines.
- The guides do not cite flow version numbers. Commit format `type: summary`; the flow history is regenerated as the last commit.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · A quality failure on an acceptance file does not name a package
  - Scenario: a temporary repo whose manifest gives `WP-01` the file `src/a.py` and the criterion `AC-001`, with a quality baseline created by `agentic.py quality --init`. The manifest has no `verify` commands and its acceptance command passes (a script that exits 0), so `quality` is the only phase that can fail; the tests' `Repo` helper (`.claude/bin/test_agentic.py:45-76`) builds the repo from a manifest the test declares (one package, `WP-01`, with `"acs": ["AC-001"]`, and `"acceptance": {"files": ["acceptance/"], "command": "<python> acc.py"}`), and the test writes `acc.py` with `raise SystemExit(0)`. After the baseline, `acceptance/test_ac_001_money.py` is written with one line of 130 characters.
  - Action: `agentic.py verify`.
  - Expected: exit 3; `blocking` contains `quality`; `suspects` is `{}`; `zone_suspects` is `{"AT": {"phases": ["quality"], "files": ["acceptance/test_ac_001_money.py"]}}`. Today `suspects` names `WP-01`: this is the bug.
  - Must not: `WP-01` in `suspects`.
  - Check: `test_quality_limits.py`
  - WP: WP-01

- AC-002 · The package that owns the file is still the suspect, and QA's zone is named too
  - Scenario: as AC-001, plus `src/a.py` with one line of 130 characters and `qa/test_qa.py` with one.
  - Action: `agentic.py verify`.
  - Expected: `suspects` is `{"WP-01": {"phases": ["quality"], "files": ["src/a.py"], "acs": []}}`; `zone_suspects` names `AT` with the acceptance file and `QA` with `qa/test_qa.py`.
  - Must not: a file of one zone listed under another.
  - Check: `test_quality_limits.py`
  - WP: WP-01

- AC-003 · Outside the quality phase nothing changes
  - Scenario: the manifest of AC-001.
  - Action: `verification.attribute(manifest, ["test_ac_001_total FAILED"])`, the same with `by_criteria=False`, and `agentic.py verify` in a repo whose quality phase passes.
  - Expected: the first names `WP-01` with `acs` `["AC-001"]`; the second is `{}`; `verify`'s output has `"zone_suspects": {}`.
  - Must not: a changed result for any existing call with two arguments.
  - Check: `test_quality_limits.py`
  - WP: WP-01

- AC-004 · The limits are printed where the rules are
  - Scenario: a temporary repo with the python stack's rules installed and a quality baseline whose `limits` set `line_chars` to 100.
  - Action: `agentic.py pipeline-plan`; `agentic.py run-wave 1` with the tests' fake `claude`; then both again after deleting the baseline.
  - Expected: with the baseline, `rules_text` ends with the sentence of section 5 carrying `no line over 100 characters`, `no new file over 800 lines` and `no new function over 60 lines (100 in a test) or nested deeper than 4`; `rules_sum` is the checksum of the whole text; the implementer's prompt of `run-wave` ends with the same sentence. Without the baseline neither text contains "Quality limits".
  - Must not: the sentence before the rules, or twice.
  - Check: `test_quality_limits.py`
  - WP: WP-02

- AC-005 · /implement presents the zone
  - Scenario: `.claude/commands/implement.md`.
  - Action: read it.
  - Expected: one line of it contains all of `` `zone_suspects` ``, `` `AT` ``, `` `QA` `` and the literal phrase `no package can fix them`.
  - Must not: that line contains "fix cycle".
  - Check: `test_quality_limits.py`
  - WP: WP-02

- AC-006 · Release 2.20.1
  - Scenario: this repository.
  - Action: read `plugin.json`, `upgrade.NOTES`, the guide.
  - Expected: version `2.20.1`; `NOTES["2.20.1"]` has at least two notes: one contains `quality limits` (lower case), another contains `zone_suspects`; `docs/how-it-works.md` contains `zone_suspects`.
  - Must not: `2.20.1` anywhere in `docs/how-it-works.md`.
  - Check: `test_quality_limits.py`
  - WP: WP-03

### Work packages

#### WP-01 · Attribution of the quality phase, and the limits' sentence
- Wave 1.
- Files: `.claude/bin/verification.py`, `.claude/bin/test_zone_attribution.py`.
- Implements the `verification.py` contracts of section 6.
- ACs: AC-001, AC-002, AC-003.
- **Patterns to mirror:** `.claude/bin/verification.py:249-266` (how a path is matched whole); `.claude/bin/verification.py:320-336` (how `suspects` is built and printed); `.claude/bin/test_agentic.py:524-563` (the attribution tests).
- **Gotchas:**
  - `verification.py` is 336 lines and `verify` is 49: both under the quality ratchet (a function of at most 60 lines). Build `zone_suspects` in a helper, not inside `verify`.
  - Do not add to `test_agentic.py`: it is 3 lines from its quality allowance. The unit cases go in `test_zone_attribution.py`.
  - A detail line (`  <key> <metric>: now N, allowed M`) repeats the path: take paths from the `FAIL` lines only.
  - `quality_limits_text` must return `""` for `{"unreadable": True}`.
  - `test_lean.py`'s budget check is red until WP-03 raises the budget: expected in waves 1 and 2, so the whole `.claude/bin` suite is red there for that one test.
- **Exact imports and APIs:** `at_entity`, `qa_entity`, `owns` from `core`; `quality_module().limits_of`, `quality_state()` in the same file.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_zone_attribution.py"`; `python3 -m unittest discover -s .claude/bin -p "test_agentic.py"`; `python3 -m unittest discover -s .claude/bin -p "test_quality.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · The plan, the one-off prompts and /implement
- Wave 2: `launch.py` imports `quality_limits_text`, and `agentic.py` imports `launch` on every command, so the function must exist first.
- Files: `.claude/bin/launch.py`, `.claude/commands/implement.md`, `.claude/bin/test_launcher.py`.
- Consumes `quality_limits_text` by implementation (WP-01).
- ACs: AC-004, AC-005.
- **Patterns to mirror:** `.claude/bin/launch.py:302-307` and `.claude/bin/launch.py:661-675` (the two places); `.claude/commands/implement.md:59-73` (one bullet per part).
- **Gotchas:** the checksum is of the text actually put in the plan, limits included, or both engines fall back to naming the paths. `launch.py` and `implement.md` are budgeted: one import, two call sites, one sentence. `test_lean.py`'s budget check is red until WP-03.
- **Exact imports and APIs:** `from verification import quality_limits_text` in `launch.py`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_launcher.py"`; `python3 -m unittest discover -s .claude/bin -p "test_pipeline.py"`; `python3 -m unittest discover -s .claude/bin -p "test_definitions.py"`; `node .claude/bin/test_workflow.mjs`.

#### WP-03 · Notes and release
- Wave 3.
- Files: `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_acceptance_v220.py`, `docs/how-it-works.md`.
- ACs: AC-006.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-170`; `.claude/bin/test_acceptance_v220.py:250-256` (the version it pins); `docs/how-it-works.md:389-392` (the glossary's line on failed verifications).
- **Gotchas:** `NOTES["2.20.1"]` goes right above `"2.20.0"` in the dictionary. A fix release keeps the current acceptance file and changes only the version it pins, as 2.18.1 did. `flow-budget.json`: raise only what is exceeded, with its why. `.claude/flow-history.json` is regenerated by the maintainer as the last commit.
- **WP validation:** the five commands of section 3 and `python3 -m unittest discover -s acceptance`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_quality_limits.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_quality_limits.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/verification.py", ".claude/bin/test_zone_attribution.py"],
     "acs": ["AC-001", "AC-002", "AC-003"], "mirror": [".claude/bin/verification.py:249-266", ".claude/bin/verification.py:320-336", ".claude/bin/test_agentic.py:524-563"]},
    {"id": "WP-02", "wave": 2, "depends_on": ["WP-01"], "files": [".claude/bin/launch.py", ".claude/commands/implement.md", ".claude/bin/test_launcher.py"],
     "acs": ["AC-004", "AC-005"], "mirror": [".claude/bin/launch.py:302-307", ".claude/bin/launch.py:661-675", ".claude/commands/implement.md:59-73"]},
    {"id": "WP-03", "wave": 3, "depends_on": ["WP-01", "WP-02"], "files": [".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_acceptance_v220.py", "docs/how-it-works.md"],
     "acs": ["AC-006"], "mirror": [".claude/bin/upgrade.py:156-170", ".claude/bin/test_acceptance_v220.py:250-256", "docs/how-it-works.md:389-392"]}
  ]
}
```

## 9. Test strategy

- **Acceptance** (`test_quality_limits.py`, written first and red): AC-001 to AC-003 run `verify` in temporary repos with a real quality baseline; AC-004 reads the plan and a fallback prompt; AC-005 and AC-006 read files. AC-001 must fail today by naming `WP-01`: it reproduces the bug. Nothing is spent.
- **Unit:** the attribution cases go in `test_zone_attribution.py`.
- **Teeth:** each behaviour is broken once by hand (criteria left on for quality, the zone left out, the limits missing from the checksum) and the acceptance test must fail.
- **By hand, before the pull request:** `acceptance/`, `qa/`, the installed-project job, and `agentic.py flow-history` as the last commit with its `--check`.

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| The limits travel in the rules text of the plan | A line in every brief; a new placeholder in each prompt | The rules text already reaches exactly the agents that write code or judge it by the rules, in both engines and in the one-off commands: no engine line, no scenario, one sentence |
| The values come from the project's baseline | The defaults, hard-coded | A project may set its own limits; printing others would mislead |
| No baseline, no sentence | Print the defaults anyway | Without a baseline the quality phase does not run: a limit nobody checks is noise |
| The quality phase is attributed by path only | Keep the criteria route everywhere | A quality violation names the file at fault. A criterion's number in a test's name says which package must make the test pass, not who wrote too long a line; the package cannot edit that file |
| The owning zone is reported in `zone_suspects`, and the run stops as it does today when no package owns the failure | Send the test-author or QA to a fix cycle | Left out by the user for now: a new path in both engines, with the workflow script 30 lines from its recorded limit. The run stops at once instead of spending two fix cycles, and says whose files they are |
| A new key beside `suspects` | Add `AT` and `QA` to `suspects` | The engines read `suspects` and skip what is not a package; a different key cannot be mistaken for a package by an older reader |
| Three waves of one package each | Two packages in wave 1 | `launch.py` cannot import a function that does not exist yet without breaking every `agentic.py` command, the hook included; and the release comes last. The packages are small, so the chain costs little |
| A fix release, 2.20.1, that keeps the current acceptance file | A minor release with its own acceptance file | It repairs behaviour the flow already claimed (verification names who owns a failure); as 2.18.1 did, its tests live in a named file |
| How the packages of the 2.11.0 runs came to be named is not reproduced | Reproduce on 2.11.0 | Those runs are the user's report. What is reproduced is the route that exists today: a criterion's number in the name of an acceptance file or function |
| Written with Fable 5.2 | Pause to switch model | The user chose it at the model gate |

## 11. Risks and open questions

- **A test-author that still breaks a limit stops the run at verification.** That is better than two wasted fix cycles, but review, QA and documentation still do not start until a person fixes the file or relaunches the agent. Issue 134's second proposal covers it.
- **The sentence costs tokens on every call that prints rules:** about 60 words, not measured in tokens.
- **A mixed failure** (a package's file and an acceptance file both over a limit) sends the package to fix its own file, and the next verification stops naming the zone: one fix cycle is spent, on a real defect of that package.
- **Other languages' test files** follow the same rule: the limits come from one baseline and apply to every file the quality phase measures.
