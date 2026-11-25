# Architecture: a Standards finding pinned by an acceptance test goes to a person, not to a fix (issue 145; agentic-flow 2.22.1)
Type: fix · Size: standard

## 1. Goal

A field run (PowerShell, native engine, ≤ 2.21.1) ended `REVIEW` with build, tests (1537/0) and acceptance green. The acceptance test of AC-810 greps the source for `ShowBalloonTip(10000`. The sequence, read from its `workflow-result.json`: the wave wrote a named constant (as section 7 asks), verification failed AC-810 (`verification_failures[0].fix_cycle: 0`, before any fix cycle), fix 1 put the literal back, the Standards reviewer confirmed "No magic numbers" on that line (`F68e7a69e`), fix 2 (the escalation model) knowingly left the literal and said why, the re-review said NOT_ADDRESSED and the run ended with a `fix limit reached` item that reads as an implementer failure.

This release does two things:
1. **Detection, deterministic.** After every review, a new read-only command `agentic.py pinned` checks each confirmed Standards reflex finding with a line: if a string literal of an acceptance test, read as code text, occurs on that line, the finding leaves the fix queue and becomes a blocking pending item of type `acceptance conflict`, which names the test. No fix cycle is spent on it, in both engines.
2. **Prevention, in wave 0.** The test-author is told not to assert on source text when the behaviour can be observed through section 6, and never to pin a form section 7 or the rules forbid; the test-auditor reports such a pin as a blocking finding.

## 2. Scope

### Included

- `agentic.py pinned FILE:LINE ...`: one JSON line with the pins it found; exit 0 whatever happens.
- `findings.py`: which findings are checked, how the command's answer splits them, and the pending item; mirrored in the workflow.
- Both engines: the check in the review's close; the pending list `acceptance conflict`; `review.standards.pinned`.
- Four conformance scenarios (Annex A).
- `test-author.md` and `test-auditor.md`: one rule and one checklist item.
- Release 2.22.1: notes, `/implement`'s presentation, `how-it-works.md`, the budget, the 2.22.0 acceptance file's version pin.

### Excluded (non-goals)

