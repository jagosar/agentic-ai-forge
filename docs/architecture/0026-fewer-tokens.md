# Architecture: fewer tokens after a fix, and rules only where they are used (agentic-flow 2.19.0)
Type: change · Size: standard

## 1. Goal

A review of the flow against the bench's own records (12 sessions, 2.14.0 against 2.18.0) showed where a run spends without gaining anything. After a fix cycle QA repeats its whole pass, while the reviewers already re-review only what the fix touched; and the coding rules are printed in the prompt of three agents whose definitions say they do not judge by them. This release gives QA a scoped re-check after a fix, keeps QA's first report when the fix only closed Standards findings, and prints the rules only for the agents that use them. Both engines change together and stay equivalent. The saving is measured with an A/B against 2.18.1 before the release is proposed.

## 2. Scope

### Included

- **A scoped QA re-check.** After a fix cycle, QA is asked to re-check the packages fixed since its last pass, against the fixes' diffs and the defects of its last report, with a new prompt `qa_recheck`. In the fallback engine that call continues QA's session.
- **No second QA for a Standards-only fix.** When every defect of every fix cycle since QA's last pass came from the standards reviewer, QA is not launched again: its last report stands.
- **A record of QA's passes.** `run["qa_passes"]` says, per pass, whether QA ran whole, scoped, or was kept.
- **Rules only where used.** The printed rules leave the prompts of the test-auditor, the doc-updater, the Spec reviewer and the Spec axis of a re-review.
- **doc-updater.** It no longer checks links (`docs-check` runs right after it) and says nothing about a CHANGELOG that is outside its zone.
- **Release 2.19.0**: notes, docs, the budget, one acceptance file.
- **Measurement.** `bench.py ab` of `agentic-flow--v2.18.1` against this branch, fixture `tally`, 5 sessions per arm, committed with the release.

### Excluded (non-goals)

- Merging gatekeeper calls (10 to 8 per run): a small saving, not measured, that costs the difference between "wave N" and "verification" when a call is lost. The user left it out.
- Trimming QA's rules to their security list: it needs code to cut a section out of a rules file.
- Skipping the first QA when the review already blocks: the bench keeps only QA's last report, so its cost in quality cannot be judged. `qa_passes` makes that visible for a later decision.
- Whether Claude Code also loads `.claude/rules/` into each agent, so the printed rules arrive twice. Not confirmed: see section 11.
- Session resume in the native workflow (it has none, as for fix attempts).
- The budget's count of agent calls (`budget_for_cycle`): it keeps counting one QA call per cycle, which is an upper bound.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`
- Bench: `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/workflows/pipeline-spec.json     WP-01  prompts: qa_recheck added; {rules} removed from three
.claude/bin/pipeline.py                  WP-01  the QA decision, the rules per agent
.claude/bin/launch.py                    WP-01  QA's session is kept for a resume
.claude/bin/conformance.json             WP-01  new scenarios (shared by both engines)
.claude/bin/test_pipeline.py             WP-01
.claude/bin/test_launcher.py             WP-01
.claude/bin/test_fix_cycles.py           WP-01  a pinned count of resumed calls
.claude/workflows/agentic-implement.js   WP-01  the same decision and prompts
.claude/bin/test_workflow.mjs            WP-01
.claude/agents/qa.md                     WP-02  a "# Re-check" section
.claude/agents/doc-updater.md            WP-02
.claude/agents/reviewer.md               WP-02
.claude/commands/implement.md            WP-02  how to present QA's passes
.claude/bin/test_definitions.py          WP-02
docs/how-it-works.md                     WP-03
.claude-plugin/plugin.json               WP-03  2.19.0
.claude/bin/upgrade.py                   WP-03  NOTES["2.19.0"]
.claude/flow-budget.json                 WP-03
.claude/quality-baseline.json            by hand: the workflow script's recorded size
.claude/bin/test_lean_hook.py            WP-03  the classes moved from test_acceptance_v218.py
.claude/bin/test_acceptance_v218.py      WP-03  deleted
.claude/flow-history.json                by hand: regenerated as the last commit
.claude/bin/test_acceptance_v219.py      AT
bench/results/                           by hand: the A/B's files
```

## 4b. Existing code context

| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| The judge loop: verification, review, QA, then a fix cycle or the end. QA is one `self.call("qa", "qa", …, "QA")`; its report replaces `run["qa"]` | `.claude/bin/pipeline.py:635-707` | The loop to change; everything after `run["qa"] = qa` stays as it is | read |
| The same loop in the workflow | `.claude/workflows/agentic-implement.js:731-797` | Must make the same calls with the same prompts | read |
| The re-review: scope is `fixed_since_review`, the diffs are `.claude/state/runs/<WP>.fix-<n>.diff` for every fix since the last review, one call per axis with open findings, label `<agent> (re-review)` | `.claude/bin/pipeline.py:590-625`, `.claude/workflows/agentic-implement.js:609-629` | The pattern the QA re-check copies: a set of packages fixed since, a count of fixes at the last pass, reset when the pass runs | read |
| `reviewed_now` resets `fixed_since_review` and copies `fix_count` | `.claude/bin/pipeline.py:541-544` | The reset to mirror for QA | read |
| A fix cycle groups defects by package, adds one to `fix_count` per package and adds the packages to `fixed_since_review` | `.claude/bin/pipeline.py:489-504` | Where the packages and defects fixed since QA's last pass are recorded | read |
| Every defect sent to a fix carries `source`: `reviewer`, `standards-reviewer`, `qa` or `verification` | `.claude/bin/pipeline.py:672-673`, `.claude/bin/pipeline.py:288` | The Standards-only test reads `source` | read |
| `call(agent_type, label, prompt, id, model, resume, schema)` counts the call and passes only truthy options to the engine's agent | `.claude/bin/pipeline.py:214-226` | `resume=True` is how a fix attempt continues its session | read |
| A fix attempt asks for `{"resume": True}` | `.claude/bin/pipeline.py:427-433` | The same option for the QA re-check | read |
| The fallback keeps a session, and what it cost, only for the idents in `packages` | `.claude/bin/launch.py:558-575`, `.claude/bin/launch.py:626` | Add `"QA"` to that set; a resumed call that gives no report already falls back to a fresh one | read |
| `render` replaces only the names it is given and leaves an unknown `{name}` as it is | `.claude/bin/pipeline.py:39-41` | A prompt without `{rules}` renders the same with or without `rules=` | read |
| The rules text and how it arrived (`printed`, `pointed`, `none`) | `.claude/bin/pipeline.py:141-147`, `.claude/workflows/agentic-implement.js:544-550` | Unchanged | read |
| Where each prompt takes the rules today | `.claude/bin/pipeline.py:358-411`, `.claude/bin/pipeline.py:555-556`, `.claude/bin/pipeline.py:603`, `.claude/bin/pipeline.py:665`, `.claude/bin/pipeline.py:725` | Remove the argument only where section 6 says | read |
| The workflow's literals for the same prompts | `.claude/workflows/agentic-implement.js:370`, `.claude/workflows/agentic-implement.js:567-568`, `.claude/workflows/agentic-implement.js:623-628`, `.claude/workflows/agentic-implement.js:706`, `.claude/workflows/agentic-implement.js:762` | Text equal to the spec's, character by character | read |
| The one-off commands (`run-review`, `run-docs`) render the spec's prompts through `render_prompt` | `.claude/bin/launch.py:302-307` | They follow the spec with no change of their own | read |
| The spec's prompts and their placeholders | `.claude/workflows/pipeline-spec.json:1-40` | One line per prompt; `{rules}` is always last | read |
| A conformance scenario is a name plus the answers each agent gives, in order; both engines run all of them and every prompt and result must match | `.claude/bin/conformance.json:1-40`, `.claude/bin/test_pipeline.py:139-225` | New behaviour needs a scenario. `summarize` builds the summary, and the `keys` tuple at `.claude/bin/test_pipeline.py:220-222` decides which of its keys are compared | read |
| `ConformanceTests` runs `node test_workflow.mjs --dump` and compares it with the Python engine's summaries | `.claude/bin/test_pipeline.py:203-225` | The two engines can only be green together, so they are one package | read |
| The node side builds the same summary | `.claude/bin/test_workflow.mjs:498-617` | Add `qa_passes` to both summaries and to the `keys` tuple | read |
| The quality limits: a function of at most 60 lines, and per file a count of lines over 120 characters that may not rise. `Pipeline.judge` is 73 lines and the workflow's `runAfterPlan` is capped at 128, both recorded in the baseline as they are | `.claude/bin/quality.py:18-19`, `.claude/quality-baseline.json:1-113` | Neither function may grow by one line; the long-line counts of `pipeline.py`, `agentic-implement.js` and `test_pipeline.py` may not rise | read |
| Two tests pin that the reviewer's prompts carry the rules ("printed rules reach the writers and judges only", and "the implementer can be left without the rules" right after it) | `.claude/bin/test_pipeline.py:459-476` | Tests to update (WP-01): the reviewer leaves those lists; the standards reviewer stays | read |
| An end-to-end test of the fallback with `FAKE_RESUME_FAILS` pins `agent_calls == len(calls) - 1`: one resumed call fails and runs again | `.claude/bin/test_fix_cycles.py:163-185` | Test to update (WP-01): its run fixes a Spec finding, so QA's re-check is resumed too and also fails once; the expected value becomes `len(calls) - 2`, and the message names both retries | read |
| The scripted agents of the tests take no extra options | `.claude/bin/test_pipeline.py:260-335` | A call with `resume=True` raises `TypeError` there, which the engine reports as "QA returned no report": the helpers must accept `**opts` | read |
| The guide says the workflow hands the rules "to each agent" | `docs/how-it-works.md:401` | Line to correct (WP-03) | read |
| The acceptance tests of 2.18.0 and their helpers (`temp_dir`, `module`, `load`, `write`, `FORBIDDEN`, `PAYLOAD`, `MARK`) | `.claude/bin/test_lean_hook.py:1-50` (where the 2.18.0 acceptance file ends up) | The helpers move with the classes (WP-03) | read |
| A test pins `{rules}` in the `re_review` prompt | `.claude/bin/test_definitions.py:652-657` | Stays true: the prompt keeps the placeholder, the Spec axis renders it empty | read |
| A test pins "the rules printed in your prompt" in implementer, test-author and qa | `.claude/bin/test_definitions.py:645-649` | Stays true: none of the three loses the rules | read |
| The reviewer's definition tells it to read the printed rules | `.claude/agents/reviewer.md:23` | Reword (WP-02): it no longer receives them | read |
| QA's process, step by step | `.claude/agents/qa.md:25-38` | The re-check is a new section after it, as the reviewers have "# Re-review" | read |
| doc-updater steps 4 and 5 | `.claude/agents/doc-updater.md:30-35` | The two lines to change | read |
| The release pattern: notes, one acceptance file, the previous one's classes moved | `.claude/bin/upgrade.py:156-170`, `.claude/bin/test_field_fixes.py:1-10` | Mirror for WP-03 | read |
| Design 0020 printed the rules for every agent that writes or judges code | `docs/architecture/0020-reliable-review.md:228` | The decision this design narrows (section 10) | read |

