# Architecture: fixes go where they belong, QA that could not run says so, and no PowerShell rule runs arbitrary code (issues 140, 141, 142, 118; agentic-flow 2.21.2)
Type: fix · Size: standard

## 1. Goal

A real run of a PowerShell project (result `REVIEW`, `fix_cycles: 2`, QA `BLOCKER` three times with 0 defects) showed four defects of the flow.

- **Issue 140.** A fix attempt's diff `runs/<WP>.fix-<N>.diff` is named from the ledger's `fix_count`, which is never reset between runs. The engines read it by their own in-run counter, which starts at 0. So agents read diffs left by earlier runs.
- **Issue 141.** A finding whose evidence names files of several packages goes to one package. The fix prompt forbids it to touch the others' files, and the re-review can only say ADDRESSED or NOT_ADDRESSED. So the finding burns every fix cycle.
- **Issue 142.** When the environment refused QA's commands, QA's `BLOCKER` is read as a verdict on the code. A `kept` QA pass then replays that stale report.
- **Issue 118.** `sync-permissions` allows a verify command only as its whole line. An agent that runs a subset of the tests matches no rule, and auto mode refuses it. Also, a `powershell … -Command X:*` rule lets an agent run any PowerShell code, and `validate` does not see it.

This release fixes the four, in both engines, which stay equivalent.

## 2. Scope

### Included

- **Issue 140, fix-attempt numbering.**
  - `close-stage` accepts `ID=state@N` with `--fix`. N becomes the diff's number and the ledger's `fix_count`.
  - Both engines send their in-run attempt number.
  - An attempt whose diff cannot be computed writes a placeholder, so no stale file survives under that number.
- **Issue 141, findings split by owner.**
  - After verification, every confirmed review finding (both axes) whose `evidence` or `fix` names files that other packages own is split into one finding per owning package. Each part carries `scope`, the files it is judged in.
  - `pipeline-plan` gives the engines each package's files (`owners`) and the repo root (`root`).
  - The re-review prompt says a finding with a `scope` is judged only in those files.
  - The reviewers' definitions ask for one finding per owning package.
- **Issue 142, QA blocked by the environment.**
  - The QA schema gains two optional fields, `blocker_kind` (`environment` | `design`) and `not_run` (the commands QA could not run).
  - An environment `BLOCKER` becomes one `needs validation` pending item per command, of kind `qa not run`. The run's `detail` says QA did not run.
  - The next QA pass after a fix is a full call, never `kept`.
  - The run still ends `REVIEW` (the user's choice: QA did not validate).
- **Issue 118, permissions.**
  - `validate` rejects `powershell`/`pwsh` prefix rules (`:*`) that run code. A rule is safe only if a `-File`/`-f` comes before any `-Command`/`-EncodedCommand` flag. Bare `powershell`, `pwsh` and `cmd` (one word, no arguments) are rejected too.
  - `sync-permissions` writes only the exact rule for a verify or acceptance command that runs PowerShell code, and removes the `:*` form it wrote before.
  - `validate` warns about such a command.
  - The PowerShell rules pack and `/architect` recommend a fixed runner script run with `-File`.
- **Docs and release 2.21.2.** The guide, `/implement`'s presentation, the agents' definitions (QA, both reviewers), the notes, the budget and the pin in `test_acceptance_v221.py`.

### Excluded (non-goals)

- **QA defects that span packages.** The split applies to review findings only, which is what the run showed. QA's `defects` keep their `wp`.
- **New findings of a re-review.** They are still recorded and never fixed in the run.
- **The manual commands' counting** (`run-wave --fix` increments the ledger's `fix_count` as its cap, `.claude/bin/launch.py:419-427`). `close-stage` without `@N` behaves exactly as today.
- **Resetting the ledger or deleting old diffs at the start of a run.** The explicit number makes them harmless (section 10).
- **Whether auto mode's classifier honours allow rules.** Not reproducible here (section 11). The design makes the rules match what the agents run.
- **The PowerShell project's own fixes** (its manifest, its `$ExitUnreachable` copies). They belong to the user.

## 3. Stack

