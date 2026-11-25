# Architecture: the rules travel in the briefs, and a wave blocked by the acceptance tests is repaired once (agentic-flow 2.22.0)
Type: feature · Size: standard

## 1. Goal

A field report from a PowerShell project (native `/implement`, Windows PowerShell 5.1) ended `REVIEW` at wave 2. The acceptance tests wrapped a `List[object]` in `@(...)`, which throws on 5.1. The tests died before testing the code, and two packages ended `BLOCKED` because they cannot edit the acceptance zone. The PowerShell rules have documented that exact trap since 2.15.0, but they did not reach the test-author: the workflow result says `rules: "pointed"`. In 4 of the 5 runs of that cycle, the full text reached no agent. In the native engine the rules text (about 8.5 KB for common plus PowerShell) travels inside `pipeline-plan`'s output, copied by hand by the gatekeeper (a Haiku agent). When the copy is not exact, the checksum fails and the agents get only the rule paths, which they do not read.

This release does two things:
1. The agents that write code (the test-author and each package) get the rules inside their brief. `agentic.py briefs` writes the brief from disk, and reading it is already their first step.
2. When a wave is blocked only because the acceptance tests themselves fail, the flow relaunches the test-author with the blockers, then relaunches the blocked packages. This happens once per run, in both engines.

## 2. Scope

### Included

- **Rules in the briefs.**
  - `agentic.py briefs` appends the rules (common and stack languages, full text) and the quality-limits sentence to `AT.md` and to every package's brief.
  - The prompts of the test-author and of the packages stop carrying the rules, in both engines.
  - The judges (standards reviewer, QA, re-review on the standards axis) keep today's path: printed when the checksum holds, the paths otherwise.
- **Acceptance repair.**
  - An implementer's `BLOCKED` report may say `blocker.in: "acceptance"`: its package is done, and the acceptance tests themselves fail.
  - When an implement wave fails to close only because of such reports, the flow runs these steps:
    1. It reopens the acceptance stage.
    2. It runs the test-author with the blockers.
    3. It closes the acceptance stage.
    4. It reopens the wave and relaunches only the blocked packages.
    5. It closes the wave again.
  - Once per run, within the agent-call budget. The run records `acceptance_repairs`.
- **Docs and release 2.22.0.** The guide, `/implement`'s presentation, the implementer's and test-author's definitions, the notes, the budget, and one acceptance file. The 2.21.x acceptance tests move to a named file.

### Excluded (non-goals)