- Spec-axis findings, floor-tier findings and finish notes: never checked (a pin does not excuse a correctness or security defect).
- A finding the reviewer gave without `line`, or the parts `split_by_owner` makes (they have no line): never checked.
- JavaScript regex literals (`/.../`), string concatenations, values held in variables: not recognised as pins. A pin the command does not see behaves as today.
- The verification failure that comes first when the wave writes the form the rules ask for (fix 1 of the field run): left to the prevention in wave 0.
- An implementer reporting a conflict, and the Standards reviewer declaring one (both discussed and declined: section 10).
- Auto-waiving: the conflict blocks; the person decides.
- A change to `/architect` or the plan-reviewer about criteria that pin code text (section 11).

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The repository's own suites, which CI also runs (`.github/workflows/agentic-flow-ci.yml:70-71`): `python3 -m unittest discover -s acceptance` and `python3 -m unittest discover -s qa`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`
- Bench: `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/bin/repo_scan.py                 WP-01  pin_fragments, find_pins, pinned (the command), the PIN_* constants
.claude/bin/agentic.py                   WP-01  cmd_pinned, COMMANDS, the usage line, the import
.claude/bin/launch.py                    WP-01  "pinned" in SEQ_COMMANDS
.claude/bin/test_pinned.py               WP-01  new: unit cases of the command and its helpers
.claude/bin/test_definitions.py          WP-01  the command count (line 510): 37 -> 38
.claude/bin/findings.py                  WP-02  PIN_PATH, PIN_MAX_ARGS, ACCEPTANCE_CONFLICT_DECISION, pinned_args, split_pinned, conflict_item
.claude/bin/pipeline.py                  WP-02  close_review checks pins; conflict_pending; pending_now
.claude/workflows/agentic-implement.js   WP-02  the same, in the native engine, with mirrors of the findings.py helpers
.claude/bin/conformance.json             WP-02  four scenarios (Annex A)
.claude/bin/test_pipeline.py             WP-02  the simulated world answers `pinned`
.claude/bin/test_workflow.mjs            WP-02  the same
.claude/bin/test_pinned_findings.py      WP-02  new: unit cases of the findings.py helpers
.claude/agents/test-author.md            WP-03  rule 2 extended
.claude/agents/test-auditor.md           WP-03  checklist item and severity
.claude/commands/implement.md            WP-03  the pending item and review.standards.pinned
docs/how-it-works.md                     WP-03  one paragraph
.claude-plugin/plugin.json               WP-03  2.22.1
.claude/bin/upgrade.py                   WP-03  NOTES["2.22.1"]
.claude/flow-budget.json                 WP-03  code lines and prompt bytes, with the why
.claude/bin/test_acceptance_v222.py      WP-03  its version pin (line 229): 2.22.1
.claude/bin/test_pinned_conflict.py      AT
.claude/quality-baseline.json            by hand: agentic-implement.js's stored lines, raised in WP-02's commit if needed
.claude/flow-history.json                by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| A read-only analysis command: one JSON line on stdout, a warning on stderr, exit 0 even on error, `EMPTY_*` shape plus `error` | `.claude/bin/repo_scan.py:270-283` | Copy this shape for `pinned` | read |
| Module constants with a comment each (`CALLERS_PER_SYMBOL`, `CALLERS_MAX`…) | `.claude/bin/repo_scan.py:178-186` | Name every `PIN_*` limit the same way, and give each a one-line comment (these have none) | read |
| `repo_scan.py` imports from `core` in one block | `.claude/bin/repo_scan.py:13-16` | Add `at_entity` there | read |
| Commands: a `cmd_*` wrapper, the `COMMANDS` table, the usage docstring line, the import from `repo_scan` | `.claude/bin/agentic.py:40`, `.claude/bin/agentic.py:101`, `.claude/bin/agentic.py:315-316`, `.claude/bin/agentic.py:427-439` | `pinned` joins each | read |
| `test_commands_match_the_docstring` holds the usage docstring and `COMMANDS` equal, and pins their count at 37 | `.claude/bin/test_definitions.py:507-510` | Add the usage line; change 37 to 38 | read |
| `seq` accepts only `SEQ_COMMANDS` | `.claude/bin/launch.py:49-50`, `.claude/bin/launch.py:493-509` | Add `"pinned"` | read |
| The fallback's gate runs each command with `shlex.split` and merges stdout then stderr | `.claude/bin/launch.py:476-491`, `.claude/bin/launch.py:624-626` | A path with spaces or quotes cannot be an argument: such findings are not checked | read |
| The acceptance zone: `at_entity(manifest)["files"]`, `acceptance/` by default; `owns(pattern, path)` | `.claude/bin/core.py:231-234`, `.claude/bin/core.py:262-264` | | read |
| `source_files()`: git's tracked and untracked files, without dependency folders | `.claude/bin/core.py:329-339` | Acceptance tests written in wave 0 are untracked and still listed | read |
| `findings.py` is pure (no flow imports), mirrored by the workflow; `_without_root` strips the repo root and reads `\` as `/` | `.claude/bin/findings.py:1-8`, `.claude/bin/findings.py:109-122` | New helpers live here; the JS mirrors them | read |
| A pending item built by a helper with a module constant (`QA_NOT_RUN_DETAIL`, `_not_run_item`) | `.claude/bin/findings.py:22-23`, `.claude/bin/findings.py:168-190` | `conflict_item` and `ACCEPTANCE_CONFLICT_DECISION` follow it | read |
| The workflow's mirror of those helpers | `.claude/workflows/agentic-implement.js:219-232` | `pinnedArgs`, `splitPinned`, `conflictItem` go beside it | read |
| `noRoot` (JS mirror of `_without_root`) and `plan.root` | `.claude/workflows/agentic-implement.js:180-190`, `.claude/workflows/agentic-implement.js:194-196` | | read |
| Pending lists and `pendingNow`; `pendingKey` for dedupe | `.claude/workflows/agentic-implement.js:266-270`, `.claude/workflows/agentic-implement.js:306-318` | Add `conflictPending` after `limitPending` | read |
| `closeReview`: sets `lastConfirmed`, closes review, opens QA | `.claude/workflows/agentic-implement.js:709-722` | The pin check goes at its start | read |
| `run.review` is built before `closeReview` in both review paths; `review.standards.waived` is set there | `.claude/workflows/agentic-implement.js:640-657`, `.claude/workflows/agentic-implement.js:697-707` | `closeReview` overwrites `standards.confirmed` and `confirmed`, and sets `standards.pinned` | read |
| `seq` with one command calls the gate directly; `step`, `ok`, `lastJson` | `.claude/workflows/agentic-implement.js:107-135` | | read |
| The result decides `REVIEW` when any pending item `blocks` | `.claude/workflows/agentic-implement.js:868-871`, `.claude/bin/pipeline.py:654-655` | A conflict item has `tier: "reflex"`, and the result's check passes no waivers, so it always blocks (a waived finding is never confirmed, so never pinned) | read |
| The fallback: `__init__` lists, `pending_now`, `close_review` | `.claude/bin/pipeline.py:42-53`, `.claude/bin/pipeline.py:139-140`, `.claude/bin/pipeline.py:570-576` | The same change as the workflow | read |
| `pipeline.py` imports from `findings` in one block | `.claude/bin/pipeline.py:17-19` | | read |
| A hand fix (`run-wave --fix`) reads only `confirmed` of each axis from the run record | `.claude/bin/launch.py:341-348` | A pinned finding is never fixed by hand: no change needed (AC-001 checks the record) | read |
| The simulated worlds: every gate command's default answer | `.claude/bin/test_pipeline.py:54-78`, `.claude/bin/test_workflow.mjs:29-41` | Add `pinned` → `{"pinned": [], "skipped": []}` | read |
| `run_scenario` returns a summary; `world` + `pipeline.Pipeline` give the full result | `.claude/bin/test_pipeline.py:204-208` | The AT reads `pending` items from the full result | read |
| The happy path makes exactly 10 gatekeeper calls | `.claude/bin/test_workflow.mjs:345-352` | No `pinned` call without a candidate | read |
| A scenario's declaration (standards findings, `gate_fail` with an output) | `.claude/bin/conformance.json:908-930`, `.claude/bin/conformance.json:996-1025` (scenarios "callers reach the reviewer" and "a reflex finding blocks until it is fixed") | Annex A uses the same keys | read |
| Unit tests of findings helpers, header and style | `.claude/bin/test_owner_split.py:1-30` | | read |
| Command tests in a temporary repo (`Repo`, `MANIFEST` with `acceptance/`) | `.claude/bin/test_agentic.py:34-75`, `.claude/bin/test_agentic.py:906-916` | | read |
| Release notes: newest first after `2.11.0`'s entry; `2.22.0` at line 156 | `.claude/bin/upgrade.py:156-163` | `2.22.1` goes right before `2.22.0` | read |
| `/implement`'s pending bullets | `.claude/commands/implement.md:63-67` | One bullet for `acceptance conflict` | read |
| The 2.22.0 acceptance file pins the version, and forbids other test files from pinning `2.22.0` or `2.21.2` | `.claude/bin/test_acceptance_v222.py:226-252` | Change only line 229 to `"2.22.1"` | read |
| Quality ratchet: functions ≤ 60 lines, nesting ≤ 4, lines ≤ 120 chars; `agentic-implement.js` is stored at 890 lines and 64 long lines (allowance 920 lines, 64 long lines); `pipeline.py` at 29 long lines | `.claude/quality-baseline.json`, `.claude/bin/quality.py:232-235` | No new line over 120 characters in either engine. The JS's 30-line growth is likely not enough (estimate 30-40 lines, not measured): its stored `lines` is raised by hand in WP-02's commit, with the reason in the message, as `ea92ec5` did (831 → 890) | read |
| The test-author's black-box rule and the auditor's checklist | `.claude/agents/test-author.md:17-25`, `.claude/agents/test-auditor.md:20-36` | | read |
| The auditor reads the AT brief, which ends with the rules since 2.22.0 | `.claude/agents/test-auditor.md:18`, design 0032 | It can tell a forbidden form | read |
| The field run's sequence (wave wrote the constant; fix 1 restored the literal; fix 2 left it) | issue 145; `verification_failures` recorded with `run.fix_cycles` before `fixCycle` increments it (`.claude/workflows/agentic-implement.js:545`, `.claude/workflows/agentic-implement.js:829-832`) | | inferred |

What must NOT change: the happy path's gate calls; prompts and schemas (`pipeline-spec.json` is untouched); spec findings; waivers; the re-review's verdict handling.

## 5. Data model

```python
# findings.py
PIN_PATH = r"[A-Za-z0-9_.@-]+(?:/[A-Za-z0-9_.@-]+)*"  # a repo-relative path the gate can pass unquoted
PIN_MAX_ARGS = 40                                      # arguments of one pinned call, so the command stays short
ACCEPTANCE_CONFLICT_DECISION = (
    "the fix would break the acceptance test that pins this line's text: change the test to check behaviour, "
    "or waive this rule for this file in the plan's waivers")