Python 3.9+ (standard library only), and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- **Unit and acceptance:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- **The workflow against the conformance scenarios:** `node .claude/bin/test_workflow.mjs`
- **Quality limits:** `python3 .claude/bin/agentic.py quality`
- **Bench:** `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/bin/stage.py                    WP-01  close-stage: ID=state@N with --fix; placeholder diff
.claude/bin/agentic.py                  WP-01  close-stage's usage text only
.claude/bin/test_fix_attempts.py        WP-01  new: unit cases
.claude/bin/findings.py                 WP-02  split_by_owner, qa_environment_blocked, qa_not_run_items, QA_NOT_RUN_DETAIL
.claude/bin/pipeline.py                 WP-02  @N in fix closes, split after verification, QA environment blocker, no kept replay
.claude/workflows/agentic-implement.js  WP-02  the same, in the native engine
.claude/workflows/pipeline-spec.json    WP-02  QA schema fields; re_review prompt sentence
.claude/bin/launch.py                   WP-02  pipeline_plan: owners and root
.claude/bin/conformance.json            WP-02  three new scenarios (Annex A)
.claude/bin/test_pipeline.py            WP-02  the pinned --fix gate string
.claude/bin/test_workflow.mjs           WP-02  the pinned --fix gate strings
.claude/bin/test_owner_split.py         WP-02  new: unit cases of split_by_owner and the QA helpers
.claude/bin/manifest_check.py           WP-03  runs_code, open_ended_rule, OPEN_ENDED, code_runner_commands, the warning
.claude/bin/installer.py                WP-03  sync_permissions: exact rule only, removes the old :* form
.claude/rules-library/powershell.md     WP-03  runner script with -File; allow_bash example
.claude/commands/architect.md           WP-03  the allow_bash bullet
.claude/bin/test_code_runner_rules.py   WP-03  new: unit cases
docs/how-it-works.md                    WP-04  diffs, split, QA environment blocker, PowerShell rules
docs/how-to/README.md                   WP-04  the diff's N
.claude/commands/implement.md           WP-04  detail and qa not run; qa_passes
.claude/agents/qa.md                    WP-04  blocker_kind and not_run
.claude/agents/reviewer.md              WP-04  one finding per owning package
.claude/agents/standards-reviewer.md    WP-04  one finding per owning package
.claude-plugin/plugin.json              WP-04  2.21.2
.claude/bin/upgrade.py                  WP-04  NOTES["2.21.2"]
.claude/flow-budget.json                WP-04
.claude/bin/test_acceptance_v221.py     WP-04  its version pin: 2.21.2
.claude/bin/test_failure_evidence.py    WP-04  its two version pins (lines 225, 241): 2.21.2
.claude/bin/test_fix_routing.py         AT
.claude/flow-history.json               by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| `close_stage(manifest, label, items)` parses `ID=state` with `partition("=")`, checks `jid in entities(manifest)` and `state in LEDGER_STATES`, and dies with `close-stage: invalid entry '<item>' (...)`. With `--fix` it sets `fix_count` to the ledger's value + 1 and calls `write_fix_diffs` with that number | `.claude/bin/stage.py:236-277` (the fix count at 256-260) | `@N` is split off the state after the `=`. Without `@N`, unchanged | read |
| `write_fix_diffs(manifest, label, attempts)` returns early when `tree-<label>.txt` is missing or `git_tree()` is falsy. It skips a package with no files and writes `runs/<ID>.fix-<N>.diff`, or `(this attempt changed no file)` | `.claude/bin/stage.py:284-304` | The early return becomes a placeholder write | read |
| `LEDGER_STATES`; `ledger_read`/`ledger_update` (the ledger is never cleared by the flow) | `.claude/bin/core.py:30`, `.claude/bin/core.py:379-389` | `fix_count` is set to N, not incremented, when N is given | read |
| `close-stage`'s usage text, in the module docstring and in `cmd_close_stage` | `.claude/bin/agentic.py:14`, `.claude/bin/agentic.py:216-219` | Mention `ID=state@N` | read |
| The manual `run-wave --fix` caps by the ledger's `fix_count` and increments it | `.claude/bin/launch.py:397-433` | Unchanged | read |
| CLI tests that close with `--fix` and no `@N`: two cycles give `fix_count` 2; the diff holds only that package's files | `.claude/bin/test_agentic.py:485-490`, `.claude/bin/test_agentic.py:572-583` | Must stay green: hence `@N` is optional | read |
| Fallback engine: `wave_states` builds `WP-01=done` marks; `launch_wave` returns `close-stage {wave} {marks}{' --fix'}`, and its attempt is `self.fix_count.get(wp, 0) + 1`, the retry diff `fix-{attempt - 1}`; `fix_cycle` increments `self.fix_count` after the waves run | `.claude/bin/pipeline.py:85-90`, `.claude/bin/pipeline.py:415-446`, `.claude/bin/pipeline.py:508-522` | The marks of a fix wave gain `@<attempt>` | read |
| Native engine: `waveStates`, `launchWave` (`attempt = (fixCount[wp] \|\| 0) + 1`; `closeCmd` at 439), `fixCycle` | `.claude/workflows/agentic-implement.js:298`, `.claude/workflows/agentic-implement.js:409-441`, `.claude/workflows/agentic-implement.js:498-517` | The same change | read |
| The readers of diffs: the retry prompt, the re-review (`fixDiffs` / the `diffs` join) and QA's re-check | `.claude/workflows/agentic-implement.js:418`, `.claude/workflows/agentic-implement.js:679-686`, `.claude/bin/pipeline.py:430`, `.claude/bin/pipeline.py:618-619`, `.claude/bin/pipeline.py:667-668` | Unchanged: they already use the in-run counter, which the writer now follows | read |
| Tests that pin the fix close's gate string | `.claude/bin/test_pipeline.py:405-414` (`startswith("close-stage 1 WP-01=blocker --fix")`), `.claude/bin/test_workflow.mjs:180-187`, `.claude/bin/test_workflow.mjs:418-423` (`gates.includes('close-stage 1 WP-02=done --fix')`) | WP-02 updates them to `@1` | read |
| `attribute(manifest, lines, by_criteria)` maps text to packages by whole path. It normalises `\` to `/` and strips `ROOT/`, and a file matches with `(?<![\w./-])` + escaped path + `(?![\w-])` (no lookahead for a directory ending in `/`) | `.claude/bin/verification.py:277-295` | `split_by_owner` uses the same matching, without criteria | read |
| `findings.py`: `fingerprint` (FNV-1a over axis\|tier\|rule\|file\|problem) and `with_fingerprints` (a repeat gets `-2`, `-3`); the workflow's copies | `.claude/bin/findings.py:70-94`, `.claude/workflows/agentic-implement.js:236-253` | A part's fingerprint is `fingerprint(part)`, suffixed the same way if taken | read |
| `pipeline.py` imports from `findings` | `.claude/bin/pipeline.py:19` | Add the new names to that import | read |
| The full review: findings marked with fingerprints, the graves verified, `record[axis].confirmed`, `run.review`, then `close_review` with the confirmed per axis | `.claude/bin/pipeline.py:567-609`, `.claude/workflows/agentic-implement.js:568-616` | The split runs on each axis's confirmed list before `record` is built | read |
| The re-review: open findings of the fixed packages by `wp`, a verdict per fingerprint; its prompt (`re_review` in the spec; inline in the workflow) | `.claude/bin/pipeline.py:611-646`, `.claude/workflows/agentic-implement.js:623-662` | One sentence is appended after "with the line that shows it." in both | read |
| A test pins the head of the re-review prompt (the text before `{findings}`) | `.claude/bin/test_workflow.mjs:602-611` | The new sentence goes after `{diffs}`: the head does not change | read |
| `pipeline_plan` prints the plan JSON (`wave_of`, `work_packages`, `agents`, …); `wps(manifest)` gives each package with its `files` | `.claude/bin/launch.py:662-678` | Add `owners` and `root` | read |
| The conformance plan the simulated worlds answer `pipeline-plan` with (no `owners`) | `.claude/bin/conformance.json` (key `plan`), `.claude/bin/test_pipeline.py:65-66` | The engines must work without `owners`/`root` | read |
| QA's schema (`status` PASS\|FAIL\|BLOCKER; required `status, plan, defects, gaps, needs_validation`) in the spec and the workflow's copy; a test compares the copies | `.claude/workflows/agentic-implement.js:127-145`, `.claude/bin/test_workflow.mjs:587-600` | Two optional properties, the same in both | read |
| `qa_stage`/`qaStage`: `mode` is `full` (no report, or no source since), `kept` (only the standards reviewer since) or `scoped`; `kept` makes no call and re-records the standing report in `qa_passes` | `.claude/bin/pipeline.py:656-678`, `.claude/workflows/agentic-implement.js:688-712` | An environment-blocked standing report forces `full` | read |
| The end of a pass: `baseline` (design, no WP, needs-validation items) becomes `qa_pending`; with nothing eligible, `result` is `REVIEW` when there are defects, QA is `BLOCKER` or a pending item blocks | `.claude/bin/pipeline.py:712-740`, `.claude/workflows/agentic-implement.js:806-829` | The QA items join `baseline`; `detail` is set in that branch | read |
| `needs_item`/`needsItem` and `untestedItem`, the shape of a `needs validation` pending item (with `kind`, `claim`, `fact`, `how_to_check`) | `.claude/bin/pipeline.py:250-256`, `.claude/workflows/agentic-implement.js:283`, `.claude/workflows/agentic-implement.js:290-295` | `qa_not_run_items` builds the same shape | read |
| `summarize` compares `detail`, `pending` types and `qa_passes` across engines | `.claude/bin/test_pipeline.py:154-171`, `.claude/bin/test_pipeline.py:211-222` | The new scenarios are checked by it with no change | read |
| QA tests pin `qa_passes` modes for the existing scenarios | `.claude/bin/test_qa_recheck.py:57-116` | Must stay green: only an environment `BLOCKER` changes the mode | read |
| `OPEN_ENDED`, `open_ended_rule` (a rule is open-ended when it is empty, has `*` in its prefix, or is one token in `OPEN_ENDED`) and `open_ended_command` | `.claude/bin/manifest_check.py:30-33`, `.claude/bin/manifest_check.py:39-43`, `.claude/bin/manifest_check.py:46-60` | `open_ended_rule` gains the PowerShell case. `open_ended_command` reads `OPEN_ENDED` (lines 54-58), which is why the new one-word shells go in a separate set and `OPEN_ENDED` does not change | read |
| `command_errors` reports `allow_bash: rule too broad (…)`; `complexity_warnings` returns the warnings `validate` prints as `warning: …` | `.claude/bin/manifest_check.py:186-200`, `.claude/bin/manifest_check.py:78-97`, `.claude/bin/agentic.py:187-192` | The PowerShell warning is appended by `complexity_warnings` (its docstring widened), so `agentic.py` needs no change for it | read |
| Tests of broad and specific rules, and of glob commands | `.claude/bin/test_agentic.py:206-214`, `.claude/bin/test_manifest_check.py:27-37` | Stay green | read |
| `sync_permissions` adds `Bash(cmd)` and `Bash(cmd:*)` for the acceptance command and every verify command, never removes anything, and prints `N rule(s) added …` | `.claude/bin/installer.py:115-129` | PowerShell code commands get the exact rule only, and their `:*` form is removed | read |
| Its test: other rules kept, idempotent | `.claude/bin/test_agentic.py:509-521` | Stays green | read |
| The PowerShell pack's command table recommends `powershell … -Command "Invoke-Pester …"` | `.claude/rules-library/powershell.md:43-49` | Replaced by a runner script with `-File` | read |
| `/architect`'s `allow_bash` bullet | `.claude/commands/architect.md:218` | Extended | read |
| QA's `status` line; the standards reviewer's "one finding per rule and file"; the reviewer's report line | `.claude/agents/qa.md:67`, `.claude/agents/standards-reviewer.md:27`, `.claude/agents/reviewer.md:107` | Lines to extend | read |
| The guide's lines on fix diffs and statuses; the how-to's diff line; `/implement`'s `detail` and `qa_passes` lines | `docs/how-it-works.md:155`, `docs/how-it-works.md:366`, `docs/how-it-works.md:392`, `docs/how-to/README.md:204`, `.claude/commands/implement.md:51`, `.claude/commands/implement.md:59` | Lines to extend | read |
| The release pattern of a fix: `NOTES["2.21.1"]` right above `"2.21.0"`; the minor release's test pins the version | `.claude/bin/upgrade.py:156-163`, `.claude/bin/test_acceptance_v221.py:138-145` | `NOTES["2.21.2"]` right above `"2.21.1"`; pin `2.21.2` | read |
| The 2.21.1 acceptance file pins the version: `plugin["version"] == "2.21.1"` and `'"2.21.1"'` in `test_acceptance_v221.py`; its other checks (`NOTES["2.21.1"]` right above `"2.21.0"`, `2.21.1` absent from the guide) stay true | `.claude/bin/test_failure_evidence.py:222-242` (the pins at 225 and 241) | WP-04 changes only those two pins to `2.21.2` | read |
| `test_lean.py` holds the flow's size to `flow-budget.json` (5 % slack below); `test_the_flow_stays_within_its_budget` runs in every package's validation | `.claude/bin/test_lean.py:24-25`, `.claude/bin/test_lean.py:57-70`, `.claude/bin/test_lean.py:138` | Raise what is exceeded, with its why (WP-04). In wave 1 it is expected to fail | read |
| `shlex.split` reads an unquoted `\` as an escape: `C:\Windows\x\powershell.exe -Command x` gives `C:Windowsxpowershell.exe` | measured with `python3 -c "import shlex; …"` in this session | Replace `\` by `/` before splitting (a measured behaviour of the standard library, not repo code) | inferred |
| `close-stage`'s usage text is in Spanish (`ID=estado`, `Uso:`) | `.claude/bin/agentic.py:14`, `.claude/bin/agentic.py:219` | WP-01 writes it in English (`ID=state[@N]`, `Usage:`) | read |
| The rules packs' tables must keep the rows `build`, `types`, `lint`, `tests` in that order | `.claude/bin/test_definitions.py:318-328` | `powershell.md` keeps the four rows | read |
| `raw_run(decl)` runs a scenario in the fallback engine and returns the raw result (with full `pending` items) | `.claude/bin/test_pipeline.py:336` | AC-006 reads pending items through it | read |
| The quality ratchet: a file at or under 800 lines may grow to 800; a function's allowance is 60 lines or its stored value; no new line over 120 characters in a file at its stored count | `.claude/bin/quality.py:225-243`, `.claude/quality-baseline.json` | Measured now: `pipeline.py` 790 lines (allowed 800), 26 long (allowed 29); `agentic-implement.js` 842 (allowed 861), 64 long (allowed 64); `Pipeline.judge` 71 (allowed 73); `runAfterPlan` 126 (allowed 128) | read |

What must not change: a `close-stage` without `@N`; the readers' diff names; `attribute`; the fingerprint formula; the verify phases; `open_ended_command`; the `reports` path; QA `kept` mode for any report that is not an environment `BLOCKER`; a finding whose evidence names no other package's file (the same object, no `scope`).

## 5. Data model

```text
close-stage item           ID=state            (as today)
                           ID=state@N          (only with --fix; N an integer >= 1)