- A PowerShell-specific grep of the acceptance tests (the report's proposal 1).
- Telling a helper's failure from missing code in the red run (proposal 2).
- A repair in a fix wave: only implement waves are repaired.
- A second test-audit after the repair.
- A reliable path for the judges' rules (section 11).
- Making the gatekeeper's copy of `pipeline-plan` reliable.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`
- Bench: `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/bin/launch.py                    WP-01  write_briefs appends the rules; render_prompt leaves writers' prompts bare
.claude/bin/test_brief_rules.py          WP-01  new: unit cases
.claude/bin/test_quality_limits.py       WP-01  the limits sentence is read from the brief, not the prompt
.claude/bin/pipeline.py                  WP-02  writers' prompts without rules; acceptance repair
.claude/bin/pipeline_parts.py            WP-02  new: pipeline.py's module-level helpers, moved to make room
.claude/workflows/agentic-implement.js   WP-02  the same, in the native engine
.claude/workflows/pipeline-spec.json     WP-02  prompts without {rules}; test_author_repair; blocker.in
.claude/bin/conformance.json             WP-02  the rules scenarios updated; repair scenarios
.claude/bin/test_pipeline.py             WP-02  summary key and EngineTests
.claude/bin/test_workflow.mjs            WP-02  summary key; the rules test
.claude/bin/test_qa_recheck.py           WP-02  writers' prompts without the rules, judges' with them
docs/how-it-works.md                     WP-03  rules and the acceptance repair
.claude/commands/implement.md            WP-03  presents acceptance_repairs
.claude/agents/implementer.md            WP-03  when to say blocker.in "acceptance"
.claude/agents/test-author.md            WP-03  the rules are at the end of the brief
.claude-plugin/plugin.json               WP-03  2.22.0
.claude/bin/upgrade.py                   WP-03  NOTES["2.22.0"]
.claude/flow-budget.json                 WP-03
.claude/bin/test_zone_stop_gate.py       WP-03  new: the classes of test_acceptance_v221.py without its ReleaseTests
.claude/bin/test_acceptance_v221.py      WP-03  deleted
.claude/bin/test_failure_evidence.py     WP-03  its ReleaseTests stop pinning the plugin version
.claude/bin/test_fix_routing.py          WP-03  the same
.claude/bin/test_native_usage.py         WP-03  the fallback's rules are read from the brief, not the prompt
.claude/bin/test_acceptance_v222.py      AT
.claude/flow-history.json                by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| The native engine gets the plan through the gatekeeper, a Haiku agent that copies a command's output by hand into a structured answer | `.claude/workflows/agentic-implement.js:103-105`, `.claude/agents/gatekeeper.md:1-20` | Why a long text is not reliable on that path | read |
| The engine prints the rules only when `textSum(plan.rules_text) === plan.rules_sum`; otherwise `RULES` is the paths sentence and `run.rules` is `pointed`. `IMPLEMENTER_RULES` is `RULES` unless `plan.implementer_rules === false` | `.claude/workflows/agentic-implement.js:536-541` | Stays for the judges | read |
| The fallback engine's equivalents: `self.rules`, `self.impl_rules` | `.claude/bin/pipeline.py:175-176`, `.claude/bin/pipeline.py:343` | Same | read |
| Where the writers get the rules today: test-author `prompt + RULES`, its revision, the implement/fix prompts `+ IMPLEMENTER_RULES`, the NEEDS_CONTEXT retry | `.claude/workflows/agentic-implement.js:386-411`, `.claude/workflows/agentic-implement.js:420-436`, `.claude/workflows/agentic-implement.js:716-746`, `.claude/bin/pipeline.py:371-418`, `.claude/bin/pipeline.py:419-447`, `.claude/bin/pipeline.py:461-478` | Each one drops the rules | read |
| The prompt templates carry `{rules}`: `implement`, `fix`, `test_author`, `test_author_revision`, `implement_full` | `.claude/workflows/pipeline-spec.json:15-19`, `.claude/workflows/pipeline-spec.json:26` | `{rules}` leaves those five; `qa`, `standards_reviewer`, `re_review` keep it | read |
| `rule_files(manifest)` lists the installed rules (common and stack); `render_rules(paths, root)` prints them under "Rules you must follow…", each file without its frontmatter | `.claude/bin/repo_scan.py:59-77` | The brief's rules are `render_rules(rule_files(manifest), ROOT)`: always the full text, never the native pointer | read |
| `quality_limits_text()`: the limits sentence, `""` without a readable quality baseline | `.claude/bin/verification.py:323-333` | Appended after the rules in the brief | read |
| `write_briefs(manifest)` writes `.claude/state/briefs/<ID>.md` for each package and `AT` from `brief.slice_architecture` | `.claude/bin/launch.py:268-277`, `.claude/bin/brief.py:84-107` | The rules go after the slice (or after the whole document when the plan cannot be sliced) | read |
| `render_prompt` (the fallback's one-off commands) fills `{rules}` except for implementers when `implementer_rules` is false; `IMPLEMENTER_PROMPTS = ("implement", "fix", "implement_full")` | `.claude/bin/launch.py:304-308`, `.claude/bin/launch.py:42` | With `{rules}` gone from the writers' templates, the value is ignored there | read |
| `launch.py` already imports `rule_files` and `quality_limits_text` | `.claude/bin/launch.py:28-29` | Add `render_rules` to the `repo_scan` import | read |
| The implementer's report: `status` in `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, `BLOCKED`; `blocker` `{missing, section, options}` or null | `.claude/workflows/pipeline-spec.json:167-200`, `.claude/agents/implementer.md:47`, `.claude/agents/implementer.md:70` | `blocker` gains an optional `in` | read |
| The test-author's report: `status` `DONE` or `BLOCKER` | `.claude/workflows/agentic-implement.js:35` | The repair reads it as today | read |
| `launchWave` / `launch_wave` run a wave's packages, store each report in `run.work_packages[wp]` and return the close command | `.claude/workflows/agentic-implement.js:386-418`, `.claude/bin/pipeline.py:419-447` | The repair calls them with the blocked packages only | read |
| `runWaves` / `run_waves`: open, launch, close (with the next open-stage in the same `seq`); a close that fails stops with "the wave ended with blockers, missing reports or writes outside ownership". A `seq` stops at its first failing step, so the next open-stage did not run | `.claude/workflows/agentic-implement.js:440-473`, `.claude/bin/pipeline.py:480-512` | The repair goes in that `!good` branch, implement waves only | read |
| A close that saw writes outside ownership prints `OUTSIDE OWNERSHIP` | `.claude/bin/stage.py:181` | Such a close is never repaired: a new snapshot would accept those writes | read |
| Wave 0: `open-stage acceptance` (`seqRetry`), the test-author, `closeSeq(['close-stage acceptance AT=<state> --expect red'])`, a revision reopens the stage | `.claude/workflows/agentic-implement.js:716-746`, `.claude/bin/pipeline.py:371-418` | The repair follows the same steps without `--expect` (the code exists by then) | read |
| The agent-call budget: `plan.max_agent_calls`, `run.agent_calls`, `budgetForCycle` | `.claude/workflows/agentic-implement.js:507-520`, `.claude/bin/pipeline.py:546-560` | The repair runs only when the rest of the run fits in what is left, counted as in section 6 | read |
| The run record's initial keys | `.claude/workflows/agentic-implement.js:249`, `.claude/bin/pipeline.py:189-191` | `acceptance_repairs: []` joins them | read |
| The conformance harness: `summarize` in both, the keys `ConformanceTests` compares | `.claude/bin/test_pipeline.py:154-170`, `.claude/bin/test_pipeline.py:216-226`, `.claude/bin/test_workflow.mjs:553-575` | `acceptance_repairs` added to both summaries and to the keys | read |
| Tests that pin the writers' prompts carrying the rules | `.claude/bin/test_pipeline.py:470-488`, `.claude/bin/test_workflow.mjs:317-330`, `.claude/bin/test_qa_recheck.py:128-130`, `.claude/bin/test_quality_limits.py:126-145`, `.claude/bin/test_native_usage.py:216-232` | To update (WP-02, WP-02, WP-02, WP-01, WP-03) | read |
| Tests that pin the version `2.21.2` | `.claude/bin/test_acceptance_v221.py:140-153`, `.claude/bin/test_failure_evidence.py:223-226`, `.claude/bin/test_fix_routing.py:263-271` | WP-03 | read |
| `pipeline.py` is at 800 lines, the file limit; its module-level helpers sit at the top | `.claude/bin/pipeline.py:25-160` | WP-02 moves them to `pipeline_parts.py` | read |
| `agentic-implement.js` has 824 lines against an allowance of 861, and 64 lines over 120 characters against an allowance of 64 | `.claude/quality-baseline.json:54-57` | No new line over 120 characters | read |

What must not change: the judges' rules, `run.rules`, `pipeline-plan`'s `rules_text`/`rules_sum`, the fix waves, wave 0, the stop gate.

## 5. Data model

The implementer's `blocker` (schema in `pipeline-spec.json`; both engines read the spec):

```json
{"missing": "string", "section": "string", "options": ["string"], "in": "design | acceptance"}
```

`in` is optional. Without it, or with `design`, the blocker is what it is today.

A brief, after the slice:

```
<the slice, or the whole architecture.md when it cannot be sliced>

Rules you must follow (common and language). They are printed here, so do not read them from disk:

--- .claude/rules/agentic/common.md ---
...
--- .claude/rules/agentic/powershell.md ---
...
Quality limits, checked on every file you write, ...   (only with a readable quality baseline)
```

A package's brief has no rules when the spec's `constants.implementer_rules` is `false`. `AT.md` always has them.

The run record gains:

```json
"acceptance_repairs": [{"wave": 2, "wps": ["WP-02", "WP-03"], "test_author": "DONE"}]
```

`test_author` holds the test-author's report status, or `null` without a report.

## 6. Contracts between modules

**`launch.py` (WP-01):**

```python
def brief_rules(manifest, ident)
    """The rules section a brief ends with: render_rules(rule_files(manifest), ROOT) + quality_limits_text(),
    or "" for a package (any ident other than "AT") when the spec's constants.implementer_rules is False."""
```

`write_briefs` writes `body + brief_rules(manifest, ident)`, where `body` is the slice (or the whole text) with its trailing newlines kept as today.

**Both engines (WP-02), equivalent in every scenario:**

- The writers' prompts no longer end with the rules. These are the `implement`, `fix`, `implement_full`, `test_author` and `test_author_revision` prompts, plus the new `test_author_repair`.
- The `implement_full` prompt names the brief: `... This time your brief is architecture.md, whole: read it and implement. The rules you must follow are at the end of {brief}. ...`.
- The `implement` and `fix` prompts add one sentence: `If your package is done and the acceptance tests themselves fail (an error inside a test or its doubles, not in your code), return BLOCKED with blocker.in "acceptance" and, in missing, each failing test, its file and its error.`
- `acceptance_blocked(wp_ids, reports)` (JS `acceptanceBlocked`) returns the sorted ids of the packages whose report is `BLOCKED` with `blocker.in === "acceptance"`. It returns them only when every other report of `wp_ids` is `DONE` or `DONE_WITH_CONCERNS`; otherwise it returns `[]`. A missing report counts as not done.
- The repair, in the `!good` branch of an implement wave, runs only when all of these hold:
  - the run has not repaired yet;
  - the close output does not contain `OUTSIDE OWNERSHIP`;
  - `acceptance_blocked` is not empty;
  - `max_agent_calls` is unset, or what is left (`max_agent_calls - run.agent_calls`) covers the rest of the run, counted as `budgetAtStart` counts it: 1 (the test-author) + the blocked packages + the packages of the later waves + 2 (reviewers) + 1 (QA) + 1 if `plan.docs`.
- The repair's steps:
  1. `seqRetry(['open-stage acceptance'])`. If it fails, the run stops `wave <N>`: `the acceptance stage could not be reopened to repair the tests`.
  2. The test-author, label `test-author (repair)`, id `AT`, with prompt `test_author_repair` rendered with `brief=brief("AT")`, `wave=N` and `blockers`:
     ```
     Repair the acceptance tests (your brief is {brief}). The code of wave {wave} is written, and these packages could not finish because the acceptance tests themselves fail, as JSON:
     {blockers}
     Fix the tests or their doubles in your zone so that they test what the criteria say. Do not weaken what a criterion checks and do not touch production code. Run the acceptance command before you report.
     ```
     `{blockers}` is `compact([{"wp": id, "missing": report.blocker.missing}])`, in the order of the blocked ids.
  3. `closeSeq(['close-stage acceptance AT=<done|blocker>'])`, without `--expect`. Push `{stage: 'acceptance repair (wave N)', ok, check}`, then append `{wave, wps, test_author}` to `acceptance_repairs`. If the test-author is not `DONE` or the close fails, the run stops `wave <N>`: `the test-author could not repair the acceptance tests`.
  4. `seqRetry(['open-stage <N>'])` (a failure stops `wave <N>`: `the stage could not be opened`), then `launchWave(N, blocked, null)` and its close command run as a `seq` of that close alone (never with the next open-stage). Its marks hold only the relaunched packages: the others' ledger states stay `done`.
  5. Push `{stage: 'wave N (after repair)', ok, check}` and add its gate denials. A close that fails stops with today's detail. A close that passes continues: the fallback calls `self.wave_done(wave)` as `run_waves` does after a good close (`.claude/bin/pipeline.py:504-505`; the native engine has no equivalent); the last wave runs `WAVE_TAIL`; otherwise the next wave opens on its own (`opened = false`).
- Without a repair, the `!good` branch stops exactly as today.

## 7. Conventions

- English everywhere; usage errors keep the `Uso:` prefix (design 0016).
- No type annotations in signatures (Python 3.9), as in the rest of `.claude/bin`. This overrides the python rules' "type annotations on every public signature": it is the existing code's style, not a finding.
- Every `open` and `read_text` names `encoding="utf-8"`.
- The two engines change together. A scenario that differs in `prompts`, `gate_calls`, `agents` or `acceptance_repairs` fails `ConformanceTests`.
- This repository's quality phase measures `.claude/bin` and `.claude/workflows`, the tests of this design included:
  - no line over 120 characters;
  - no new function over 60 lines (100 in a test), nested deeper than 4;
  - no new file over 800 lines.
- Recorded allowances this design must not exceed:
  - `agentic-implement.js`: 861 lines and 64 long lines (824 and 64 today);
  - `test_pipeline.py`: 16 long lines;
  - `pipeline.py`: 800 lines (800 today).
- The guides do not cite flow version numbers. Commit format `type: summary`; the flow history is regenerated as the last commit.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · The test-author's brief carries the language rules (reproduces the field bug)
  - Scenario: a temporary repo made with the tests' `Repo` helper (`.claude/bin/test_agentic.py:45-76`) from its default manifest with `"stack": ["powershell"]`. The library is copied into `.claude/rules-library/` and `agentic.py rules-sync` has run. `agentic.py quality --init` has run.
  - Action: `agentic.py briefs`.
  - Expected: `.claude/state/briefs/AT.md` contains:
    - `--- .claude/rules/agentic/common.md ---`;
    - `--- .claude/rules/agentic/powershell.md ---`;
    - `argument types do not match`;
    - `Quality limits, checked on every file you write`.

    `WP-01.md` contains the same four. Before this release, `AT.md` contains none of them.
  - Must not: a brief that names the rule paths without their text; frontmatter (`paths:`) inside the brief.
  - Check: `test_acceptance_v222.py`
  - WP: WP-01

- AC-002 · The packages' briefs follow implementer_rules, and an unsliceable plan still ends with the rules
  - Scenario: as AC-001.
  - Action:
    - (a) the spec's `constants.implementer_rules` set to `false` (the test writes its own copy of `pipeline-spec.json` into the repo's `.claude/workflows/`), then `agentic.py briefs`;
    - (b) with the spec restored, a manifest whose packages have no `acs` (the plan cannot be sliced), then `agentic.py briefs`.
  - Expected:
    - (a) `AT.md` still contains `--- .claude/rules/agentic/powershell.md ---`, and `WP-01.md` contains no `Rules you must follow`;
    - (b) `WP-01.md` starts with the plan's first line and ends with the rules section.
  - Must not: the test-author left without rules by `implementer_rules`.
  - Check: `test_acceptance_v222.py`
  - WP: WP-01