# repo_scan.py
PIN_PATH = r"[A-Za-z0-9_.@-]+(?:/[A-Za-z0-9_.@-]+)*"  # the same pattern as findings.PIN_PATH (AC-003 holds them equal)
PIN_MIN_CHARS = 8           # a shorter fragment pins nothing
PIN_CODE_CHARS = "()[]{}=;"  # a fragment must hold one: it is code text, not a word or a message
PIN_WINDOW = 1              # lines around the finding's line that are searched
PIN_MAX_BYTES = 262144      # a larger acceptance file is not read
PIN_TEXT_MAX = 160          # characters of the fragment reported
EMPTY_PINNED = {"pinned": [], "skipped": []}
```

A pin, as the command reports it:

```json
{"file": "src/w.ps1", "line": 2, "test": "acceptance/t.Tests.ps1", "test_line": 5, "text": "ShowBalloonTip(10000"}
```

A pinned finding: the finding with `"pinned_by": {"test", "test_line", "text"}`. The pending item:

```json
{"type": "acceptance conflict", "source": "standards-reviewer", "...the pinned finding's fields...": "",
 "decision": "<ACCEPTANCE_CONFLICT_DECISION>"}
```

`run.review.standards.pinned`: the pinned findings of that review (`[]` when none). The run's result gains no new key.

## 6. Contracts between modules

### C1 · `agentic.py pinned [FILE:LINE ...]` (WP-01; consumed by WP-02 by signature, by the AT)

- Order: with no arguments, it prints the empty shape at once; otherwise it reads the manifest first (a missing manifest is the error path), then checks the arguments.
- Prints one JSON line on stdout, `{"pinned": [pin, ...], "skipped": [arg, ...]}`, and exits 0. On any unexpected exception: a line `[agentic] pinned skipped: <Type>: <msg>` on stderr, then `{"pinned": [], "skipped": [], "error": "<Type>: <msg>"}`, exit 0. With no arguments: `{"pinned": [], "skipped": []}` without reading the manifest.
- **An argument** is split at its last `:`. It is skipped (listed in `skipped`, once, in argument order) when the path does not fully match `PIN_PATH`, has a segment `.` or `..`, the line part does not fully match `[1-9][0-9]*`, or `ROOT / path` is not a file. The source file is read with the same rules as the tests (UTF-8 with `errors="replace"`, `\r` stripped; larger than `PIN_MAX_BYTES`: skipped). A test file that is the finding's own file is not searched for that argument (a test never pins itself). A repeated argument is ignored after its first appearance.
- **The tests**: the files of `source_files()` owned by any pattern of `at_entity(load_manifest())["files"]` (`owns`), in sorted order, each at most `PIN_MAX_BYTES` bytes (larger ones are left out), read as UTF-8 with `errors="replace"`, split on `\n` with `\r` stripped.
- **`pin_fragments(line) -> list[str]`** (pure): for each match, in order, of `'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"` in the line, its content is split on `\.\*\??|\.\+\??|\\[sSdDwW][*+?]?|[*^$]`; each piece has `\\(.)` replaced by the character, is stripped of whitespace, and is kept when it has at least `PIN_MIN_CHARS` characters and contains at least one character of `PIN_CODE_CHARS`. `'ShowBalloonTip\(10000'` gives `["ShowBalloonTip(10000"]`; `'*Get-Item -Path*'` gives `[]` (no code character); `"a(b"` gives `[]` (too short).
- **`find_pins(path, line, tests) -> dict | None`** (pure over text): `tests` is `[(test_path, [lines])]`. The source window is lines `max(1, line - PIN_WINDOW) .. line + PIN_WINDOW` of `path` (those that exist). The answer is the first `(test_path, test_line, fragment)`, in the order test path, test line ascending, fragment order, whose fragment occurs as a substring of a window line; `text` is the fragment cut to `PIN_TEXT_MAX` characters. `None` when nothing matches.
- `pinned` lists at most one pin per argument, in argument order.

### C2 · `findings.py` (WP-02; mirrored in the workflow)

- `pin_path(finding, root) -> str | None`: `None` unless the finding is a dict with `tier == "reflex"`, a `line` that is an `int` (not a `bool`) and ≥ 1, and a non-empty string `file`. The path is `_without_root(file, root)` (`root` a string, else `""`); `None` unless it fully matches `PIN_PATH` and has no segment `.` or `..`.
- `pinned_args(findings, root) -> list[str]`: `f"{pin_path(f, root)}:{f['line']}"` for each finding with a path, in order, without repeats, the first `PIN_MAX_ARGS`.
- `split_pinned(findings, root, answer) -> (kept, pinned)`: `answer` is the command's parsed JSON or `None`. Its usable pins are the entries of `answer["pinned"]` (when `answer` is a dict and that is a list) that are dicts with a string `file`, `test` and `text` and integer `line` and `test_line` (a `bool` is not an integer in Python; a float such as `3.0` is not one either. The command only prints ints, so JS's `Number.isInteger` is enough there). A finding is pinned when its `pin_path` and `line` equal a usable pin's `file` and `line` and its argument is among `pinned_args(findings, root)`. `kept`: the other findings, the same objects, in order. `pinned`: copies of the pinned ones with `"pinned_by": {"test", "test_line", "text"}` from that pin, in order. A malformed answer pins nothing.
- `conflict_item(finding) -> dict`: `{"type": "acceptance conflict", "source": "standards-reviewer", **finding, "decision": ACCEPTANCE_CONFLICT_DECISION}`.
- JS mirrors, same names in camelCase: `pinPath(f)`, `pinnedArgs(findings)`, `splitPinned(findings, answer)` returning `{ kept, pinned }`, `conflictItem(f)`, all reading `plan.root` through `str(plan.root)`, with `PIN_PATH`, `PIN_MAX_ARGS` and `ACCEPTANCE_CONFLICT_DECISION` equal to the Python values. `Number.isInteger` stands for the `int` check, and the JS `PIN_PATH` is anchored (`new RegExp('^(?:' + PIN_PATH + ')$')`) because Python uses `fullmatch`.