plan (pipeline-plan JSON) + "owners": {"WP-01": ["src/a.py", "src/b/"], ...}   every package's manifest files, as written
                          + "root":   "/abs/path/of/the/repo"                  ROOT.as_posix()

finding part (a split)     the finding's fields, and:
  "wp"          the owning package
  "file"        the first of its scope (sorted), for a part that is not the original
  "scope"       [paths]  sorted, unique: the files of that package named in evidence/fix (the original part also
                         holds its own normalised "file")
  "split_from"  the original finding's fingerprint (parts other than the original)
  "fingerprint" fingerprint(part), suffixed -2, -3 … if already taken in the axis's list
  (a part other than the original has no "line")

QA report + "blocker_kind": "environment" | "design"   optional; meaningful only with status BLOCKER
          + "not_run": ["<command>", ...]               optional; the commands QA could not run

pending item of a QA environment blocker (one per not_run command):
  {"type": "needs validation", "source": "qa", "wp": null, "file": null, "kind": "qa not run",
   "problem": cmd, "claim": cmd, "fact": "not run: the environment refused it", "how_to_check": "run " + cmd}
  with no not_run: one item, cmd = "QA's validation" and how_to_check = "allow QA's test commands, then run /implement again"

QA_NOT_RUN_DETAIL = 'QA did not run: the environment refused its commands (see the pending items of kind "qa not run")'
```

## 6. Contracts between modules

**`agentic.py close-stage L ID=state[@N]... [--expect red|green] [--fix]`** (WP-01)
- `@N` is accepted only with `--fix`, with N an integer ≥ 1. Otherwise it dies with exit 1 and `close-stage: invalid entry '<item>' …` (the existing message).
- With `@N`: the ledger's `fix_count` of ID becomes N, and the diff is written to `.claude/state/runs/<ID>.fix-<N>.diff`.
- Without `@N`: exactly as today (ledger + 1).
- `GATE:`, `RESULT:` and the exit codes are unchanged. The ledger's state is the part before `@`.

**`stage.write_fix_diffs(manifest, label, attempts)`** (WP-01)
- When the tree file is missing or `git_tree()` is falsy, it writes `(the diff of this attempt could not be recorded)\n` to every attempt's file of a package with files, instead of returning.

**`findings.split_by_owner(findings, owners, root) -> list`** (WP-02)
- `findings` is one axis's confirmed list, each item with `fingerprint`. `owners` is `{wp: [files]}` (it may be `{}` or `None`). `root` is a string (it may be `""` or `None`).
- **Text matched:** `evidence` + `"\n"` + `fix` (missing ones are `""`), with `\` replaced by `/` and, when `root` is non-empty, every `root + "/"` removed. Matching and root stripping compare ASCII-lowercased copies (only `A`-`Z` lowered, never Unicode case folding, and no `re.I`), so a drive letter of another case still matches. The output keeps every path exactly as written in `owners` or in the finding (normalised `\`→`/` and root removed, case untouched).
- **Which files a package has in the text:** `mentioned(wp)` is that package's files that match like `attribute` (`.claude/bin/verification.py:286-287`), but with an ASCII word class so both engines agree. The pattern is `(?<![A-Za-z0-9_./-])` + escaped path + `(?![A-Za-z0-9_-])`, with no lookahead for a path ending in `/`. Python escapes with `re.escape`, JS with `s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')`.
- **A finding whose `wp` is not in `owners`** is treated the same: its own mentioned files are `[]`, and its `scope` holds only its normalised `file`.
- **No other package named:** when no package other than the finding's `wp` has a mentioned file, the item is returned unchanged (the same object, no `scope`).
- **Otherwise** the output holds, in this order:
  - the original, with `scope` = sorted unique (its own normalised `file`, which has the same replacements, plus `mentioned(its wp)`);
  - then, for each other package with mentioned files, in ascending id order, a part with `wp`, `file` = `scope[0]`, `scope` = sorted `mentioned(wp)`, `split_from` = the original's fingerprint, no `line`, and `fingerprint` = `fingerprint(part)`. If that fingerprint is already taken, either by any item of the input list or by a part already produced, it gets `-2`, `-3`, … as `with_fingerprints` does.
- Order is kept: each finding's group goes in its input position.
- It never raises on non-string fields: they are treated as `""`.