- AC-003 · The writers' prompts carry no rules; the judges' do, in both engines
  - Scenario: the conformance scenarios `printed rules reach the agents`, `rules text that arrives damaged falls back to the paths` and `the implementer can be left without the rules`, as updated by WP-02.
  - Action: `test_pipeline.run_scenario(<scenario>)`, and `node .claude/bin/test_workflow.mjs --dump`.
  - Expected:
    - In every scenario no `implementer` or `test-author` prompt contains `RULE-TEXT` or `Rules you must follow`, and each names its brief (`.claude/state/briefs/`).
    - In `printed rules reach the agents`, every `standards-reviewer` and `qa` prompt contains `RULE-TEXT`.
    - In the damaged scenario, the `standards-reviewer` prompts contain `Rules you must follow (language and common): .claude/rules/agentic/common.md`.
    - The native engine's prompts equal the fallback's.
  - Must not: the judges losing the rules; the engines differing.
  - Check: `test_acceptance_v222.py`
  - WP: WP-02

- AC-004 · A wave blocked only by the acceptance tests is repaired and resumed, in both engines
  - Scenario: the conformance scenario `a wave blocked by the acceptance tests is repaired and resumed`, on the conformance plan (waves 1 and 2; WP-01 and WP-02 in wave 1, WP-03 in wave 2):
    - in wave 1, WP-01 answers `DONE` and WP-02 answers `BLOCKED` with `blocker` `{"missing": "test_ac_002 dies in its double: argument types do not match", "section": "8", "in": "acceptance"}`;
    - the gate call `close-stage 1 WP-01=done WP-02=blocker` answers exit 3 (a `gate_fail` entry matched by that prefix);
    - its relaunch answers `DONE`.
  - Action: `test_pipeline.run_scenario(<scenario>)`, and `node .claude/bin/test_workflow.mjs --dump`.
  - Expected:
    - `result` `OK`.
    - `acceptance_repairs` == `[{"wave": 1, "wps": ["WP-02"], "test_author": "DONE"}]`.
    - The prompt `test-author:test-author (repair)#1` contains `test_ac_002 dies in its double` and `.claude/state/briefs/AT.md`.
    - The gate calls contain, in this order: `open-stage acceptance`, `close-stage acceptance AT=done`, `open-stage 1`, and a `close-stage 1` that marks `WP-02=done` and no `WP-01`.
    - WP-01 is called once and WP-02 twice.
    - The native engine's `result`, `acceptance_repairs`, `gate_calls`, `agents` and `prompts` equal the fallback's.
  - Must not: WP-01 relaunched; `--expect red` on the repair's close; the engines differing.
  - Check: `test_acceptance_v222.py`
  - WP: WP-02