### C3 · The engines' review close (WP-02)

At the start of `closeReview(byAxis)` (JS) and `close_review(by_axis)` (Python), before anything else:

1. `args = pinnedArgs(byAxis.standards)` (Python: `pinned_args(by_axis["standards"], self.plan.get("root"))`; `split_pinned` takes the same root). When empty: no gate call, `run.review.standards.pinned = []`, and the rest is as today.
2. Otherwise one gate call, alone, labelled `pinned`: the command `pinned <args joined by one space>`. Its answer is `lastJson(output)` when the step exists and exited 0, else `null`.
3. `{kept, pinned} = splitPinned(byAxis.standards, answer)`; `byAxis` becomes `{spec, standards: kept}`. Each pinned finding's `conflictItem` joins `conflictPending` (`self.conflict_pending`) unless an item with the same `pendingKey` is there.
4. `run.review.standards.confirmed = kept`, `run.review.standards.pinned = pinned`, `run.review.confirmed = [...spec, ...kept]`.
5. The rest of today's `closeReview` runs with the new `byAxis`: `lastConfirmed`, the `REVIEW=pass|fail` mark (from what is left) and the returned `confirmed` exclude the pinned findings.

`pendingNow()` / `pending_now()` become `[...qaPending, ...limitPending, ...conflictPending, ...concernPending, ...newPending]`. `conflictPending` starts empty and is kept for the whole run.

## 7. Conventions

- English for code, comments, prompts and docs; the repository's existing style.
- Standard library only. `findings.py` keeps no import from the flow.
- No line over 120 characters in any file you touch; functions ≤ 60 lines, nesting ≤ 4 (`agentic.py quality`).
- Every limit is a named module constant with a one-line comment.
- The JS mirror and the Python helper keep the same names (camelCase in JS) and the same behaviour; a comment above the JS mirror names the Python function.
- A command that analyses never stops the flow: on error it prints its empty shape with `error` and exits 0.
- Docs and notes never name a flow version except in `upgrade.NOTES` and `plugin.json`.
- Commit messages: `type: summary` in lowercase (`feat:`, `fix:`, `test:`, `release:`, `design:`, `chore:`), ending with the session's attribution lines.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · A pinned reflex finding goes to pending without a fix, in both engines (the bug of issue 145)
  - Scenario: Annex A scenario "a reflex finding pinned by an acceptance test goes to pending". Today both engines send the finding to WP-02 as a fix.
  - Action: the fallback engine runs it (`test_pipeline.run_scenario`, and `test_pipeline.world` + `pipeline.Pipeline` for the full result); the native one through `node .claude/bin/test_workflow.mjs --dump`.
  - Expected: the gates contain `pinned src/b/x.py:3` exactly once; `fix_cycles` 0; `result` `REVIEW`; `pending` types `["acceptance conflict"]`; that item has `wp` `WP-02`, `file` `/repo/src/b/x.py`, `tier` `reflex`, `pinned_by` `{"test": "acceptance/test_x.py", "test_line": 12, "text": "limit(10000"}` and `decision` equal to `findings.ACCEPTANCE_CONFLICT_DECISION`; in the full result `review.standards.confirmed` is `[]`, `review.standards.pinned` has 1 item, and `launch._record_items(result, "STANDARDS", False)` (what a hand fix reads) is `[]`. Both engines agree on result, failed_stage, detail, fix_cycles, pending, gates, gate_calls, agents and prompts.
  - Must not: any implementer call labelled `(fix)`; a `fix limit reached` item; the result `OK`.
  - Check: `test_pinned_conflict.py`, AC-001 tests.
  - WP: WP-02
- AC-002 · A `pinned` step that fails or answers no JSON changes nothing
  - Scenario: Annex A scenario "a pinned step that cannot answer leaves the finding to be fixed".
  - Action: both engines run it.
  - Expected: the gates contain `pinned src/b/x.py:3` exactly once; `fix_cycles` 1; `result` `OK`; `pending` `[]`; both engines agree as in AC-001.
  - Must not: a stop; an `acceptance conflict` item.
  - Check: `test_pinned_conflict.py`, AC-002 tests.
  - WP: WP-02