**Workflow `splitByOwner(findings)`** (WP-02): the same rules, reading `plan.owners` and `plan.root`. It must produce exactly what the Python function produces; the conformance scenarios of Annex A compare them.

**`findings.qa_environment_blocked(qa) -> bool`** (WP-02): `qa` is a dict with `status == "BLOCKER"` and `blocker_kind == "environment"`. The workflow mirrors it as `qaEnvironmentBlocked(qa)`.

**`findings.qa_not_run_items(qa) -> list`** and **`findings.QA_NOT_RUN_DETAIL`** (WP-02)
- Returns the items of section 5 when `qa_environment_blocked(qa)`, else `[]`.
- Non-string entries of `not_run` are skipped, and repeats are kept once, in order. A `not_run` that is missing, not a list, or has no string entry gives the single default item.
- The workflow mirrors it as `qaNotRunItems(qa)` and `QA_NOT_RUN_DETAIL` with the same text.

**Engines** (WP-02, both, equivalent):
- **Fix closes.** A fix wave's marks are `<wp>=<state>@<attempt>`, with `attempt` = the in-run count before the cycle + 1 (the same number its prompt uses). An implement wave's marks have no `@`.
- **The split.** In the full review, each axis's confirmed list goes through the split before `record` and `run.review` are built. The split parts are in `confirmed` and reach `close_review`, fixes and re-reviews like any finding. `refuted`, `advisory` and `waived` are untouched.
- **The re-review prompt** (`re_review` in the spec and inline in the workflow) appends, right after `with the line that shows it. `, the sentence `A finding with a "scope" is judged only in those files: what its evidence says about other files is another package's finding. `
- **QA's next pass.** If the standing QA report is environment-blocked, the next `qa_stage` uses mode `full` whatever the sources.
- **The end of a QA pass.** `qa_not_run_items(qa)` joins `baseline` (so `qa_pending`), after the needs-validation items. When the run ends in the "nothing eligible" branch and the standing QA is environment-blocked, `run.detail = QA_NOT_RUN_DETAIL`. The result stays `REVIEW`, because QA is `BLOCKER`.

**`launch.pipeline_plan(manifest)`** (WP-02): adds `"owners": {wp_id: list(wp["files"])}` and `"root": ROOT.as_posix()`.

**Spec** (WP-02): `schemas.qa.properties` gains `blocker_kind` (`{"type": "string", "enum": ["environment", "design"]}`) and `not_run` (`{"type": "array", "items": {"type": "string"}}`). `required` is unchanged, and the workflow's `QA_SCHEMA` copy is the same.

**`manifest_check.runs_code(tokens) -> bool`** (WP-03)
- `tokens` is a list of words. Every caller builds it as `shlex.split(text.replace("\\", "/"))`, falling back to `text.replace("\\", "/").split()` on `ValueError`. Splitting without that replacement would glue a Windows path into one word with no separators (4b).
- **Program.** The program is `tokens[0]` after its last `/` or `\`, lowercased, with a final `.exe` removed. When it is not `powershell` or `pwsh`, the answer is False.
- **Flags.** Each later token is lowercased, and a leading `/` reads as `-`.
  - A token is a *file flag* when it is `-f` or `-file`.
  - A token is a *code flag* when it is `-c`, `-e` or `-ec`; or it has 3 or more characters and `-command` starts with it; or it has 4 or more characters and `-encodedcommand` starts with it.
- **Answer.** True unless a file flag comes before every code flag. So no file flag means True.

**`manifest_check.open_ended_rule(rule)`** (WP-03): as today, and also True when the rule ends with `:*` and `runs_code(shlex-split prefix)` is True. A new set `SHELLS_ALONE = {"powershell", "pwsh", "powershell.exe", "pwsh.exe", "cmd", "cmd.exe"}` makes a one-word rule open-ended, case-insensitively. It is used by `open_ended_rule` only: `OPEN_ENDED` does not change, so `open_ended_command` keeps its behaviour for verify commands.

**`manifest_check.code_runner_commands(manifest) -> list`** (WP-03): the acceptance command and the verify commands (strings only: a missing or `None` acceptance or a non-dict `verify` is skipped; in that order, without repeats) for which `runs_code` is True, with the words built as above.

**`manifest_check.complexity_warnings(manifest)`** (WP-03): also appends, per command of `code_runner_commands`, a warning that contains the command, `-File` and `.claude/rules-library/powershell.md`. Its exact text is free.

**`installer.sync_permissions(manifest)`** (WP-03)
- For a command in `code_runner_commands`, it adds only `Bash(<cmd>)` and removes `Bash(<cmd>:*)` from `permissions.allow` if present.
- For every other command, nothing changes.
- **Output.** The existing line is unchanged. When something was removed, it adds a second line `N rule(s) removed from .claude/settings.local.json: …`.
- It is idempotent.

## 7. Conventions

- The project's own: English in code, comments and messages; standard library only; docstrings in the style of the surrounding module; no `print` debugging left.
- **The two engines stay equivalent.** Every behaviour of WP-02 lands in `pipeline.py` and in `agentic-implement.js` with the same output, and `conformance.json` scenarios prove it (`test_pipeline.ConformanceTests`).
- **The workflow script has no disk:** it cannot import `findings.py`. The JS mirrors are kept beside `fingerprint` (`.claude/workflows/agentic-implement.js:236-253`) and must give the same results.
- **Quality ratchet:** no file or function may pass its allowance (4b's last row). A new file has no baseline entry, so none of its lines may exceed 120 characters: this holds for `test_fix_routing.py`, `test_fix_attempts.py`, `test_owner_split.py` and `test_code_runner_rules.py` (split long literals such as AC-008's Windows paths). A package may compact code of its own files to make room (for example one-line object literals in the workflow's schemas), without changing behaviour. `quality-baseline.json` is not edited.
- **Errors:** `die()` for CLI misuse, with the existing message forms. The engines never raise on an agent's malformed report: they treat a missing field as absent.
- **Commits:** imperative subject, `Fixes #NNN` lines in the body of the last commit of each package.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · A fix's diff carries the run's attempt number, whatever the ledger holds (reproduces issue 140)
  - Scenario: the CLI test repo of `.claude/bin/test_agentic.py` (WP-02 owns `src/b/`). `src/b/x.py` contains `v1`, the ledger's `WP-02.fix_count` is 3 (left by earlier runs), and `.claude/state/runs/WP-02.fix-1.diff` contains `STALE`.
  - Action: `open-stage 1`; write `v2` to `src/b/x.py`; `close-stage 1 WP-02=done@1 --fix`.
  - Expected: `runs/WP-02.fix-1.diff` contains `+v2` and not `STALE`; the ledger's `WP-02.fix_count` is 1; `runs/WP-02.fix-4.diff` does not exist.
  - Must not: write `fix-4`, or leave `STALE`.
  - Check: `test_fix_routing.py`.
  - WP: WP-01

- AC-002 · An attempt whose diff cannot be computed overwrites the file with a placeholder; `@N` needs `--fix`
  - Scenario: as AC-001, after `open-stage 1`, delete `.claude/state/tree-1.txt`.
  - Action: `close-stage 1 WP-02=done@1 --fix`; then, in a fresh stage, `close-stage 1 WP-02=done@1` (no `--fix`) and `close-stage 1 WP-02=done@0 --fix`.
  - Expected: `runs/WP-02.fix-1.diff` is exactly `(the diff of this attempt could not be recorded)\n`. The two later calls exit 1, and their stderr contains `invalid entry` (`die` prints there, `.claude/bin/core.py:192-196`).
  - Must not: `STALE` survive; an `@N` accepted without `--fix`.
  - Check: `test_fix_routing.py`.
  - WP: WP-01