- AC-005 · No repair when the wave is not blocked only by the acceptance tests, or twice
  - Scenario: conformance scenarios, one per case:
    - (a) `a design blocker beside an acceptance blocker stops as before`: WP-01 is `BLOCKED` without `in`, WP-02 is `BLOCKED` with `in: "acceptance"`;
    - (b) `writes outside ownership are never repaired`: as AC-004, but the failing `close-stage 1` output contains `OUTSIDE OWNERSHIP`;
    - (c) `the acceptance repair runs once per run`: wave 1 is repaired as in AC-004, then WP-03 in wave 2 is `BLOCKED` with `in: "acceptance"` and `close-stage 2` fails;
    - (d) `a test-author that cannot repair stops the run`: as AC-004, with the repair's test-author answering `BLOCKER`.
  - Action: `test_pipeline.run_scenario(<scenario>)`, and `node .claude/bin/test_workflow.mjs --dump`.
  - Expected:
    - (a) and (b): `result` `REVIEW`, `failed_stage` `wave 1`, `detail` `the wave ended with blockers, missing reports or writes outside ownership`, no `test-author (repair)` call, `acceptance_repairs` `[]`.
    - (c): `failed_stage` `wave 2`, the same detail, and exactly one `test-author (repair)` call.
    - (d): `failed_stage` `wave 1`, `detail` `the test-author could not repair the acceptance tests`, `acceptance_repairs` `[{"wave": 1, "wps": ["WP-02"], "test_author": "BLOCKER"}]`, WP-02 called once.
    - Both engines agree in each case.
  - Must not: a repair that relaunches a package after the test-author failed; a second repair.
  - Check: `test_acceptance_v222.py`
  - WP: WP-02