- AC-003 · Only Standards reflex findings with a line and a passable path are checked
  - Scenario: Annex A scenario "only reflex findings with a line are checked for pins"; the default happy path (no findings); unit calls of the helpers.
  - Action: both engines run the two runs; `findings.pinned_args` and `findings.split_pinned` are called directly.
  - Expected: in the scenario, no gate starts with `pinned`, `fix_cycles` 1, `result` `OK`. The happy path makes no `pinned` call (the native engine's 10 gatekeeper calls stand). `pinned_args` of `[reflex line 3 file "/repo/src/a.py", reflex line 3 same file, reflex line True, reflex line 0, finish line 3, reflex file "src/a b.py" line 3, reflex file "../x.py" line 3, reflex with no line]` with root `/repo` is `["src/a.py:3"]`; 45 distinct reflex findings with lines give 40 arguments. `split_pinned` with the answers `None`, `{}`, `{"pinned": "x"}` and `{"pinned": [{"file": "src/a.py", "line": "3", "test": "t", "test_line": 1, "text": "x"}]}` pins nothing and returns the same objects. `findings.PIN_PATH == repo_scan.PIN_PATH`.
  - Must not: a spec, floor or finish finding checked; a finding pinned by an entry for another line.
  - Check: `test_pinned_conflict.py`, AC-003 tests.
  - WP: WP-02
- AC-004 · A pinned finding leaves the re-review and stays pending while another is fixed
  - Scenario: Annex A scenario "a pinned finding is not re-reviewed and stays pending".
  - Action: both engines run it.
  - Expected: the gate `pinned src/b/x.py:3 src/b/x.py:9` exactly once; one fix cycle (a `WP-02 (fix)` call); the standards re-review prompt contains the fingerprint (`findings.fingerprint` of the finding with `"axis": "standards"`) of the line-9 finding and not that of the line-3 one; `result` `REVIEW`; `pending` `["acceptance conflict"]`; both engines agree as in AC-001.
  - Must not: a second `pinned` gate (nothing reflex is left confirmed after the re-review); the line-3 finding's problem text in a fix prompt.
  - Check: `test_pinned_conflict.py`, AC-004 tests.
  - WP: WP-02
- AC-005 · `pinned` finds a literal of an acceptance test on the finding's line
  - Scenario: a temporary repo (the `Repo` of `test_agentic.py`, whose manifest has `acceptance.files` = `["acceptance/"]`). `src/w.ps1`: line 1 `param()`, line 2 `  $n.ShowBalloonTip(10000, 'a', 'b', 'Info')`, line 3 `# end`, line 4 `Write-Output ('ok')`. `acceptance/t.Tests.ps1`: lines 1-4 `# t`, line 5 `        $src | Should -Match 'ShowBalloonTip\(10000'`. `tests/u.Tests.ps1` (outside the zone) line 1: `"Write-Output ('ok')"`.
  - Action: `agentic.py pinned src/w.ps1:2`, then `agentic.py pinned src/w.ps1:4`.
  - Expected: the first prints, as its last stdout line, `{"pinned": [{"file": "src/w.ps1", "line": 2, "test": "acceptance/t.Tests.ps1", "test_line": 5, "text": "ShowBalloonTip(10000"}], "skipped": []}`, exit 0. The second prints `{"pinned": [], "skipped": []}`, exit 0 (line 4 is two lines from line 2; the literal that matches line 4 sits outside the zone).
  - Must not: a pin from a file outside the acceptance zone; an exit other than 0.
  - Check: `test_pinned_conflict.py`, AC-005 tests.
  - WP: WP-01
- AC-006 · `pinned` ignores weak fragments, skips bad arguments, and never fails
  - Scenario: the repo of AC-005, with `acceptance/t.Tests.ps1` lines 6-8: `'ShowBalloonTip'`, `'(10000'`, `'*Get-Item -Path*'`; and `src/v.ps1` line 1 `ShowBalloonTip ; (10000 ; Get-Item -Path x`.
  - Action: `agentic.py pinned src/v.ps1:1 src/w.ps1:0 src/w.ps1:x ../w.ps1:2 src/none.ps1:1 src/w.ps1 src/w.ps1:2 src/w.ps1:2`; then `agentic.py pinned src/w.ps1:2` in a repo whose `architecture.md` has no manifest block and which also holds `src/w.ps1`.
  - Expected: the first prints `{"pinned": [<the AC-005 pin>], "skipped": ["src/w.ps1:0", "src/w.ps1:x", "../w.ps1:2", "src/none.ps1:1", "src/w.ps1"]}` (nothing for `src/v.ps1:1`; `src/w.ps1:2` once), exit 0. The second: exit 0, a last line with `"pinned": []` and a string `error`.
  - Must not: a pin from a fragment shorter than 8 characters or without a character of `()[]{}=;`; a traceback with a non-zero exit.
  - Check: `test_pinned_conflict.py`, AC-006 tests.
  - WP: WP-01
- AC-007 · The test-author and the test-auditor are told
  - Scenario: the repository's definitions.
  - Action: read `.claude/agents/test-author.md` and `.claude/agents/test-auditor.md`.
  - Expected: `test-author.md` has a line that contains both `source text` and `section 7`; `test-auditor.md` has a line that starts with `   - **Pins the code's form:**` and contains `High`, and the first bullet under its `# Severity` heading contains `pins a form`.
  - Must not: the checklist item outside the numbered step 3 of the auditor's process (it must sit after the **Wrong** item).
  - Check: `test_pinned_conflict.py`, AC-007 test.
  - WP: WP-03
- AC-008 · Release 2.22.1
  - Scenario: the repository.
  - Action: read the release files; run `python3 .claude/bin/agentic.py quality`.
  - Expected: `.claude-plugin/plugin.json`'s version, as a tuple of ints, is ≥ `(2, 22, 1)`; `upgrade.NOTES["2.22.1"]` exists, its key comes right before `"2.22.0"` in `list(upgrade.NOTES)`, some note contains `acceptance conflict` and some contains `pinned`; `.claude/commands/implement.md` has exactly one line containing `` `acceptance conflict` ``; `docs/how-it-works.md` contains `acceptance conflict` and `agentic.py pinned` and does not contain `2.22.1`; `quality` exits 0.
  - Must not: a line of `test_acceptance_v222.py` that contains both `plugin["version"]` and `"2.22.0"`.
  - Check: `test_pinned_conflict.py`, AC-008 test (flow repo only).
  - WP: WP-03

### Work packages

#### WP-01 · The `pinned` command
- Wave 1.
- Files: `.claude/bin/repo_scan.py`, `.claude/bin/agentic.py`, `.claude/bin/launch.py`, `.claude/bin/test_pinned.py`, `.claude/bin/test_definitions.py` (line 510 only: `37` → `38`).
- Implements C1. Defines its own `PIN_PATH` (section 5); it imports nothing from `findings.py`.
- ACs: AC-005, AC-006.
- **Patterns to mirror:** `.claude/bin/repo_scan.py:270-283` (the command's shape, stderr warning, exit 0); `.claude/bin/repo_scan.py:178-186` (constants); `.claude/bin/agentic.py:315-316` and `.claude/bin/agentic.py:427-439` (wrapper and table); `.claude/bin/test_agentic.py:906-916` (a command test in a temporary `Repo`).
- **Gotchas:**
  - `pinned(args)` takes the argument list: `cmd_pinned(args)` calls `pinned(args)`.
  - Print the JSON with `ensure_ascii=False` and call `sys.exit(0)` at the end, as `callers` does.
  - `load_manifest()` raises `ManifestError` when the block is missing: that is the "unexpected exception" path (error JSON, exit 0).
  - Fragments come from the test's literal only; the source window is searched for the fragment as a plain substring.
  - Known red before integration (not yours to fix; never touch `flow-budget.json`): the AC-001..004 tests of `test_pinned_conflict.py` and its `PIN_PATH` equality check (WP-02), and `test_lean` (the budget, WP-03). Any other red test is yours.
- **WP validation note:** run `test_pinned.py` first; the full suite is only expected green after integration.
- **Exact imports and APIs:** add `at_entity` to the existing `from core import (...)` block (`load_manifest`, `owns`, `source_files`, `ROOT` are already there); `re`, `json`, `sys` are already imported.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p test_pinned.py`; `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · Both engines route a pinned finding to pending
- Wave 1.
- Files: `.claude/bin/findings.py`, `.claude/bin/pipeline.py`, `.claude/workflows/agentic-implement.js`, `.claude/bin/conformance.json`, `.claude/bin/test_pipeline.py`, `.claude/bin/test_workflow.mjs`, `.claude/bin/test_pinned_findings.py`.
- Implements C2 and C3; consumes C1 by signature (its output shape; the simulated worlds answer for it).
- ACs: AC-001, AC-002, AC-003, AC-004.
- **Patterns to mirror:** `.claude/bin/findings.py:168-190` (a helper and its constant); `.claude/workflows/agentic-implement.js:219-232` (the JS mirror); `.claude/workflows/agentic-implement.js:709-722` and `.claude/bin/pipeline.py:570-576` (the close you change); `.claude/bin/test_owner_split.py:1-30` (unit tests of helpers); `.claude/bin/test_pipeline.py:54-78` (the world's defaults).
- **Gotchas:**
  - The check runs in the close, after the verifiers: a pinned finding was confirmed first (a refuted one is never checked).
  - In the re-review, `closeReview` receives the still-confirmed findings of every package (not only the fixed ones): any reflex one with a line is checked again. That is intended (a fix may have restored a pinned form).
  - `run.review` already exists when `closeReview` runs, in both paths; overwrite `standards.confirmed` and `confirmed`, and set `standards.pinned` even when empty.
  - The gate call is a lone command, not part of the close's `seq`: the close's `REVIEW=` mark depends on its answer.
  - Existing scenarios with a reflex finding with a line (for example "a reflex finding blocks until it is fixed") now make one more gate call in both engines; they keep passing because the engines are compared with each other and the default answer pins nothing.
  - `agentic-implement.js` may not gain a line over 120 characters (64 stored). Its line allowance is 920; keep the mirrors compact (one line per short helper, as `tierOf` and `inScope` are). If it still ends above 920, `.claude/quality-baseline.json`'s `lines` for that file is set by hand to the measured count in WP-02's commit, saying why; never any other entry, never `long_lines`.
  - Known red before integration (not yours to fix; never touch `flow-budget.json`): every test of `test_pinned_conflict.py` except AC-001..004 and AC-003's `PIN_PATH` equality; `test_lean` (the budget, WP-03); and, without WP-01, `test_definitions.py`'s `test_workflow_calls_existing_commands` and `test_cited_commands_exist` (`pinned` is not a command yet). Any other red test is yours.
  - New engine tests go in `test_pinned_findings.py` or `test_workflow.mjs`, not in `test_pipeline.py` (732 lines, limit 800).
  - `test_pinned_findings.py` also reads `agentic-implement.js` as text and checks that its `PIN_PATH`, `PIN_MAX_ARGS` and `ACCEPTANCE_CONFLICT_DECISION` literals equal the Python ones.
  - Python `bool` is an `int`: exclude it explicitly.
  - JS `str(plan.root)` is the existing helper (`.claude/workflows/agentic-implement.js:193`).
- **Exact imports and APIs:** in `pipeline.py`, extend `from findings import (...)` with `conflict_item, pinned_args, split_pinned`; `lines_json` (already imported from `pipeline_parts`) parses the answer; `self.seq([cmd], "pinned")`, `self.step(res, 0)`, `self.ok(st)`, `pending_key`. In the workflow: `seq`, `step`, `ok`, `lastJson`, `pendingKey`, `noRoot`, `str`.
- **The JS item:** add a test to `test_workflow.mjs` that runs Annex A's first scenario and checks the `acceptance conflict` item's `pinned_by` and `decision` (the dump shows only pending types).
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p test_pinned_findings.py`; `node .claude/bin/test_workflow.mjs`; `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-03 · Definitions, documentation and release 2.22.1
- Wave 2 (it measures the code and prompts the other packages changed).
- Files: `.claude/agents/test-author.md`, `.claude/agents/test-auditor.md`, `.claude/commands/implement.md`, `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_acceptance_v222.py`.
- Depends on WP-01 and WP-02 by implementation (the budget counts their lines; the docs describe their behaviour).
- ACs: AC-007, AC-008.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-163` (a release's notes); `.claude/commands/implement.md:63-67` (pending bullets); `.claude/agents/test-auditor.md:20-36` (checklist and severity); `.claude/agents/test-author.md:17-25` (rules).
- **What to write:**
  - `test-author.md`, rule 2 gains: "Do not assert on the source text of production code when the behaviour can be observed through section 6. When a criterion can only be checked by reading the source, assert the smallest fragment it needs, and never pin a form that section 7 or the rules forbid (a bare literal where a named constant is required, for example): the implementer could not satisfy both." (The line must contain `source text` and `section 7`.)
  - `test-auditor.md`, a new checklist item after **Wrong**: `   - **Pins the code's form:** a test that reads a production file as text and asserts a fragment of it. High when the fragment holds a form section 7 or the rules forbid (the fix the Standards reviewer would ask for breaks the test); medium when the behaviour could be observed through section 6 instead.` The severity section's first bullet gains: `, or a test that pins a form section 7 or the rules forbid`.
  - `implement.md`, a pending bullet after **Concerns**: `  - **Acceptance conflicts** (items of type `acceptance conflict`): a Standards finding on a line whose text an acceptance test pins (`pinned_by`: the test, its line and the text). No fix was attempted: the person changes the test to check behaviour, or adds a waiver for that rule and file.` And the Review bullet for Standards adds `and the findings an acceptance test pins (`pinned`)`.
  - `how-it-works.md`: a paragraph after the fix-cycle paragraph (line 155) explaining `agentic.py pinned`, the reflex-with-a-line candidates, the literal heuristic and its limits (no regex literals, no variables), the `acceptance conflict` item, and the two prevention rules. No version number.
  - `plugin.json` → `2.22.1`; `upgrade.NOTES["2.22.1"]` before `"2.22.0"`, two notes (the detection with `acceptance conflict` and `agentic.py pinned`; the test-author and test-auditor rules), naming issue 145.
  - `flow-budget.json`: re-measure with `python3 -c "import sys; sys.path.insert(0, '.claude/bin'); import test_lean; from pathlib import Path; print(test_lean.code_lines(Path('.')), test_lean.prompt_bytes(Path('.')))"`, and write the `why` for 2.22.1 (design 0033), with the measured deltas.
  - `test_acceptance_v222.py:229`: `"2.22.0"` → `"2.22.1"`, nothing else.
- **Gotchas:** `test_acceptance_v222.py` forbids any other test file from pinning `"2.22.0"` or `"2.21.2"` in a line with `version`. `test_lean.py` holds the budget to a two-sided 5 % band: measure after WP-01 and WP-02 are in.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 -m unittest discover -s acceptance`; `python3 -m unittest discover -s qa`; `python3 .claude/bin/agentic.py quality`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)", "Bash(python3 .claude/bin/agentic.py quality)"],
  "acceptance": {"files": [".claude/bin/test_pinned_conflict.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_pinned_conflict.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/repo_scan.py", ".claude/bin/agentic.py", ".claude/bin/launch.py", ".claude/bin/test_pinned.py", ".claude/bin/test_definitions.py"],
     "acs": ["AC-005", "AC-006"], "mirror": [".claude/bin/repo_scan.py:270-283", ".claude/bin/repo_scan.py:178-186", ".claude/bin/agentic.py:315-316", ".claude/bin/agentic.py:427-439", ".claude/bin/test_agentic.py:906-916"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/findings.py", ".claude/bin/pipeline.py", ".claude/workflows/agentic-implement.js", ".claude/bin/conformance.json", ".claude/bin/test_pipeline.py", ".claude/bin/test_workflow.mjs", ".claude/bin/test_pinned_findings.py"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004"], "mirror": [".claude/bin/findings.py:168-190", ".claude/workflows/agentic-implement.js:219-232", ".claude/workflows/agentic-implement.js:709-722", ".claude/bin/pipeline.py:570-576", ".claude/bin/test_owner_split.py:1-30", ".claude/bin/test_pipeline.py:54-78"]},
    {"id": "WP-03", "wave": 2, "depends_on": ["WP-01", "WP-02"], "files": [".claude/agents/test-author.md", ".claude/agents/test-auditor.md", ".claude/commands/implement.md", "docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_acceptance_v222.py"],
     "acs": ["AC-007", "AC-008"], "mirror": [".claude/bin/upgrade.py:156-163", ".claude/commands/implement.md:63-67", ".claude/agents/test-auditor.md:20-36", ".claude/agents/test-author.md:17-25"]}
  ]
}
```

## 9. Test strategy

- **Unit:** WP-01 in `test_pinned.py` (`pin_fragments`, `find_pins` and the command through `Repo`); WP-02 in `test_pinned_findings.py` (`pin_path`, `pinned_args`, `split_pinned`, `conflict_item`). The JS mirrors are held equal by the conformance scenarios (`test_pipeline.ConformanceTests`).
- **Acceptance (AT, wave 0):** `.claude/bin/test_pinned_conflict.py`, written before the code, red until WP-01 and WP-02 exist. Engine criteria use the scenario names of Annex A with `test_pipeline.run_scenario` and `node .claude/bin/test_workflow.mjs --dump` (skip the native half without `node`, as `test_acceptance_v222.EngineCase` does); the full fallback result (for `pending` items and `review`) comes from `test_pipeline.world(decl)` and `pipeline.Pipeline(test_pipeline.SPEC, gate, agent, parallel=lambda thunks: [t() for t in thunks]).execute()`. A missing scenario raises an `AssertionError` that names it (red for the right reason). AC-008 is skipped outside the flow repo (`core.is_flow_repo`). The AT must not pin `"2.22.0"` or `"2.21.2"` in a line with `version`.
- **QA:** exploratory: a temporary repo with a Python test pinning `"MAX = 3"` style text and a PowerShell one, the command run by hand; the gate's `seq pinned ...` form; a finding with an absolute Windows path and a root of another case.
- Everything runs with the commands of section 3. Executed by hand, as every design that touches `.claude/` (design 0016).

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| The conflict is a blocking pending item (`acceptance conflict`, tier reflex) | Non-blocking item; an automatic waiver | User's choice. A waiver needs who decided (`validate` demands it); an acceptance test that pins form may itself be wrong. |
| Deterministic detection by a command | The implementer declares a conflict in its fix report; the Standards reviewer marks `pinned_by` | User's choice. Neither depends on an agent following a new instruction; the implementer route still spends the cycle the issue complains about. |
| Prevention in the test-author and a narrow auditor finding | Auditor blocks every source-text assertion; no prevention | User's choice. A blanket rule would stop wave 0 for legitimate static checks ("does not call Invoke-Expression") after one revision. |
| Only Standards reflex findings with a line | Spec and floor findings too | A pin never excuses a correctness or security defect; reflex is the tier a waiver could cover. |
| One check point, the review's close | Before the verifiers (saves a verifier call) | One insertion point per engine covers the full review and the re-review alike; the verifier call is the price. |
| Fragment must hold one of `()[]{}=;` and 8+ characters; window ±1 line | Any literal; exact line only; ±2 | Messages and names in tests (`'Get-Item -Path'`, `"file not found"`) would otherwise pin lines their tests only observe; a reviewer's line can be one off. The thresholds are not measured. |
| Paths matching `PIN_PATH` only | Quoting arguments | The fallback splits with `shlex` and the workflow's gatekeeper copies the command; a path with spaces would break both. Such findings behave as today. |
| A fail-open step (no answer → nothing pinned) | Stop the run | It is an instrument, like `callers`: it never makes a run worse than today. |
| Version 2.22.1 | 2.23.0 | A fix release, as 2.21.1 and 2.21.2 were, although it adds a command (as 2.21.2 added `validate` checks). |
| AT in a named file `test_pinned_conflict.py`, with no exact version pin | A `test_acceptance_v2221.py` | `test_acceptance_v222.py` requires it to be the only `test_acceptance*` file; patch releases add named files (design 0031). |
| Reuse `source_files`, `at_entity`, `owns`, `_without_root`, `pendingKey` | New scanners | Already tested. |

## 11. Risks and open questions

- **False positives** (a reflex finding whose line holds code text an acceptance test also quotes, while the fix would not touch that text): the finding goes to a person instead of a fix. Bounded by the code-character rule and the ±1 window; not measured.
- **False negatives** (regex literals, concatenations, variables, multi-line pins): the run behaves as today. Not measured.
- **The first wasted cycle of the field run** (the wave writes the form the rules ask for, the pin fails verification) is only addressed by the prompts of WP-03; prompt changes are not measured here (no bench scenario).
- **Criteria that pin code text come from the plan.** If `/architect` writes "the source contains `ShowBalloonTip(10000`", the test-author now has a contradiction to report as `BLOCKER`. A sentence in `/architect` and the plan-reviewer is a follow-up, not in this release.
- **The workflow's line allowance**: WP-02 may need a hand raise of `agentic-implement.js`'s stored lines (the ratchet's baseline is owned by no package). It is the same step 2.22.0 took.
- **The field result's version** is inferred from its shape (issue 145), not stated.

## Annex A · Conformance scenarios

WP-02 adds these four scenarios to `.claude/bin/conformance.json` (`scenarios`, at the end), exactly. The AT refers to them by name. Every other key takes the defaults of `conformance.json`'s `plan` and of the simulated worlds; the default re-review answer is ADDRESSED.

```json
[
  {
    "name": "a reflex finding pinned by an acceptance test goes to pending",
    "plan": {"root": "/repo"},
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-02", "file": "/repo/src/b/x.py", "line": 3, "problem": "PINNED-PROBLEM", "evidence": "x = limit(10000)",
         "fix": "a named constant", "if_skipped": "drift", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]}
    ],
    "gate_fail": [
      {"prefix": "pinned", "exit_code": 0, "output": {"pinned": [
        {"file": "src/b/x.py", "line": 3, "test": "acceptance/test_x.py", "test_line": 12, "text": "limit(10000"}], "skipped": []}}
    ]
  },
  {
    "name": "a pinned step that cannot answer leaves the finding to be fixed",
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-02", "file": "src/b/x.py", "line": 3, "problem": "PINNED-PROBLEM", "evidence": "x = limit(10000)",
         "fix": "a named constant", "if_skipped": "drift", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]},
      {"status": "PASS", "axis": "standards", "findings": [], "not_checked": []}
    ],
    "gate_fail": [{"prefix": "pinned", "exit_code": 1, "output": "boom"}]
  },
  {
    "name": "only reflex findings with a line are checked for pins",
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-02", "file": "src/b/x.py", "line": 3, "problem": "FINISH-NOTE", "evidence": "e", "fix": "f",
         "if_skipped": "s", "provenance": "read", "tier": "finish", "rule": "No magic numbers"},
        {"wp": "WP-02", "file": "src/b/y.py", "problem": "NO-LINE", "evidence": "e", "fix": "f", "if_skipped": "s",
         "provenance": "read", "tier": "reflex", "rule": "No magic numbers"},
        {"wp": "WP-02", "file": "src/b/a b.py", "line": 3, "problem": "SPACED-PATH", "evidence": "e", "fix": "f",
         "if_skipped": "s", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]},
      {"status": "PASS", "axis": "standards", "findings": [], "not_checked": []}
    ]
  },
  {
    "name": "a pinned finding is not re-reviewed and stays pending",
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-02", "file": "src/b/x.py", "line": 3, "problem": "PINNED-PROBLEM", "evidence": "x = limit(10000)",
         "fix": "a named constant", "if_skipped": "drift", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"},
        {"wp": "WP-02", "file": "src/b/x.py", "line": 9, "problem": "FIXED-PROBLEM", "evidence": "y = 255",
         "fix": "a named constant", "if_skipped": "drift", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]}
    ],
    "gate_fail": [
      {"prefix": "pinned", "exit_code": 0, "output": {"pinned": [
        {"file": "src/b/x.py", "line": 3, "test": "acceptance/test_x.py", "test_line": 12, "text": "limit(10000"}], "skipped": []}}
    ]
  }
]
```

What each one must produce, in both engines:

| Scenario | `pinned` gates | `fix_cycles` | `result` | `pending` types |
|---|---|---|---|---|
| a reflex finding pinned by an acceptance test goes to pending | `pinned src/b/x.py:3` | 0 | REVIEW | `acceptance conflict` |
| a pinned step that cannot answer leaves the finding to be fixed | `pinned src/b/x.py:3` | 1 | OK | none |
| only reflex findings with a line are checked for pins | none | 1 | OK | none |
| a pinned finding is not re-reviewed and stays pending | `pinned src/b/x.py:3 src/b/x.py:9` | 1 | REVIEW | `acceptance conflict` |

In the third, the finish note never blocks, and the two reflex findings (no line; a path with a space) are fixed and re-reviewed as today.