- AC-003 · Both engines number each fix close by the in-run attempt
  - Scenario: the conformance scenario `a defect that does not get fixed is capped` (QA reports a high implementation defect on WP-03 on every pass).
  - Action: run it in the fallback engine (`test_pipeline.run_scenario`) and in the workflow (`node .claude/bin/test_workflow.mjs --dump`).
  - Expected: in both, the gates that contain ` --fix` are exactly `close-stage 2 WP-03=done@1 --fix` then `close-stage 2 WP-03=done@2 --fix`; the second `implementer:WP-03 (fix)` prompt contains `.claude/state/runs/WP-03.fix-1.diff`; the two summaries are equal.
  - Must not: a fix gate without `@`; an implement-wave gate with `@`.
  - Check: `test_fix_routing.py` (the workflow part skipped without `node`, as `ConformanceTests` is).
  - WP: WP-02

- AC-004 · A finding that names another package's files is split and each part goes to its owner (reproduces issue 141)
  - Scenario: the conformance scenario `a finding that names another package's files is split` (Annex A).
  - Action: run it in both engines.
  - Expected:
    - Both engines give `result` `OK` and `fix_cycles` 1, and the summaries are equal.
    - `implementer:WP-01 (fix)#1` and `implementer:WP-03 (fix)#1` are both called.
    - WP-03's fix prompt contains `"wp":"WP-03"`, `"file":"src/c.py"`, `"scope":["src/c.py"]` and `"split_from":"F`.
    - WP-01's contains `"scope":["src/a.py"]` and not `"scope":["src/c.py"]`.
    - The summary's `re_review` is `{"spec": [0, 0, 0], "standards": [2, 0, 0]}`: both parts were open and both were addressed.
  - Must not: only WP-01 fixed; a `fix limit reached` pending item; a split when `owners` is absent (every existing scenario keeps its summary).
  - Check: `test_fix_routing.py`.
  - WP: WP-02

- AC-005 · `split_by_owner`'s edges and the re-review's scope sentence
  - Scenario: direct calls to `findings.split_by_owner`, and the re-review prompt of the AC-004 scenario.
  - Action:
    - Call it with `owners = {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["lib/util.py"]}` and `root = "C:/repo"`, on findings whose evidence is (a) `src/a.py:3 only`, (b) `C:\repo\src\b\x.py:7 and src/a.py:3`, and (c) `util.py:9`.
    - Separately, call it on two findings of the same rule and problem that both name `src/b/x.py`.
  - Expected:
    - (a) is returned as the same object, with no `scope`.
    - (b) gives two items, the original WP-01 one with `scope` `["src/a.py"]` (its `file` being `src/a.py`), then a WP-02 part with `file` `src/b/` and `scope` `["src/b/"]`.
    - (c) is unchanged: `util.py` is not `lib/util.py`.
    - The two WP-02 parts get different fingerprints, the second ending in `-2`.
    - The AC-004 scenario's `standards-reviewer:standards-reviewer (re-review)#1` prompt contains `A finding with a "scope" is judged only in those files`.
  - Must not: a part with a `line`; `owners=None` or `{}` raising.
  - Check: `test_fix_routing.py`.
  - WP: WP-02

- AC-006 · QA that the environment blocked is pending, and the run says so (reproduces issue 142)
  - Scenario: the conformance scenario `QA blocked by the environment is pending, not a verdict` (Annex A).
  - Action: run it in both engines.
  - Expected:
    - Both engines give `result` `REVIEW`, `fix_cycles` 0 and `detail` exactly `QA_NOT_RUN_DETAIL`, and the summaries are equal.
    - The raw result's `pending`, from `test_pipeline.raw_run` (the summaries hold only pending types, so this field check is on the fallback engine; the workflow's equality comes from the summaries), holds an item with `kind` `qa not run`, `claim` `powershell -NoProfile -NonInteractive -File build/Invoke-Tests.ps1` and `how_to_check` `run powershell -NoProfile -NonInteractive -File build/Invoke-Tests.ps1`.
    - With `blocker_kind` `design` (a variant built in the test), `detail` is `None` and no `qa not run` item exists.
  - Must not: `detail` `None` in the environment case; a `qa not run` item from a `FAIL` or `PASS` report.
  - Check: `test_fix_routing.py`.
  - WP: WP-02

- AC-007 · An environment-blocked QA report is never kept
  - Scenario: the conformance scenario `QA blocked by the environment is called again after a standards-only fix` (Annex A).
  - Action: run it in both engines.
  - Expected: `qa_passes` is `["full", "full"]`, the result is `OK`, and there are 2 `qa:qa` calls in both.
  - Must not: `["full", "kept"]`. The existing scenario `a standards-only fix keeps the QA report` must still give `["full", "kept"]`.
  - Check: `test_fix_routing.py`.
  - WP: WP-02

- AC-008 · `validate` rejects PowerShell prefix rules that run code (issue 118)
  - Scenario: the manifest of `.claude/bin/test_manifest_check.py` (`MANIFEST`) with one `allow_bash` rule at a time.
  - Action: `agentic.validate(...)` for each rule.
  - Expected:
    - An error containing `too broad` for each of these: `Bash(powershell -NoProfile -NonInteractive -Command Invoke-Pester:*)`, `Bash(pwsh -c Invoke-Pester:*)`, `Bash(C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command x:*)`, `Bash(powershell -NoProfile Invoke-Pester:*)`, `Bash(pwsh -EncodedCommand AAAA:*)`, `Bash(powershell -Command x -File y.ps1:*)`, `Bash(pwsh:*)`, `Bash(powershell)`.
    - No error for any of these: `Bash(powershell -NoProfile -NonInteractive -File build/Invoke-Tests.ps1:*)`, `Bash(pwsh -f build/Invoke-Tests.ps1:*)`, `Bash(powershell -ExecutionPolicy Bypass -File build/t.ps1:*)`, `Bash(powershell -NoProfile -NonInteractive -Command Invoke-Pester -EnableExit)`.
    - A verify command `powershell -NoProfile -NonInteractive -Command "Invoke-Pester -EnableExit"` gives no error.
  - Must not: reject the exact `-Command` rule or the verify command; accept a `-Command` before `-File`.
  - Check: `test_fix_routing.py`.
  - WP: WP-03

- AC-009 · `sync-permissions` writes only the exact rule for a PowerShell code command and removes the old `:*`
  - Scenario: the CLI test repo, with `verify.tests` = `powershell -NoProfile -NonInteractive -Command "Invoke-Pester -EnableExit"`. `.claude/settings.local.json` allows `Read` and `Bash(powershell -NoProfile -NonInteractive -Command "Invoke-Pester -EnableExit":*)`.
  - Action: `agentic.py sync-permissions`, twice.
  - Expected:
    - `allow` contains `Read` and `Bash(powershell -NoProfile -NonInteractive -Command "Invoke-Pester -EnableExit")`, and does not contain the `:*` form.
    - The first run's output contains `removed`.
    - The second run leaves `allow` unchanged.
    - The repo's other verify commands keep both forms.
  - Must not: the `:*` form present after the sync; any other rule removed.
  - Check: `test_fix_routing.py`.
  - WP: WP-03

- AC-010 · The warning and the guidance point to a runner script with `-File`
  - Scenario: the CLI test repo with the verify command of AC-009; the repository's `.claude/rules-library/powershell.md` and `.claude/commands/architect.md`.
  - Action: `agentic.py validate`; read the two files.
  - Expected:
    - `validate` exits 0, and one stdout line starts with `warning:` and contains `Invoke-Pester -EnableExit`, `-File` and `powershell.md`.
    - `powershell.md` contains `-File build/Invoke-Tests.ps1` and `Bash(powershell -NoProfile -NonInteractive -File build/Invoke-Tests.ps1:*)`, and contains no `-Command "Invoke-` (neither Pester nor ScriptAnalyzer). Its table keeps the rows `build`, `types`, `lint`, `tests`.
    - `architect.md`'s line that starts with ``- **`allow_bash`:**`` contains `-File`.
  - Must not: the warning for a command without PowerShell.
  - Check: `test_fix_routing.py`.
  - WP: WP-03