- AC-006 · The budget and the fix waves are respected
  - Scenario: conformance scenarios:
    - (a) `a repair that does not fit the budget stops as before`: as AC-004, with `max_agent_calls` 9. The start check needs 8 (2 for wave 0, 3 packages, 2 reviewers, QA); when wave 1 closes 4 calls are spent, 5 are left, and the repair needs 6 (test-author, WP-02, WP-03, 2 reviewers, QA);
    - (b) `a fix wave blocked by the acceptance tests is not repaired`: verification fails, WP-02's fix answers `BLOCKED` with `in: "acceptance"`, and `close-stage 1 WP-02=blocker` fails.
  - Action: `test_pipeline.run_scenario(<scenario>)`, and `node .claude/bin/test_workflow.mjs --dump`.
  - Expected:
    - (a): `failed_stage` `wave 1`, today's detail, no `test-author (repair)` call.
    - (b): `failed_stage` `fix wave 1`, detail `the fix ended with blockers or writes outside ownership`, no `test-author (repair)` call.
    - Both engines agree.
  - Must not: a repair that exceeds `max_agent_calls`; a repair in a fix wave.
  - Check: `test_acceptance_v222.py`
  - WP: WP-02

- AC-007 · The spec and the definitions say how to ask for a repair
  - Scenario: this repository.
  - Action: read `pipeline-spec.json`, `.claude/agents/implementer.md`, `.claude/agents/test-author.md`, `.claude/commands/implement.md`.
  - Expected:
    - The `implementer` schema's `blocker.properties.in` has `enum` `["design", "acceptance"]`.
    - The prompts `implement` and `fix` contain `blocker.in "acceptance"`.
    - None of `implement`, `fix`, `implement_full`, `test_author`, `test_author_revision`, `test_author_repair` contains `{rules}`; `test_author_repair` contains `{brief}`, `{wave}` and `{blockers}`.
    - `implementer.md` contains `"acceptance"` on the line that describes `blocker`.
    - `test-author.md` contains `end of your brief`.
    - `implement.md` has exactly one line containing `` `acceptance_repairs` ``.
  - Must not: `{rules}` left in a writer's prompt.
  - Check: `test_acceptance_v222.py`
  - WP: WP-02 (spec), WP-03 (definitions)