What must not change: the schemas, the review, the verifier, the fix limit, the budget's arithmetic, every stage command and their order, `run["qa"]` as QA's last report.

## 5. Data model

The engine's new state (Python names; the workflow uses the same in camelCase):

```python
self.fixed_since_qa: set[str] = set()      # packages fixed since QA's last pass
self.fix_count_at_qa: dict[str, int] = {}  # fix_count when QA last ran
self.sources_since_qa: set[str] = set()    # the "source" of every defect fixed since QA's last pass
```

The run record gains one key:

```python
run["qa_passes"]: list[dict]  # one per time the loop reaches QA
# {"mode": "full" | "scoped" | "kept", "status": <QA's status>, "defects": <len of its defects>}
# "kept": QA was not launched; status and defects are those of the report that stands.
```

`run["qa"]` stays QA's last report.

## 6. Contracts between modules

**The spec's prompts** (`pipeline-spec.json`, read by the Python engine; the workflow holds the same text as literals):

- `test_auditor`, `reviewer`, `doc_updater`: the same text without the trailing `{rules}`.
- `re_review`: unchanged. The engine renders `{rules}` as the rules for the Standards axis and as the empty string for the Spec axis.
- `qa`, `implement`, `implement_full`, `fix`, `test_author`, `test_author_revision`, `standards_reviewer`: unchanged.
- New, `qa_recheck`:

```
Re-check the system after a fix, according to architecture.md. Packages fixed since your last pass: {wps}. The fixes' diffs are {diffs}: read them and the code they changed. Your last report listed these defects, as JSON:
{defects}
Run the tests in your zone and the full suite again, and add tests only for what the diffs changed. Report every defect that is still open, from that list or new, with the same fields; leave out the ones the fix closed. Do not repeat the rest of your first pass.{rules}
```

`{wps}`: the packages of `fixed_since_qa`, sorted, joined with `", "`. `{diffs}`: `.claude/state/runs/<WP>.fix-<n>.diff` for each of those packages, sorted, and each `n` from `fix_count_at_qa[wp] + 1` to `fix_count[wp]`, joined with `", "` (the re-review's rule). `{defects}`: the compact JSON of `run["qa"]["defects"]`. `{rules}`: the rules.

**The QA decision**, the same in both engines, where the loop reaches QA:

1. No QA report yet in this run: the `qa` prompt, label `qa`. Mode `full`.
2. A report exists and `sources_since_qa == {"standards-reviewer"}`: no call. `run["qa"]` stays. Mode `kept`. `fixed_since_qa`, `fix_count_at_qa` and `sources_since_qa` are not reset, so a later re-check covers these fixes too.
3. A report exists and `sources_since_qa` holds any other source: the `qa_recheck` prompt, label `qa (re-check)`, the QA schema, ident `QA`, and `resume=True` in the Python engine. Mode `scoped`. A missing report stops the run as today (`stop("qa", "QA returned no report")`).
4. A report exists and `sources_since_qa` is empty (the loop only returns to QA after a fix cycle, so this is not expected): as rule 1, mode `full`.
5. After a call (modes `full` and `scoped`): `fixed_since_qa = set()`, `fix_count_at_qa = dict(fix_count)`, `sources_since_qa = set()`.
6. Every mode appends to `run["qa_passes"]`.
7. In mode `kept` the stage commands do not change: `open-stage qa` and `close-stage qa QA=…` run as today, with no agent between them. The stage check only looks at what was written, so an untouched QA zone closes clean; no guard is added.

`fix_cycle(defects, opened)` adds the cycle's packages to `fixed_since_qa` and the `source` of each of its defects to `sources_since_qa`.

Everything after QA (the defects that go to a fix, pending, `close-stage qa QA=…`, the documentation) reads `run["qa"]` exactly as today, in the three modes.

**The fallback's sessions** (`launch.py`): `resuming(launch, set(wps(manifest)) | {"QA"})`. No other change: a resumed QA that gives no report runs once more fresh, and its cost is its own (2.18.1).

**The summary compared by the conformance tests** gains `"qa_passes"`: the list of modes, in order. It is added to `summarize` in `test_pipeline.py` and in `test_workflow.mjs`, and to the `keys` tuple at `.claude/bin/test_pipeline.py:220-222`.

**The new conformance scenarios**, with exactly these names:

- `QA re-checks only what a fix touched`
- `a standards-only fix keeps the QA report`
- `a verification fix is re-checked by QA`
- `a kept QA report is covered by the next re-check`

## 7. Conventions

- English everywhere; usage errors keep the `Uso:` prefix (design 0016).
- The workflow's prompt literals equal the spec's text character by character; the conformance tests compare every prompt.
- No new module, no new dependency. `flow-budget.json` is raised only by what the change needs, with its why.
- The guides do not cite flow version numbers (`acceptance/test_docs.py`).
- Commit format: `type: summary` in English; the flow history is regenerated as the last commit.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · QA re-checks only what a fix touched
  - Scenario: the conformance plan; QA's first report is FAIL with one high implementation defect on WP-02; its second is PASS.
  - Action: the Python engine (`pipeline.Pipeline`) runs to the end with scripted agents. The acceptance tests of AC-001 to AC-004 declare their own scenarios inline, with `test_pipeline.py`'s helpers for a scripted gate and agents, and read the options each call received; they do not read `conformance.json`.
  - Expected: two QA calls. The first prompt is the `qa` prompt. The second has label `qa (re-check)`, starts with `Re-check the system after a fix`, names `WP-02`, `.claude/state/runs/WP-02.fix-1.diff` and the first report's defect as JSON, ends with the rules, and is asked with `resume=True`. `run["qa_passes"]` modes are `["full", "scoped"]`. `run["qa"]` is the second report.
  - Must not: the second prompt is the `qa` prompt; the diff of a package that was not fixed is named.
  - Check: `test_acceptance_v219.py`
  - WP: WP-01

- AC-002 · A Standards-only fix keeps QA's report
  - Scenario: the standards reviewer reports one reflex finding on WP-02, then its re-review says ADDRESSED; QA's only report is PASS with one low defect.
  - Action: the Python engine runs to the end.
  - Expected: exactly one QA call. `run["qa"]` is that report, with its low defect. Modes are `["full", "kept"]`. The gate still receives `close-stage qa QA=pass` after the fix. The result is `OK`.
  - Must not: a second QA call; a missing `close-stage qa`.
  - Check: `test_acceptance_v219.py`
  - WP: WP-01

- AC-003 · Any other fix is re-checked, and a kept report is covered later
  - Scenario A: QA's first report has one high implementation defect on WP-02; after its fix, verification fails once on a file of WP-01 (source `verification`), which is fixed too.
  - Scenario B: the standards reviewer reports one reflex finding on WP-02. After the first fix its re-review says NOT_ADDRESSED (QA is kept), so WP-02 is fixed a second time. After that fix verification fails once on a file of WP-01, which is fixed; then the re-review says ADDRESSED.
  - Action: the Python engine runs to the end.
  - Expected: A: modes `["full", "scoped"]`, and the scoped prompt names `WP-01, WP-02` and the diffs `WP-01.fix-1` and `WP-02.fix-1`. B: modes `["full", "kept", "scoped"]`, and the scoped prompt names `WP-01, WP-02` and the three diffs `WP-01.fix-1`, `WP-02.fix-1` and `WP-02.fix-2`.
  - Must not: `kept` when a defect of the cycle has a source other than `standards-reviewer`.
  - Check: `test_acceptance_v219.py`
  - WP: WP-01

- AC-004 · The rules are printed only where they are used
  - Scenario: a plan whose rules text is `RULE-TEXT`, with documentation; the reviewer and the standards reviewer each report one blocking finding on WP-02, so one fix cycle re-reviews both axes.
  - Action: the Python engine runs to the end.
  - Expected: `RULE-TEXT` is in every prompt of the implementer, the test-author, the standards reviewer (review and re-review) and QA; it is in no prompt of the test-auditor, the reviewer (review and re-review), the doc-updater, the verifier or the gatekeeper.
  - Must not: `Rules you must follow` in any prompt of the second group.
  - Check: `test_acceptance_v219.py`, on the Python engine's prompts; the workflow's are compared by AC-005
  - WP: WP-01

- AC-005 · Both engines stay equivalent
  - Scenario: `conformance.json` with the four scenarios named in section 6.
  - Action: `node .claude/bin/test_workflow.mjs`, and `test_pipeline.ConformanceTests`.
  - Expected: both pass. The four names are in `conformance.json`. `"qa_passes"` is in the `keys` tuple of `test_pipeline.ConformanceTests` and in the text of `test_workflow.mjs`. The text of `agentic-implement.js` contains `qa (re-check)` and `Re-check the system after a fix`.
  - Must not: a scenario skipped in one engine.
  - Check: `test_acceptance_v219.py` (the names, the key and the literals) and the two commands, which `verify` runs
  - WP: WP-01

- AC-006 · The definitions say what the prompts now do
  - Scenario: the agent definitions and `implement.md`.
  - Action: read them.
  - Expected: `qa.md` has a `# Re-check` section that names the diffs and "every defect that is still open". `reviewer.md` does not contain "rules printed in your prompt". `doc-updater.md` contains neither "check that all its relative links" nor "Create it if it is in your zone", and says to write the CHANGELOG only when it is in its zone. `implement.md` mentions `qa_passes`.
  - Must not: `qa.md`, `implementer.md` or `test-author.md` lose "the rules printed in your prompt".
  - Check: `test_acceptance_v219.py`
  - WP: WP-02

- AC-007 · Docs and release 2.19.0
  - Scenario: this repository.
  - Action: read `plugin.json`, `upgrade.NOTES`, `docs/how-it-works.md`, the test files.
  - Expected: version `2.19.0`; `NOTES["2.19.0"]` has at least two notes that name "QA" and "rules"; `how-it-works.md` says QA re-checks after a fix; the only `test_acceptance*.py` is `test_acceptance_v219.py`; `test_lean_hook.py` holds the classes `HookPathTests`, `LeanTests` and `ReleaseTests` moved from the 2.18.0 file.
  - Must not: a version number of the flow in a guide.
  - Check: `test_acceptance_v219.py`
  - WP: WP-03

### Work packages

#### WP-01 · The spec, both engines and the scenarios
- Wave 1.
- Files: `.claude/workflows/pipeline-spec.json`, `.claude/bin/pipeline.py`, `.claude/bin/launch.py`, `.claude/bin/conformance.json`, `.claude/bin/test_pipeline.py`, `.claude/bin/test_launcher.py`, `.claude/bin/test_fix_cycles.py`, `.claude/workflows/agentic-implement.js`, `.claude/bin/test_workflow.mjs`.
- Implements section 6 whole. Consumes nothing. One package for both engines: `ConformanceTests` compares them, so neither is green without the other.
- ACs: AC-001, AC-002, AC-003, AC-004, AC-005.
- **Patterns to mirror:** `.claude/bin/pipeline.py:590-625` and `.claude/workflows/agentic-implement.js:609-629` (scope, diffs and label of a scoped pass, in each engine); `.claude/bin/pipeline.py:541-544` (the reset); `.claude/bin/pipeline.py:427-433` (`resume`); `.claude/workflows/agentic-implement.js:544-550` (`RULES`); `.claude/bin/test_pipeline.py:459-470` (how a test reads a scenario's prompts by agent); `.claude/bin/test_workflow.mjs:498-617` (the summary and the spec comparison).
- **Gotchas:**
  - Quality: a function may have at most 60 lines. `Pipeline.judge` (73) and the workflow's `runAfterPlan` (capped at 128) are in the baseline and may not grow by a line: the QA decision goes in its own method, `qa_stage` in Python and `qaStage` in the workflow, and the loop calls it. The number of lines over 120 characters may not rise in `pipeline.py`, `agentic-implement.js` or `test_pipeline.py`: split the `qa_recheck` literal across lines in the workflow, as the re-review's is.
  - `qa_passes` must be added in three places or it is never compared: both `summarize` functions and the `keys` tuple.
  - The workflow has no disk and no resume: its re-check is an ordinary `report(...)` with label `qa (re-check)`. `test_workflow.mjs` compares the spec's prompts with the script's literals, so `qa_recheck` must be found there.
  - Sort the packages before joining, in both engines, or the prompts differ.
  - A resumed call uses the QA schema of the agent type: no `schema=` is passed.
  - The scripted agents of `test_pipeline.py` must accept `**opts`, or the resumed QA call fails inside them (4b). The acceptance tests' own agents too.
  - `test_fix_cycles.py:185` changes as 4b says; read `test_ac_005` (line 163) as well, whose run now resumes QA.
- **Exact imports and APIs:** `render`, `compact`, `self.call`, `self.stop`, `self.prompts[...]`, all already in `pipeline.py`; `report`, `stop`, `RULES`, `QA_SCHEMA` in the workflow.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_pipeline.py"`; `python3 -m unittest discover -s .claude/bin -p "test_launcher.py"`; `python3 -m unittest discover -s .claude/bin -p "test_fix_cycles.py"`; `node .claude/bin/test_workflow.mjs`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · The definitions
- Wave 1.
- Files: `.claude/agents/qa.md`, `.claude/agents/doc-updater.md`, `.claude/agents/reviewer.md`, `.claude/commands/implement.md`, `.claude/bin/test_definitions.py`.
- Consumes section 6 by signature.
- ACs: AC-006.
- **Patterns to mirror:** `.claude/agents/reviewer.md:98-103` (how a "# Re-review" section is written); `.claude/bin/test_definitions.py:612-626` (how a definition test reads phrases).
- **Gotchas:** `prompt_bytes` is budgeted (99,000; 98,956 today) and counts the agents and the commands, `implement.md` included: the new text should be paid for by the lines removed; if the sum still grows, WP-03 raises the budget. `test_definitions.py` pins phrases of these files: run it.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_definitions.py"`.

#### WP-03 · Docs, notes, release and the moved tests
- Wave 2 (it moves the previous acceptance file and regenerates the history, after everything else).
- Files: `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_lean_hook.py`, `.claude/bin/test_acceptance_v218.py`.
- ACs: AC-007.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-170` (a release's notes); `.claude/bin/test_field_fixes.py:1-10` (the header of a file of moved tests); `docs/how-it-works.md:140-156` (where fix cycles are described).
- **Gotchas:**
  - The moved classes need the helpers of `test_acceptance_v218.py` (`temp_dir`, `module`, `load`, `write`, `FORBIDDEN`, `PAYLOAD`, `MARK`): move them too.
  - In the moved `ReleaseTests`, drop the two assertions that only a current release can hold (the plugin's version, and "the only acceptance file"). Keep the rest, `NOTES["2.18.0"]` and the docs included, and mark the class `FLOW_REPO_ONLY`, because it reads this repository's docs.
  - `flow-budget.json`: `code_lines` (7,210) will grow with the engines and the notes, and `prompt_bytes` may: raise only what is exceeded, with its why.
  - The README does not describe QA's passes: it needs no change.
  - `docs/how-it-works.md:401` says the workflow hands the rules "to each agent": say which agents now.
  - `.claude/flow-history.json` is not this package's: it is built from git, so the maintainer regenerates it by hand as the last commit.
- **WP validation:** the four commands of section 3, and `python3 -m unittest discover -s acceptance` (it holds the docs test of section 7).

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v219.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v219.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/workflows/pipeline-spec.json", ".claude/bin/pipeline.py", ".claude/bin/launch.py", ".claude/bin/conformance.json", ".claude/bin/test_pipeline.py", ".claude/bin/test_launcher.py", ".claude/bin/test_fix_cycles.py", ".claude/workflows/agentic-implement.js", ".claude/bin/test_workflow.mjs"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-005"], "mirror": [".claude/bin/pipeline.py:590-625", ".claude/workflows/agentic-implement.js:609-629", ".claude/bin/pipeline.py:541-544", ".claude/bin/pipeline.py:427-433", ".claude/workflows/agentic-implement.js:544-550", ".claude/bin/test_pipeline.py:459-470", ".claude/bin/test_workflow.mjs:498-617"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/agents/qa.md", ".claude/agents/doc-updater.md", ".claude/agents/reviewer.md", ".claude/commands/implement.md", ".claude/bin/test_definitions.py"],
     "acs": ["AC-006"], "mirror": [".claude/agents/reviewer.md:98-103", ".claude/bin/test_definitions.py:612-626"]},
    {"id": "WP-03", "wave": 2, "depends_on": ["WP-01", "WP-02"], "files": ["docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_lean_hook.py", ".claude/bin/test_acceptance_v218.py"],
     "acs": ["AC-007"], "mirror": [".claude/bin/upgrade.py:156-170", ".claude/bin/test_field_fixes.py:1-10", "docs/how-it-works.md:140-156"]}
  ]
}
```

## 9. Test strategy

- **Acceptance** (`test_acceptance_v219.py`, written first and red): AC-001 to AC-004 drive `pipeline.Pipeline` with a scripted gate and scripted agents, the way `test_pipeline.py` runs a conformance scenario, and read the prompts and options each call received. AC-005 to AC-007 read files. Nothing is spent.
- **Unit:** each package extends the tests of its files; the conformance scenarios are the shared check of both engines.
- **Teeth:** before the release, each behaviour is broken once by hand (the `kept` test inverted, the Spec axis given the rules, a package left out of the diffs) and the acceptance test must fail.
- **Measurement, by hand, after the code is green:** `python3 bench/bench.py ab --a agentic-flow--v2.18.1 --b <this branch> --fixture tally --repeat 5 --seed 0` (10 real sessions; about 9 USD at the costs of the last A/B, not measured for this one). The result files are committed. Reported: cost, minutes, output, oracle and mutation, the interval and the sign test, and `qa_passes` per session, read by hand from each session's result file in the A/B's folder (the bench saves the whole run record).
- **By hand, before the pull request:** the suites CI runs beyond `verify` (`python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`), the installed-project job, and `agentic.py flow-history` as the last commit, with its `--check`.
- **What decides:** quality first. If the oracle or the mutation score of arm B is lower than arm A's beyond what the sessions of one arm differ among themselves, the QA change is not released as it is. A saving whose interval includes 1 is reported as not shown, not as a saving.

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| QA gets a scoped re-check after a fix, with its last report's defects in the prompt | Leave QA whole; pass only the diffs | The second pass was a full repeat in the 5 sessions of the last A/B that had a fix cycle. The defects go in the prompt because the workflow has no resume: without them a fresh QA could not say which of its defects are still open, and the final report would lose them |
| A Standards-only fix keeps QA's report | Always re-check | Such a fix names a constant or renames something; verification (tests and acceptance) runs after every fix and the standards re-review reads the diff. Chosen by the user |
| The test for "Standards-only" is the defects' `source` | Tier `reflex`, or the size of the diff | `source` is set by the engine, not by an agent, and is already on every defect |
| A kept report does not reset the scope | Reset on every visit | A later re-check must cover the fixes QA never saw |
| The rules leave the test-auditor, the doc-updater and the Spec reviewer | Keep 0020's "every agent that writes or judges code" | Their definitions say they do not judge by the rules (the test-auditor: "do not judge style"; the reviewer: a breach "belongs to the other axis"; the doc-updater writes prose). This narrows design 0020; chosen by the user |
| QA keeps the whole rules | Only their security list | Cutting a section needs code; left out by the user |
| `re_review` keeps `{rules}`, rendered empty for Spec | Two prompts | One prompt, one pinned test unchanged |
| QA's session is resumed in the fallback only | Add resume to the workflow | The workflow script has no sessions; the fallback already resumes fix attempts |
| `qa_passes` in the run record | Nothing, or keeping every QA report | The bench could not tell what the first QA had found; modes and counts are enough to measure this change without growing the record |
| No gatekeeper merges | Merge 10 calls into 8 | Left out by the user: small, unmeasured, and it blurs which stage a lost call belonged to |
| The budget's QA count is unchanged | One less call when a cycle is Standards-only | It is an upper bound; changing it moves pinned scenarios for no saving |
| The flow history and the A/B are steps by hand, not a package's | Give them to WP-03 | The history is built from git commits, which no agent makes; the A/B spends real sessions |
| The manifest's `docs` zone stays `docs/assets/`, as in the last maintainer designs | The guides in the doc-updater's zone | The guides are part of the design here (WP-03 owns the one that changes), so the doc-updater has nothing to add |
| Both engines in one package | One package per engine, in the same wave | `ConformanceTests` runs the workflow and compares it with the Python engine: neither passes its own validation without the other |
| The workflow script's size is recorded in the quality baseline (800 to 831 lines) | Squeeze 28 lines out of it by joining schema definitions | The script was exactly at the 800-line limit and cannot be split (it has no disk); squeezing would be cosmetic and the next change would hit the limit again. Decided by the user during the implementation |
| Written with Fable 5.2 | Pause to switch model | The user chose it at the model gate |

## 11. Risks and open questions

- **A scoped QA can miss a regression far from the fix.** Verification runs the whole suite and the acceptance tests after every fix, and QA re-runs its own tests; what is lost is new exploratory tests outside the diff. The A/B's mutation score is the check. If it drops, the scoped pass is dropped and only the kept mode is released.
- **The saving is an estimate until measured.** From the last A/B: the second QA passes cost about 10 % of the total, and the three agents' rules about 2.5 to 3 %. Neither is measured for this design; the A/B of section 9 measures the first on `tally`, and five sessions per arm can still leave an interval that includes 1.
- **Rules arriving twice: not confirmed.** In the container where this was checked, a 40 KB file in `.claude/rules/` changed the input of `claude -p` by 0 tokens, with and without `--agent`; so did a `CLAUDE.md`. The bench disables `CLAUDE.md` loading on purpose. Whether an interactive session's subagents receive `.claude/rules/` as well as the printed copy is open; nothing in this design depends on it.
- **A resumed QA session may be gone** (a new container, a pruned session): the fallback already runs a fresh agent when a resumed one gives no report, at the cost of one extra call.
- **The size budget will move.** `prompt_bytes` is 44 bytes under its budget: the new `qa_recheck` prompt lives in `pipeline-spec.json`, which the budget does not count, but the `# Re-check` section of `qa.md` and the line in `implement.md` do. `code_lines` (7,210) grows with the two engines and the notes. WP-03 raises what is exceeded, with its why.