- AC-011 · Docs, agents' definitions and release 2.21.2
  - Scenario: the repository's files.
  - Action: read them.
  - Expected:
    - **Release.** `plugin.json` version is `2.21.2`. `upgrade.NOTES["2.21.2"]` is the key right above `"2.21.1"`, with a note containing `@N`, one containing `scope`, one containing `qa not run` and one containing `-File`. `test_acceptance_v221.py` and `test_failure_evidence.py` pin `2.21.2`.
    - **Agents' definitions.** `.claude/agents/qa.md` contains `blocker_kind` and `not_run`. `.claude/agents/reviewer.md` and `.claude/agents/standards-reviewer.md` each contain `one finding per package`.
    - **Docs.** `docs/how-it-works.md` contains `scope`, `blocker_kind` and `qa not run`. Its line that starts `- **Fix attempt:**` contains `in this run`. The line of `implement.md` that contains `` `qa_passes` `` also contains `environment`.
  - Must not: `2.21.2` anywhere in `docs/how-it-works.md`.
  - Check: `test_fix_routing.py`.
  - WP: WP-04

### Work packages

#### WP-01 · close-stage numbers a fix attempt as the engine says
- Wave: 1.
- Files: `.claude/bin/stage.py`, `.claude/bin/agentic.py` (usage text only), `.claude/bin/test_fix_attempts.py` (new).
- Implements: `close-stage … ID=state@N … --fix`, `write_fix_diffs`'s placeholder (section 6). Consumes nothing new.
- ACs: AC-001, AC-002.
- **Patterns to mirror:**
  - `.claude/bin/stage.py:236-277`: the parsing loop and its `die` message. Split `state` on `@` after the existing `partition("=")`.
  - `.claude/bin/stage.py:284-304`: keep the per-package loop and `MAX_DIFF_BYTES`; the early return becomes a placeholder loop.
  - `.claude/bin/test_agentic.py:572-583`: how a CLI test opens a stage, edits a file and reads the diff.