- AC-008 · Docs and release 2.22.0
  - Scenario: this repository.
  - Action: read `plugin.json`, `upgrade.NOTES`, `docs/how-it-works.md`, the test files.
  - Expected:
    - Version `2.22.0`.
    - `NOTES["2.22.0"]` is the key right above `"2.21.2"`, with one note containing `brief` and one containing `acceptance_repairs`.
    - The guide contains `acceptance_repairs` and `end of their brief`, and does not contain `2.22.0`.
    - The only `test_acceptance*.py` is `test_acceptance_v222.py`.
    - `test_zone_stop_gate.py` holds the classes `TestAuthorGateTests`, `QaGateTests`, `FailOpenTests` and `PackageGateTests`.
    - No test file other than `test_acceptance_v222.py` has a line that contains both `version` and `"2.21.2"` or both `version` and `"2.22.0"`. No test reads `test_acceptance_v221.py`.
  - Must not: `2.22.0` in `docs/how-it-works.md`.
  - Check: `test_acceptance_v222.py`
  - WP: WP-03

### Work packages

#### WP-01 · The rules in the briefs
- Wave 1.
- Files: `.claude/bin/launch.py`, `.claude/bin/test_brief_rules.py`, `.claude/bin/test_quality_limits.py`.
- Implements `brief_rules` and the change to `write_briefs` (section 6).
- ACs: AC-001, AC-002.
- **Patterns to mirror:**
  - `.claude/bin/launch.py:268-277`: `write_briefs`.
  - `.claude/bin/launch.py:304-308`: how `render_prompt` reads `constants.implementer_rules`.
  - `.claude/bin/repo_scan.py:59-77`: `rule_files`, `render_rules`.
  - `.claude/bin/test_quality_limits.py:101-145`: a repo with rules installed and a quality baseline.
- **Gotchas:**
  - Use `render_rules(rule_files(manifest), ROOT)`, never `rules_text(manifest, native=...)`: the brief is read from disk, so the native pointer does not apply.
  - `test_quality_limits.py:126-139` asserts the implementer's prompt ends with the limits sentence. Replace that with the same assertion on `.claude/state/briefs/WP-01.md` (after `agentic.py briefs`), and do not assert anything about the prompt: it comes from the live `pipeline-spec.json`, which WP-02 changes in the same wave (AC-003 covers the prompt). Its assertions on `plan["rules_text"]` stay.
  - `render_prompt` needs no change: the writers' templates lose `{rules}` in WP-02, and `render` ignores extra values. Leave it, and do not add a second rules path.
  - `test_acceptance_v222.py`'s other ACs are red until WP-02 and WP-03: expected in wave 1. So are `test_acceptance_v221.py`'s "the only acceptance file" and `test_fix_routing.py`'s check of it, from wave 0 until WP-03, and `test_native_usage.py:216-232` from WP-02 until WP-03.
- **Exact imports and APIs:** `from repo_scan import injected_by_claude_code, render_rules, rule_files, rules_text`; `load_spec()` is defined in `launch.py` itself (`.claude/bin/launch.py:188`).
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_brief_rules.py"`; `python3 -m unittest discover -s .claude/bin -p "test_quality_limits.py"`; `python3 -m unittest discover -s .claude/bin -p "test_launcher.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · Both engines: bare writers' prompts and the acceptance repair
- Wave 1. It consumes WP-01 by signature only: its scenarios never run `briefs`.
- Files: `.claude/bin/pipeline.py`, `.claude/bin/pipeline_parts.py`, `.claude/workflows/agentic-implement.js`, `.claude/workflows/pipeline-spec.json`, `.claude/bin/conformance.json`, `.claude/bin/test_pipeline.py`, `.claude/bin/test_workflow.mjs`, `.claude/bin/test_qa_recheck.py`.
- Implements section 6's engine contracts; the scenarios named in AC-003 to AC-006.
- ACs: AC-003, AC-004, AC-005, AC-006, AC-007 (the spec's part).
- **Patterns to mirror:**
  - `.claude/workflows/agentic-implement.js:716-746`: open, test-author, close, then reopen.
  - `.claude/workflows/agentic-implement.js:440-473`: `runWaves`.
  - `.claude/bin/pipeline.py:480-512`: `run_waves`.
  - `.claude/workflows/agentic-implement.js:507-520`: the budget arithmetic.
  - `.claude/bin/test_pipeline.py:470-488`: the rules scenarios' assertions.
- **Gotchas:**
  - First move `pipeline.py`'s module-level helpers (lines 25-160: `lines_json` to `rules_of`, with their constants) to `pipeline_parts.py`. Import them back by name in `pipeline.py`, so `pipeline.render`, `pipeline.gate_line` and the rest still resolve for `launch.py` and the tests. `rules_of` uses `text_sum`: `pipeline_parts.py` imports it from `findings` itself. Run the whole suite before adding anything.
  - The workflow keeps its own copies of the spec's schemas, prompts and constants (`.claude/workflows/pipeline-spec.json:2`); `test_workflow.mjs` fails when they differ. Change both: `blocker.in` in `REPORT_SCHEMA`, and every prompt.
  - Write the repair as one function in each engine (`repair_acceptance` / `repairAcceptance`), called from the `!good` branch. `runWaves` and `run_waves` must stay within 60 lines.
  - `agentic-implement.js` can grow by 37 lines at most and add no line over 120 characters: split long template strings with `+`.
  - The relaunched packages get the plain `implement` prompt; `contextGiven` / `context_given` still apply.
  - A conformance scenario declares the repair through the existing `implementer`, `test_author` and `gate_fail` entries. `implementer` already takes a list of answers per call (`.claude/bin/test_pipeline.py:111-115`, `.claude/bin/test_workflow.mjs:76-80`). `test_author` takes one answer today (`.claude/bin/test_pipeline.py:103`, `.claude/bin/test_workflow.mjs:69`): give it a list form (one answer per call, the last repeated) in both harnesses the same way, for AC-005(d) (`DONE` in wave 0, then `BLOCKER`).
  - `test_qa_recheck.py:128-130` asserts every `implementer` and `test-author` prompt contains `RULE-TEXT`: it now asserts none does, and keeps `standards-reviewer` and `qa`.
  - Lines 64, 73 and 78 of `pipeline.py` are over 120 characters and move to `pipeline_parts.py`, a new file with no allowance: wrap them.
  - `ConformanceTests`' keys (`.claude/bin/test_pipeline.py:221-223`) and both `summarize` functions gain `acceptance_repairs`.
  - `test_workflow.mjs:317-330` asserts that every writer's prompt names the rule paths: it now asserts the opposite for `implementer` and `test-author`, and keeps the judges.
- **Exact imports and APIs:** none new. `closeSeq`/`close_seq` and `seqRetry`/`seq_retry` exist.
- **WP validation:** `node .claude/bin/test_workflow.mjs`; `python3 -m unittest discover -s .claude/bin -p "test_pipeline.py"`; `python3 -m unittest discover -s .claude/bin -p "test_launcher.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-03 · Definitions, docs, notes and release 2.22.0
- Wave 2: it moves the previous acceptance file and raises the budget after the code.
- Files: `docs/how-it-works.md`, `.claude/commands/implement.md`, `.claude/agents/implementer.md`, `.claude/agents/test-author.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_zone_stop_gate.py`, `.claude/bin/test_acceptance_v221.py`, `.claude/bin/test_failure_evidence.py`, `.claude/bin/test_fix_routing.py`, `.claude/bin/test_native_usage.py`.
- ACs: AC-007 (the definitions' part), AC-008.
- **Patterns to mirror:**
  - `.claude/bin/upgrade.py:156-170`: the notes.
  - `.claude/bin/test_native_usage.py:1-8`: the header of a file of moved tests.
  - `.claude/agents/implementer.md:70`: the line on `blocker`.
  - `.claude/commands/implement.md:71`: a presentation line.
- **Gotchas:**
  - Move the four classes of `test_acceptance_v221.py` with their helpers and constants to `test_zone_stop_gate.py`. Drop its `ReleaseTests`, and delete the file.
  - In `test_failure_evidence.py`, remove line 225 (the plugin's version) and line 241 (it reads `test_acceptance_v221.py`). In `test_fix_routing.py`, remove line 264 (the version) and lines 271-272 (they read `test_acceptance_v221.py` and look for `"2.21.2"` in `test_failure_evidence.py`). Their notes and docs checks stay, `NOTES["2.21.2"]` included.
  - `NOTES["2.22.0"]` goes right above `"2.21.2"`.
  - `implementer.md:24` says "the rules printed in your prompt": it becomes "the rules at the end of your brief". `test-author.md` says the same where it names its brief.
  - `test_native_usage.py:216-232` asserts the fallback's first implementer prompt holds the whole rules: it asserts them on `.claude/state/briefs/WP-01.md` of that project instead, and their absence from the prompt.
  - `test_definitions.py:445` asserts `plugin.json`'s version is the newest note: raise both together.
  - `flow-budget.json`: raise only what is exceeded, with its why.
  - `.claude/flow-history.json` is regenerated by the maintainer as the last commit, not by this package.
- **WP validation:** the five commands of section 3 and `python3 -m unittest discover -s acceptance`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)", "Bash(python3 .claude/bin/agentic.py quality)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v222.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v222.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/launch.py", ".claude/bin/test_brief_rules.py", ".claude/bin/test_quality_limits.py"],
     "acs": ["AC-001", "AC-002"], "mirror": [".claude/bin/launch.py:268-277", ".claude/bin/launch.py:304-308", ".claude/bin/repo_scan.py:59-77", ".claude/bin/test_quality_limits.py:101-145"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/pipeline.py", ".claude/bin/pipeline_parts.py", ".claude/workflows/agentic-implement.js", ".claude/workflows/pipeline-spec.json", ".claude/bin/conformance.json", ".claude/bin/test_pipeline.py", ".claude/bin/test_workflow.mjs", ".claude/bin/test_qa_recheck.py"],
     "acs": ["AC-003", "AC-004", "AC-005", "AC-006", "AC-007"], "mirror": [".claude/workflows/agentic-implement.js:716-746", ".claude/workflows/agentic-implement.js:440-473", ".claude/bin/pipeline.py:480-512", ".claude/bin/test_pipeline.py:470-488"]},
    {"id": "WP-03", "wave": 2, "depends_on": ["WP-01", "WP-02"], "files": ["docs/how-it-works.md", ".claude/commands/implement.md", ".claude/agents/implementer.md", ".claude/agents/test-author.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_zone_stop_gate.py", ".claude/bin/test_acceptance_v221.py", ".claude/bin/test_failure_evidence.py", ".claude/bin/test_fix_routing.py", ".claude/bin/test_native_usage.py"],
     "acs": ["AC-007", "AC-008"], "mirror": [".claude/bin/upgrade.py:156-170", ".claude/bin/test_native_usage.py:1-8", ".claude/agents/implementer.md:70", ".claude/commands/implement.md:71"]}
  ]
}
```

## 9. Test strategy

- **Acceptance** (`test_acceptance_v222.py`, written first and red):
  - AC-001 and AC-002 run `agentic.py briefs` in temporary repos.
  - AC-003 to AC-006 run the named conformance scenarios through `test_pipeline.run_scenario` and compare them with `test_workflow.mjs --dump` (skipped without `node`).
  - AC-007 and AC-008 read files.
  - Nothing is spent.
- **Unit:**
  - `test_brief_rules.py` covers `brief_rules`: with no rules installed it returns only the limits sentence (or `""` without a baseline); no quality baseline gives no limits sentence; frontmatter is stripped.
  - `test_pipeline.py`'s `EngineTests` covers `acceptance_blocked`: a missing report; `DONE_WITH_CONCERNS`; `NEEDS_CONTEXT`; a `BLOCKED` without `in`.
- **Teeth:** each behaviour is broken once by hand and an acceptance test must fail:
  - the rules left out of `AT.md`;
  - a writer's prompt with the rules again;
  - the repair relaunching the whole wave;
  - a second repair allowed;
  - the ownership check skipped;
  - one engine skipping the repair.
- **By hand, before the pull request:** the installed-project job, and `agentic.py flow-history` as the last commit with its `--check`.

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| The writers get the rules in their brief | Make the gatekeeper's relay reliable (a separate call, a retry) | Chosen with the user. The brief is written by Python from disk, and reading it is the writer's first step. A retry still depends on a Haiku agent copying 8.5 KB exactly, which the field data shows failing 4 times in 5 (`rules: "pointed"`) |
| The judges keep today's path | Give them a rules file too | Chosen with the user: the field bug was a writer's. Section 11 records the risk |
| The rules leave the writers' prompts | Print them in both places | Twice the tokens on every writer call, and two sources that can differ |
| The test-auditor reads the rules too (they are in `AT.md`) | A separate rules file for the test-author | A second file is a second read the agent may skip, which is what failed. About 8.5 KB more for the auditor, not measured in tokens |
| Brief rules are the full text, even in a native run | The native pointer for the always-loaded files | The brief is on disk; no relay limits its size |
| The package declares `blocker.in: "acceptance"` | The flow infers it from the acceptance output | Chosen with the user: deterministic. Inferring it is the report's proposal 2, excluded |
| Only the blocked packages are relaunched, once per run | The whole wave; once per wave | Chosen with the user: fewer calls; a second block in the same run is a sign for a person |
| No repair in a fix wave, and never after writes outside ownership | Repair every wave | A fix wave has its own cap and history. A new snapshot after an ownership violation would accept the stray writes |
| No `--expect red` on the repair's close | The wave 0 close | The code exists by then: the tests may pass |
| `pipeline.py`'s helpers move to `pipeline_parts.py` | Raise the file's allowance | It is at the 800-line limit; the helpers are pure functions with no state of the class |
| A minor release, 2.22.0, with its own acceptance file, and the 2.21.x tests in named files | A fix release | It adds a behaviour to both engines |
| Implementation: `agentic-implement.js`'s allowance in `.claude/quality-baseline.json` raised from 831 to 890 lines (long lines stay at 64) | Compact older code of the engine; drop the repair | Section 7 asked to stay within 861, but the repair needs about 45 lines and no line could grow past 120 characters. Chosen by the user during the implementation, as for 2.20.0 |
| Implementation: three tests the plan did not list were updated (`test_launcher.py:229`, `test_definitions.py:645-647`, `test_qa_recheck.py:172`), and `installer.py` ships `pipeline_parts.py` | Leave them red | They pinned the rules in the writers' prompts and the old wording of the agents' definitions; `test_install.py` requires every module in `INSTALL_BIN` |

## 11. Risks and open questions

- **The judges can still get only the paths.** The standards reviewer and QA keep the relayed text, and it failed 4 times in 5 in the field. A standards finding that cites a rule may be missing. Not measured how often it changes a verdict.
- **Not measured: why two of the field runs carried not even the paths.** The record of those runs was overwritten. A plan with an empty `rules` list gives `rules: "none"`; that path is unchanged.
- **A package may claim `in: "acceptance"` wrongly.** The test-author then sees the blockers, and may answer `BLOCKER` or change nothing. In the second case the relaunched package blocks again and the run stops, as today. The test-author must not weaken a criterion; there is no second audit, so that rests on its definition and on the reviewers later.
- **Field validation:** the next PowerShell run should show `rules` in `AT.md` and the repair in `acceptance_repairs`; reported by the user.

No question blocks a WP.