- **Gotchas:**
  - `marks` must keep `(jid, state)` with the bare state: `gate_line` and the ledger read it.
  - Compute the attempts list once. Today the ledger is read before the update loop and `+ 1` is applied twice, once for the ledger and once for the diffs. With `@N`, both use N.
  - `@N` without `--fix`, a non-integer or N < 1 is an invalid entry (exit 1, from `die`).
  - `test_agentic.py:485-490` still expects `fix_count` 2 after two closes without `@N`.
  - The placeholder is written only for a package with files (as today's loop).
  - The usage text at `agentic.py:14` and `:219` is rewritten in English: `close-stage L ID=state[@N]... [--expect red|green] [--fix]`, and `Usage:` in the `die`.
  - **Expected failure in wave 1:** `test_lean.test_the_flow_stays_within_its_budget` may fail because the code grew. WP-04 raises the budget in wave 2. Report it in `not_checked`, not as `BLOCKED`. Every other test must pass.
- **Exact imports and APIs:** `ledger_read`, `ledger_update`, `stage_of`, `entities`, `LEDGER_STATES`, `wps`, `STATE`, `ROOT` already imported in `stage.py`. `git_tree()` at `.claude/bin/stage.py:65`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-02 · The engines number fixes, split findings by owner and treat an environment-blocked QA as pending
- Wave: 1.
- Files: `.claude/bin/findings.py`, `.claude/bin/pipeline.py`, `.claude/workflows/agentic-implement.js`, `.claude/workflows/pipeline-spec.json`, `.claude/bin/launch.py`, `.claude/bin/conformance.json`, `.claude/bin/test_pipeline.py`, `.claude/bin/test_workflow.mjs`, `.claude/bin/test_owner_split.py` (new).
- Implements: `split_by_owner`, `qa_environment_blocked`, `qa_not_run_items`, `QA_NOT_RUN_DETAIL`, their JS mirrors, the engines' contract, `pipeline_plan`'s `owners`/`root` and the spec's QA fields. It consumes `close-stage … ID=state@N --fix` by signature (WP-01). The simulated worlds answer every gate with a canned output, so nothing of WP-01 needs to run.
- ACs: AC-003, AC-004, AC-005, AC-006, AC-007.
- **Patterns to mirror:**
  - `.claude/bin/verification.py:277-295`: the path matching (copy the regex, not the criteria part).
  - `.claude/bin/findings.py:70-94` and `.claude/workflows/agentic-implement.js:236-253`: how a Python helper and its JS mirror sit side by side.
  - `.claude/bin/pipeline.py:567-609` and `.claude/workflows/agentic-implement.js:568-616`: where the confirmed lists are built.
  - `.claude/bin/pipeline.py:656-678` and `.claude/workflows/agentic-implement.js:688-712`: the QA modes.
  - `.claude/workflows/agentic-implement.js:283` and `.claude/workflows/agentic-implement.js:290-295`: the pending item's shape.
  - `.claude/bin/test_pipeline.py:405-414`: a test reading a named scenario's gates.
- **Gotchas:**
  - **The split's place.** Split after verification, on the confirmed list only, so the verifier is called once per original finding (`agents` and `agent_calls` of existing scenarios unchanged).
  - **Fingerprint collisions.** The fingerprint of a part is computed with its new `file`. Suffix collisions against every fingerprint of the input list and every part already produced.
  - **Normalising `file`.** The original's `file` can be absolute with backslashes (the real run: `C:\Users\…\XMM.RemoteServices.psm1`). Normalise it the same way as the text before putting it in `scope`.
  - **Missing plan keys.** `plan.owners`/`plan.root` are absent in every existing scenario's plan. Treat them as `{}`/`""`, so no split and no change to existing summaries.
  - **The prompt is the same text in both engines.** Python's `compact` and JS's `JSON.stringify` must see the same key order: build the part as `{...f, wp, file, scope, split_from, fingerprint}` in both, deleting `line`.
  - **The re-review sentence** goes into `pipeline-spec.json`'s `re_review` after `{diffs}`'s sentence and into the workflow's inline prompt at the same place (`.claude/workflows/agentic-implement.js:634-635`). The test of the prompt's head (`.claude/bin/test_workflow.mjs:602-611`) stays green.
  - **QA mode.** `full` when the standing report is environment-blocked: check it before the `kept` test.
  - **`detail`** is set only in the "nothing eligible" branch. A later `stop()` overrides it as today.
  - **Room under the quality ratchet** (4b's last row). `pipeline.py` has 10 lines of room and `Pipeline.judge` 2: put the logic in `findings.py` and keep `judge`'s additions to calls of it. The workflow has 19 lines of room and no new line over 120 characters, and `runAfterPlan` has 2. Put `splitByOwner`, `qaEnvironmentBlocked`, `qaNotRunItems` and `QA_NOT_RUN_DETAIL` at top level next to `fingerprint`, and compact the workflow's own schema literals (`.claude/workflows/agentic-implement.js:25-170`) if room is short (for example `type` and `required` on one line; every line at most 120 characters, since the file has 0 long lines of room), keeping them deep-equal to the spec (`.claude/bin/test_workflow.mjs:587-600`).
  - **Annex A's scenarios** are added to `conformance.json` verbatim. Their names are what the acceptance tests look up.
  - **Pinned gate strings.** Update `test_pipeline.py:414` to `close-stage 1 WP-01=blocker@1 --fix` and `test_workflow.mjs:186`/`:422` to `close-stage 1 WP-02=done@1 --fix`.
  - **`runAfterPlan` has 2 lines of room** and needs both the QA items in `baseline` and the `detail`. Make each a call of one top-level helper, or extend existing lines within 120 characters.
  - **The JS mirror is tested** through Annex A's scenarios (compared with Python by `ConformanceTests`) and, if wanted, extra `simulate()` cases in `test_workflow.mjs`. The workflow is one async body, so its functions cannot be imported by another script. `test_owner_split.py` tests the Python functions only.
  - **Expected failure in wave 1:** `test_lean.test_the_flow_stays_within_its_budget` may fail because the code grew. WP-04 raises the budget in wave 2. Report it in `not_checked`, not as `BLOCKED`. Every other test must pass.
- **Exact imports and APIs:**
  - `from findings import blocks, text_sum, waiver_for, with_fingerprints` plus the new names (`.claude/bin/pipeline.py:19`); `findings.fingerprint`.
  - `launch.py` already has `wps`, `ROOT` (`from core import …`).
  - Workflow: `plan` (the parsed JSON, `.claude/workflows/agentic-implement.js:553`).
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`, `node .claude/bin/test_workflow.mjs`, `python3 .claude/bin/agentic.py quality`.

#### WP-03 · No PowerShell rule runs arbitrary code, and the subset of a suite can be allowed
- Wave: 1.
- Files: `.claude/bin/manifest_check.py`, `.claude/bin/installer.py`, `.claude/rules-library/powershell.md`, `.claude/commands/architect.md`, `.claude/bin/test_code_runner_rules.py` (new).
- Implements: `runs_code`, `open_ended_rule`'s PowerShell case, `SHELLS_ALONE`, `code_runner_commands`, the warning in `complexity_warnings` and `sync_permissions`' change (section 6). Consumes nothing new.
- ACs: AC-008, AC-009, AC-010.
- **Patterns to mirror:**
  - `.claude/bin/manifest_check.py:39-60`: how a rule's prefix is tokenised and judged.
  - `.claude/bin/manifest_check.py:78-97`: a warning's wording.
  - `.claude/bin/installer.py:115-129`: the settings file's read/modify/write and its print.
  - `.claude/bin/test_manifest_check.py:27-37`: a table of commands with `subTest`.
- **Gotchas:**
  - **Tokenising.** `open_ended_rule` today splits on spaces. For `runs_code`, replace `\` by `/` first, then `shlex.split` (falling back to `.split()` on `ValueError`), so `C:\…\powershell.exe` keeps its separators and a quoted argument stays one token (4b).
  - **The lint row too.** `powershell.md`'s lint row also moves to a runner with `-File` (for example `build/Invoke-Lint.ps1`). The table keeps its four rows (`.claude/bin/test_definitions.py:318-328`).
  - **Expected failure in wave 1:** `test_lean.test_the_flow_stays_within_its_budget` may fail because the code and prompt bytes grew. WP-04 raises the budget in wave 2. Report it in `not_checked`, not as `BLOCKED`. Every other test must pass.
  - **Order of flags.** A `-Command` before `-File` runs code: `-File`'s script receives nothing.
  - **Where `code_runner_commands` lives.** It belongs in `manifest_check.py`, and `installer.py` imports it the way it imports from `core` (check `installer.py`'s import list at the top: add `from manifest_check import code_runner_commands`). Running `python3 .claude/bin/agentic.py sync-permissions` must keep working, so check there is no import cycle.
  - **The runner script in `powershell.md`** is an example the project writes in its own repo. Show it whole, under 15 lines: `param([string[]]$Path = '.')`, then `Invoke-Pester -Path $Path -EnableExit -OutputFile test-results.xml -OutputFormat NUnitXml`. Show the verify line and the `allow_bash` rule for it, and say why `-Command` is exact-only. Pester 3.4 and 5 accept `-Path`, `-EnableExit` and `-OutputFormat NUnitXml` in their legacy parameter set (not measured here: section 11).
  - **`architect.md`'s bullet** must still contain "Minimal and concrete" (the plan-review prompt quotes it). Add: every command a package's validation runs needs a prefix rule that covers it, and PowerShell uses `-File`.
- **Exact imports and APIs:** `shlex` (already imported in `manifest_check.py`), `json`, `ROOT` (in `installer.py`).
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-04 · Docs, agents' definitions and release 2.21.2
- Wave: 2, depends on WP-01, WP-02 and WP-03. `flow-budget.json` measures the code the other packages wrote, and the docs describe it as built.
- Files: `docs/how-it-works.md`, `docs/how-to/README.md`, `.claude/commands/implement.md`, `.claude/agents/qa.md`, `.claude/agents/reviewer.md`, `.claude/agents/standards-reviewer.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_acceptance_v221.py`, `.claude/bin/test_failure_evidence.py` (its two version pins only, lines 225 and 241).
- Implements: nothing callable. Consumes every contract of section 6 by implementation.
- ACs: AC-011.
- **Patterns to mirror:**
  - `.claude/bin/upgrade.py:156-163`: a fix release's notes, right above the previous key.
  - `.claude/bin/test_acceptance_v221.py:138-145`: the pin.
  - `docs/how-it-works.md:392`: a one-line fact per bullet.
  - `.claude/agents/qa.md:67`: the status line to extend.
- **Gotchas:**
  - **QA's definition.** Explain when `blocker_kind` is `environment` (a command refused, a tool missing, the suite will not start for reasons outside the code) and when it is `design`, and that `not_run` lists the exact commands.
  - **Both reviewers' definitions.** Say "one finding per package": a breach that spans files owned by different packages is reported once per owning package, each with its own `wp` and `file`.
  - **`docs/how-it-works.md:392`** becomes "N is the attempt number in this run".
  - **`docs/how-to/README.md` is at its cap of 260 lines** (`.claude/bin/test_field_fixes.py:389`, `qa/test_qa_docs.py:57`): extend line 204 in place and add no line.
  - **`flow-budget.json`:** raise only what is exceeded (run `python3 -m unittest discover -s .claude/bin -p test_lean.py`), with its why.
  - **`implement.md`** is pinned by `test_quality_limits.py` and `test_definitions.py` (`zone_suspects`, `gate_denials`). Extend the `qa_passes` line (59) and the status line (51); add no new line mentioning those.
  - **`.claude/flow-history.json`** is regenerated by the maintainer as the last commit, not by this package.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`, `python3 .claude/bin/agentic.py quality`, `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs:*)", "Bash(python3 .claude/bin/agentic.py quality)"],
  "acceptance": {"files": [".claude/bin/test_fix_routing.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_fix_routing.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/stage.py", ".claude/bin/agentic.py", ".claude/bin/test_fix_attempts.py"],
     "acs": ["AC-001", "AC-002"], "mirror": [".claude/bin/stage.py:236-277", ".claude/bin/stage.py:284-304", ".claude/bin/test_agentic.py:572-583"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/findings.py", ".claude/bin/pipeline.py", ".claude/workflows/agentic-implement.js", ".claude/workflows/pipeline-spec.json", ".claude/bin/launch.py", ".claude/bin/conformance.json", ".claude/bin/test_pipeline.py", ".claude/bin/test_workflow.mjs", ".claude/bin/test_owner_split.py"],
     "acs": ["AC-003", "AC-004", "AC-005", "AC-006", "AC-007"], "mirror": [".claude/bin/verification.py:277-295", ".claude/bin/findings.py:70-94", ".claude/workflows/agentic-implement.js:236-253", ".claude/bin/pipeline.py:567-609", ".claude/workflows/agentic-implement.js:568-616", ".claude/bin/pipeline.py:656-678", ".claude/workflows/agentic-implement.js:688-712", ".claude/bin/test_pipeline.py:405-414"]},
    {"id": "WP-03", "wave": 1, "depends_on": [], "files": [".claude/bin/manifest_check.py", ".claude/bin/installer.py", ".claude/rules-library/powershell.md", ".claude/commands/architect.md", ".claude/bin/test_code_runner_rules.py"],
     "acs": ["AC-008", "AC-009", "AC-010"], "mirror": [".claude/bin/manifest_check.py:39-60", ".claude/bin/manifest_check.py:78-97", ".claude/bin/installer.py:115-129", ".claude/bin/test_manifest_check.py:27-37"]},
    {"id": "WP-04", "wave": 2, "depends_on": ["WP-01", "WP-02", "WP-03"], "files": ["docs/how-it-works.md", "docs/how-to/README.md", ".claude/commands/implement.md", ".claude/agents/qa.md", ".claude/agents/reviewer.md", ".claude/agents/standards-reviewer.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_acceptance_v221.py", ".claude/bin/test_failure_evidence.py"],
     "acs": ["AC-011"], "mirror": [".claude/bin/upgrade.py:156-163", ".claude/bin/test_acceptance_v221.py:138-145", "docs/how-it-works.md:392", ".claude/agents/qa.md:67"]}
  ]
}
```

## 9. Test strategy

- **Acceptance** (`test_fix_routing.py`, written first and red):
  - AC-001 and AC-002 run `agentic.py` in the CLI test repo of `test_agentic.py`.
  - AC-003 to AC-007 run the named conformance scenarios through `test_pipeline.run_scenario`, and through `test_workflow.mjs --dump` (skipped without `node`), plus direct calls to `findings.split_by_owner`.
  - AC-008 to AC-010 call `agentic.validate` and the CLI.
  - AC-011 reads files.
  - Nothing is spent.
- **Unit tests:**
  - `test_fix_attempts.py`: `@N` parsing, the ledger value and the placeholder.
  - `test_owner_split.py`: directories, root stripping (with a drive letter of another case), backslashes, ordering, collisions, a `wp` outside `owners`, non-string fields and the QA helpers, on the Python functions. The JS mirror is held equal through Annex A's scenarios in `ConformanceTests`.
  - `test_code_runner_rules.py`: a `runs_code` table (abbreviations, `/` flags, `.exe` and paths, the order of `-File` and `-Command`), `sync_permissions` idempotence.
- **Conformance:** the three scenarios of Annex A, compared key by key by `ConformanceTests`.
- **Teeth:** each behaviour is broken once by hand, and an acceptance test must fail:
  - the ledger + 1 used instead of `@N`;
  - no split in one engine;
  - `kept` for an environment `BLOCKER`;
  - the PowerShell check removed.
- **By hand, before the pull request:** `acceptance/`, `qa/`, `bench/`, and `agentic.py flow-history` as the last commit with its `--check`.

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| The engine passes the attempt number (`ID=state@N`) | Reset the ledger's `fix_count` and delete old diffs at `pipeline-plan` | Two counters that must agree by convention broke once already. The engine knows the number it put in the prompt, so it names the file. A reset would also need care with `--resume` and the manual `run-wave --fix` cap |
| `@N` only with `--fix`; no `@N` keeps today's behaviour | Make `@N` mandatory with `--fix` | The manual stage-by-stage commands and their tests use `--fix` alone |
| Placeholder diff instead of an early return | Keep the early return | An early return leaves whatever an earlier run wrote under that number |
| Split confirmed findings by the files their evidence/fix names (user's choice) | Reviewer prompt only; a third re-review verdict that reroutes | The prompt is not enforced. A reroute verdict spends a fix cycle before the right package is asked. The split is deterministic and reuses `attribute`'s matching |
| Split after verification | Split before verifying | The verifier would be called once per part: more calls and no new evidence |
| A part's `scope` and one sentence in the re-review prompt | A per-part re-review schema | The re-reviewer only needs to know where to look. Schemas stay as they are |
| `owners`/`root` in the plan, the JS mirror beside `fingerprint` | A gatekeeper step that splits | A gatekeeper call costs an agent call and a step, and the workflow already mirrors `findings.py` |
| QA environment blocker stays `REVIEW`, explained in `detail` and pending (user's choice) | `OK` when verification is green | QA's validation did not happen; `OK` would claim it did |
| `blocker_kind` and `not_run` optional | Required | A QA agent of an older definition still validates; absent means `design`, which is today's behaviour |
| Reject `powershell`/`pwsh` prefix rules without `-File` first (user's choice) | Warn only | `-Command X:*` lets an agent run any code: the same class as `Bash(python3:*)`, already rejected |
| Do not reject a verify or acceptance command that uses `-Command` | Reject it | The flow runs it exactly, and the PowerShell pack recommended it until now. `sync-permissions` makes it exact-only, and `validate` warns |
| `sync-permissions` removes only the `:*` form of the current code commands | Scan and clean every rule | It removes only what it would have written; the user's own rules are theirs (an invalid one in `allow_bash` is already a `validate` error) |
| The warning in `complexity_warnings` | A new warnings function printed by `agentic.py` | No change to `agentic.py` by WP-03 (WP-01 owns it). The function's docstring is widened |
| Patch release 2.21.2 (user's choice) | 2.22.0 | Bug fixes, and the QA schema gains optional fields only |
| Contracts first: WP-01, WP-02 and WP-03 in wave 1 | WP-02 after WP-01 | The engines' scenarios answer `close-stage` with canned output; nothing of WP-01 needs to run |
| WP-04 in wave 2 | Wave 1 | The budget measures the code written, and the docs describe it as built |

## 11. Risks and open questions

- **Auto mode and allow rules.** Not reproduced: no Windows session with auto mode here. The design assumes an allow rule that matches the command lets it run without the classifier. If the classifier still refuses matched commands, issue 142's pending items will say so, and issue 118 stays open for that part.
- **Pester's parameters in the runner example** (`-Path`, `-EnableExit`, `-OutputFormat NUnitXml` in Pester 3.4 and 5) are not measured here, so the example is marked as such in `powershell.md`.
- **PowerShell's own parsing of abbreviations** is wider than the rule's (for example `-co` is ambiguous in `pwsh`). The rule errs toward rejecting. A legitimate rule that is rejected can always be rewritten with `-File`.
- **Basenames in evidence.** A reviewer who quotes `x.py:3` for `src/b/x.py` does not trigger a split (whole-path matching, as `attribute`). The reviewers' definitions ask for paths, and the real run quoted root-level files by name, which are whole paths.
- **Room under the quality ratchet** is tight in both engines (4b). WP-02 may need to compact its own schema literals.
- **Wrapped commands are still open.** Two-word prefix rules such as `Bash(cmd /c x:*)` or `Bash(bash -c x:*)` are accepted today and stay accepted: issue 118 is closed for PowerShell only. A wider rule is a later design.
- **`verify` does not run `acceptance/` or `qa/`.** A regression there shows only in the by-hand run before the pull request (section 9), as in earlier designs. WP-04 runs both in its validation.

No question blocks a WP.

## Annex A · Conformance scenarios

Added to `.claude/bin/conformance.json`'s `scenarios`, verbatim (key order free):

```json
{"name": "a finding that names another package's files is split",
 "plan": {"owners": {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["src/c.py"]}, "root": "/repo"},
 "standards": [{"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
   {"wp": "WP-01", "file": "/repo/src/a.py", "line": 3, "problem": "SPLIT-PROBLEM", "evidence": "src/a.py:3 `x = 255`; src/c.py:7 `y = 255`",
    "fix": "one named constant", "if_skipped": "drift", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]},
   {"status": "PASS", "axis": "standards", "findings": [], "not_checked": []}]}

{"name": "QA blocked by the environment is pending, not a verdict",
 "qa": [{"status": "BLOCKER", "blocker_kind": "environment", "not_run": ["powershell -NoProfile -NonInteractive -File build/Invoke-Tests.ps1"],
         "plan": [], "defects": [], "gaps": ["the permission classifier denied the test command"], "needs_validation": []}]}

{"name": "QA blocked by the environment is called again after a standards-only fix",
 "standards": [{"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
   {"wp": "WP-02", "file": "src/b/x.py", "line": 3, "problem": "STANDARDS-PROBLEM", "evidence": "e", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]},
   {"status": "PASS", "axis": "standards", "findings": [], "not_checked": []}],
 "qa": [{"status": "BLOCKER", "blocker_kind": "environment", "not_run": ["pytest"], "plan": [], "defects": [], "gaps": [], "needs_validation": []},
        {"status": "PASS", "plan": [], "defects": [], "gaps": [], "needs_validation": []}]}
```

`a defect that does not get fixed is capped` (AC-003) already exists and is not changed.
