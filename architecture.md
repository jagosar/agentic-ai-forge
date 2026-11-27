# Architecture: a finding goes to the package that owns its file, path by path (issue 149; agentic-flow 2.22.3)
Type: fix · Size: standard

## 1. Goal

A 2.22.2 field run (xmm-test-tool) recorded two Standards findings with incoherent owners. In the first, the reviewer put `wp: WP-01` on a line of `XMM.RemoteStream.psm1:30`, a file WP-03 owns. `split_by_owner` kept the original on WP-01 with its line and added a part on WP-03 without one. The line was pinned by an acceptance test, so `split_pinned` (which matches on path and line) pinned only the WP-01 original. The WP-03 part stayed a normal finding, open to a fix the acceptance test forbids. In the second, the reviewer joined three paths of three other zones into one comma-separated `file` under WP-01. `split_by_owner` read it as one path, so nothing reached the real owners.

After this fix, `split_by_owner` reads `file` as a list of paths (split on `,` and `;`). It gives the finding to the package that owns its first owned path when the reviewer's `wp` owns none of them, and adds one part per other owning package, as it already does for paths the evidence names. The finding then sits on the owner of its file, with its line, so `split_pinned` pins the right package. Parts on other files are fixed as before: the pin belongs to one file and one line (user's choice). Both engines change the same way.

## 2. Scope

### Included

- `findings.split_by_owner`: `file` normalised into paths; the `wp` corrected to the owner of the file when it owns none of its paths; parts for every other package that owns a path of `file` or one named in the evidence or fix; `scope` always a list of single paths.
- The workflow's mirror `splitByOwner` in `agentic-implement.js`, the same rules.
- Three conformance scenarios (Annex A).
- Release 2.22.3.

### Excluded (non-goals)

- Pinning a part on another file because its original is pinned (user's choice: a pin is one file and one line).
- QA defects (they carry no `file`), and the verification's attribution of failures (`verification.attribute`, issue 148).
- Changing how the reviewers report `file`: the normalisation copes with what they send.
- A finding whose `file` no package owns (for example the acceptance zone): its `wp` stays as given.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- The repository's own suites, which CI also runs: `python3 -m unittest discover -s acceptance` and `python3 -m unittest discover -s qa`
- Quality limits: `python3 .claude/bin/agentic.py quality`

## 4. Repository structure

```
.claude/bin/findings.py                  WP-01  split_by_owner, _paths, _owner_of, PATH_SEPARATORS
.claude/bin/test_owner_wp.py             WP-01  new: unit cases
.claude/workflows/agentic-implement.js   WP-01  splitByOwner and its helpers, the same rules
.claude/bin/conformance.json             WP-01  three scenarios (Annex A)
docs/how-it-works.md                     WP-02  the split paragraph
.claude-plugin/plugin.json               WP-02  2.22.3
.claude/bin/upgrade.py                   WP-02  NOTES["2.22.3"]
.claude/flow-budget.json                 WP-02
.claude/bin/test_acceptance_v222.py      WP-02  its version pin (line 229): 2.22.3
.claude/bin/test_owner_split_v2.py       AT
.claude/flow-history.json                by hand (the person executing the plan): regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| `split_by_owner` today: parts only for packages whose files the evidence or fix names; the original gets `scope` (its `file` plus its own named files); parts drop `line`, get the owner's spelling of the path, `split_from` and a fresh fingerprint suffixed `-2`, `-3` when taken; an unsplit finding is the same object | `.claude/bin/findings.py:136-167` | Keep every one of these properties | read |
| `_without_root` (root removed, `\` read as `/`, ASCII case folded for the root only) and `_named` (whole-path match in lowered text, a `/` path names a directory) | `.claude/bin/findings.py:114-133` | Reuse both | read |
| `pin_path` and `split_pinned` match on the finding's `file` (root removed) and `line` | `.claude/bin/findings.py:198-248` | Unchanged: a finding on the right owner with its line is pinned as it is | read |
| The engines split each axis's confirmed findings once, after the verifiers | `.claude/bin/pipeline.py:524`, `.claude/workflows/agentic-implement.js:670-678` | Unchanged call sites | read |
| `owners` is `{wp: [files]}` and `root` the repo root, both in `pipeline-plan`'s plan | `.claude/bin/launch.py:684` | | read |
| The workflow's mirror and its helpers (`lowAscii`, `noRoot`, `pathRe`, `named`, `str`, `splitByOwner`) | `.claude/workflows/agentic-implement.js:179-218` | Mirror the new Python helpers here | read |
| Unit tests of `split_by_owner` that must keep passing (same object, owner's spelling, `WP-99` with no file, an unowned `/abs/x.py`, bad shapes) | `.claude/bin/test_owner_split.py:22-69` | None of them has a `wp` that owns none of an owned `file`: they stay valid | read |
| More split tests (the fix prompt carries the part's `wp`, `file` and `scope`; root `C:/repo`) | `.claude/bin/test_fix_routing.py:120-160` | Must keep passing | read |
| The conformance scenario of a split | `.claude/bin/conformance.json:1924-1966` | Annex A copies its shape | read |
| The workflow may grow to 967 lines (stored 937, growth 30) with no new line over 120 characters (64 stored) | `.claude/quality-baseline.json`, `.claude/bin/quality.py:232-235` | | read |
| Release notes: newest first, `2.22.2` at the top of the recent block | `.claude/bin/upgrade.py:156-164` | `2.22.3` right before `2.22.2` | read |
| `test_acceptance_v222.py` pins the plugin version | `.claude/bin/test_acceptance_v222.py:226-229` | `"2.22.2"` → `"2.22.3"` | read |

What must NOT change: a finding whose `wp` owns its `file` and whose evidence names no other package is returned as the same object; a finding that is split only because its evidence names other packages keeps its `file` exactly as the reviewer wrote it (root and backslashes included) and its `line`, as today; the fingerprint of the original; the parts' fields and order.

## 5. Data model

```python
PATH_SEPARATORS = re.compile(r"\s*[,;]\s*")  # a reviewer may join several paths into one `file`
```

A finding after the split may carry `"wp_from": "<the reviewer's wp>"` when its `wp` was corrected. `scope`, whenever present, is a list of single paths.

## 6. Contracts between modules

### C1 · `findings.split_by_owner(findings, owners, root) -> list` (WP-01; mirrored by WP-02)

For each finding `f` that is a dict (anything else passes through unchanged, in place):

1. `paths`: `_without_root(f["file"], root)` when `file` is a string, split with `PATH_SEPARATORS`, empty pieces dropped, repeats dropped, order kept. `[]` when `file` is not a string.
2. `_owner_of(path, owners)`: the first package id in ascending order whose files contain the path, compared ASCII-lowercased: equal to a file, or under a file ending in `/`. `None` when no package owns it. Owner values that are not lists are skipped (`test_owner_split.py:62` passes `{"WP-02": "src/b/"}`).
3. `wp`: `f["wp"]` when it is a string, else `None`. When at least one path has an owner and `wp` owns none of the paths, `new_wp` is the owner of the first owned path (in `paths` order) and the finding is **corrected**; otherwise `new_wp = wp`.
4. `others`: for each package `o != new_wp` in ascending id order, the paths of `paths` it owns plus the files of `o` that `_named` finds in the evidence and fix (today's rule). Packages with none are left out.
5. When the finding is not corrected, `others` is empty and `len(paths) <= 1`: append `f` itself and continue (same object).
6. The original: `{**f, "wp": new_wp, "scope": sorted(set(<paths owned by new_wp> + <unowned paths> + <new_wp's files named in the evidence>))}`. Its `file` and `line`: when the finding is not corrected and `len(paths) <= 1`, both stay exactly as the reviewer wrote them (today's behaviour). Otherwise `file` becomes the first path of `paths` owned by `new_wp`, else `paths[0]`; `line` is kept only when that new `file` equals `paths[0]`, and removed otherwise. When corrected, add `"wp_from": wp`.
7. Parts, as today: for each `o` in `others`, `{**f, "wp": o, "file": scope[0], "scope": scope, "split_from": f["fingerprint"]}` with `scope = sorted(set(files))` (the owner's spelling for named files, the finding's spelling for paths of `file`), no `line`, `wp_from` removed, and a fresh fingerprint (suffixed `-2`, `-3` ... when taken).
8. Never raises on odd shapes (non-string fields, owners not a dict, a file list).

### C2 · `splitByOwner(findings)` (agentic-implement.js, WP-02)

The same rules, reading `plan.owners` and `plan.root` as today. Helpers mirrored: `pathsOf(file)` (with `PATH_SEPARATORS = /\s*[,;]\s*/`), `ownerOf(path, owners)`.

## 7. Conventions

- English for code, comments and docs; the repository's existing style.
- Standard library only; `findings.py` keeps no flow import.
- No line over 120 characters; functions ≤ 60 lines; nesting ≤ 4 (`agentic.py quality`). Split `split_by_owner` into helpers if it would pass 60 lines.
- A comment above each JS mirror names the Python function.
- Docs and notes name no flow version outside `upgrade.NOTES` and `plugin.json`.
- Commits: `type: summary` in lowercase, ending with the session's attribution lines.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · A finding on a file its `wp` does not own goes to the file's owner, with its line (the bug, case 1)
  - Scenario: `owners = {"WP-01": ["src/a.py"], "WP-03": ["src/c.py"]}`, root `""`; one finding with fingerprint (`with_fingerprints`) of `{"axis": "standards", "tier": "reflex", "rule": "Line length", "wp": "WP-01", "file": "src/c.py", "line": 3, "problem": "P", "evidence": "src/c.py:3 is 130 characters", "fix": "split it"}`.
  - Action: `findings.split_by_owner([f], owners, "")`.
  - Expected: one finding, `wp` `WP-03`, `wp_from` `WP-01`, `file` `src/c.py`, `line` 3, `scope` `["src/c.py"]`, the same `fingerprint`.
  - Must not: a second finding (no part); `split_from` on the result.
  - Check: `test_owner_split_v2.py`, AC-001 tests.
  - WP: WP-01
- AC-002 · The pin reaches the owner, and no fix is attempted, in both engines
  - Scenario: Annex A scenario "a pinned finding on a file its wp does not own goes to the owner".
  - Action: the fallback engine (`test_pipeline.run_scenario`, and `test_pipeline.world` + `pipeline.Pipeline` for the full result) and the native engine (`node .claude/bin/test_workflow.mjs --dump`).
  - Expected: the gates contain `pinned src/c.py:3` once; `fix_cycles` 0; `result` `REVIEW`; `pending` types `["acceptance conflict"]`, and that item's `wp` is `WP-03`; `review.standards.confirmed` is `[]`. Both engines agree on result, fix_cycles, pending, gates, gate_calls, agents and prompts.
  - Must not: an implementer call labelled `(fix)`; a confirmed finding on `WP-03`.
  - Check: `test_owner_split_v2.py`, AC-002 tests.
  - WP: WP-01
- AC-003 · A `file` with several paths is split by owner, `scope` always a list (case 2)
  - Scenario: `owners = {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["src/c.py"]}`; a finding of `wp` `WP-01`, `line` 7, `file` `"src/c.py, src/b/x.py; acceptance/t.py"`, evidence `"e"`, fix `"f"`.
  - Action: `findings.split_by_owner([f], owners, "")`, and the Annex A scenario "a finding whose file lists several paths is split by owner" in both engines.
  - Expected (unit): two findings. The original: `wp` `WP-03`, `wp_from` `WP-01`, `file` `src/c.py`, `line` 7, `scope` `["acceptance/t.py", "src/c.py"]`. The part: `wp` `WP-02`, `file` `src/b/x.py`, `scope` `["src/b/x.py"]`, `split_from` the original's fingerprint, no `line`, no `wp_from`. (Engines): one fix cycle with fix calls for `WP-02` and `WP-03` and none for `WP-01`; both engines agree as in AC-002.
  - Must not: any `scope` entry containing `,` or `;`; a finding left on `WP-01`.
  - Check: `test_owner_split_v2.py`, AC-003 tests.
  - WP: WP-01
- AC-004 · A part on another file is fixed even when the original's line is pinned
  - Scenario: Annex A scenario "a part on another file is fixed although the original is pinned".
  - Action: both engines.
  - Expected: `pinned src/a.py:3` once; `pending` types `["acceptance conflict"]` with `wp` `WP-01`; one fix cycle with a `WP-03 (fix)` call and no `WP-01 (fix)` call; both engines agree.
  - Must not: the `WP-03` part in pending.
  - Check: `test_owner_split_v2.py`, AC-004 tests.
  - WP: WP-01
- AC-005 · What owned its file before is unchanged
  - Scenario: `owners` of AC-003.
  - Action: `split_by_owner` on (a) a finding of `WP-01` on `src/a.py` with evidence `"e"`; (b) `WP-01` on `/abs/x.py` (no owner), evidence `"e"`; (c) `WP-99` with `file` `None` and evidence `src/c.py`; (d) `WP-01` with `file` `["src/c.py"]` (not a string), evidence `"e"`.
  - Expected: (a), (b) and (d) are returned as the same objects; (c) gives `[("WP-99", []), ("WP-03", ["src/c.py"])]` as `(wp, scope)` pairs, as today.
  - Must not: `wp_from` on any of them.
  - Check: `test_owner_split_v2.py`, AC-005 test.
  - WP: WP-01
- AC-006 · Release 2.22.3
  - Scenario: the repository.
  - Action: read the release files; run `agentic.py quality`.
  - Expected: `plugin.json`'s version as a tuple ≥ `(2, 22, 3)`; `upgrade.NOTES["2.22.3"]` comes right before `"2.22.2"` and some note contains `wp_from`; `docs/how-it-works.md` contains `wp_from` and not `2.22.3`; `quality` exits 0.
  - Must not: a line of `test_acceptance_v222.py` with both `plugin[` and `"2.22.2"`.
  - Check: `test_owner_split_v2.py`, AC-006 test (flow repo only).
  - WP: WP-02

### Work packages

#### WP-01 · Both engines give a finding to the package that owns its file, path by path
- Wave 1.
- Files: `.claude/bin/findings.py`, `.claude/bin/test_owner_wp.py`, `.claude/workflows/agentic-implement.js`, `.claude/bin/conformance.json`.
- Implements C1 and C2.
- ACs: AC-001, AC-002, AC-003, AC-004, AC-005.
- **Patterns to mirror:** `.claude/bin/findings.py:136-167` (the function you change); `.claude/bin/test_owner_split.py:1-30` (unit tests); `.claude/workflows/agentic-implement.js:179-218` (the mirror); `.claude/bin/conformance.json:1924-1966` (a split scenario).
- **Gotchas:**
  - Both engines in one package: `test_pipeline.ConformanceTests` (`.claude/bin/test_pipeline.py:212-231`) runs the JS engine and the Python engine and compares their prompts, so neither engine can change alone.
  - The ownership test is per path: `src/b/` owns `src/b/x.py`, not `src/bb/x.py`; compare ASCII-lowercased, keep the original spelling.
  - The original's fingerprint is never recomputed; only parts get a fresh one.
  - Keep the same-object return for unchanged findings: `test_owner_split.py:66-69` pins it.
  - A function over 60 lines fails `quality`: move the path and owner helpers out.
  - The workflow has 30 lines of headroom (937 stored): reuse `noRoot`, `named`, `lowAscii` and `str`, keep the mirror compact, and add no line over 120 characters.
  - JS `sort()` on strings sorts by UTF-16 code units, Python's `sorted` by code points: equal for the ASCII paths the scenarios use.
  - Add the Annex A scenarios exactly, at the end of `scenarios`; `json.dumps(indent=2)` reproduces the file.
  - Known red until WP-02: `test_lean` (the budget) and AC-006.
- **Exact imports and APIs:** `re` (already imported), `_without_root`, `_named`, `fingerprint`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_owner*.py"`; `node .claude/bin/test_workflow.mjs`; `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · Documentation and release 2.22.3
- Wave 2 (it measures the budget after WP-01).
- Files: `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_acceptance_v222.py`.
- Depends on WP-01 by implementation.
- ACs: AC-006.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-164`.
- **What to write:** in `how-it-works.md`, after the sentence on splitting a confirmed finding, one sentence: the finding's `file` is read path by path, and a finding whose `wp` owns none of its paths goes to the owner of the first one, recording the reviewer's `wp` in `wp_from`. One note in `NOTES["2.22.3"]` naming issue 149 and `wp_from`. The budget, measured with `test_lean.code_lines(Path('.'))` and `test_lean.prompt_bytes(Path('.'))`, with a `why`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 -m unittest discover -s acceptance`; `python3 -m unittest discover -s qa`; `python3 .claude/bin/agentic.py quality`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)", "Bash(python3 .claude/bin/agentic.py quality)"],
  "acceptance": {"files": [".claude/bin/test_owner_split_v2.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_owner_split_v2.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/findings.py", ".claude/bin/test_owner_wp.py", ".claude/workflows/agentic-implement.js", ".claude/bin/conformance.json"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-005"], "mirror": [".claude/bin/findings.py:136-167", ".claude/bin/test_owner_split.py:1-30", ".claude/workflows/agentic-implement.js:179-218", ".claude/bin/conformance.json:1924-1966"]},
    {"id": "WP-02", "wave": 2, "depends_on": ["WP-01"], "files": ["docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_acceptance_v222.py"],
     "acs": ["AC-006"], "mirror": [".claude/bin/upgrade.py:156-164"]}
  ]
}
```

## 9. Test strategy

- **Unit:** WP-01 in `test_owner_wp.py` (paths, owners, correction, parts, odd shapes). The JS mirror is held equal by the conformance scenarios (`test_pipeline.ConformanceTests`).
- **Acceptance (AT, wave 0):** `.claude/bin/test_owner_split_v2.py`, red today: AC-001 gets a part and keeps `WP-01`; AC-002's pin lands on `WP-01` and a `WP-03` fix runs; AC-003 gets one finding with a comma scope. Engine criteria use the Annex A scenario names, as `test_pinned_conflict.py` does; a missing scenario raises an `AssertionError` naming it. AC-006 is skipped outside the flow repo. The AT must not write `"2.21.2"`, `"2.22.0"`, `"2.22.1"` or `"2.22.2"` on a line containing `version`.
- **QA:** Windows-style paths with a drive letter in `file`, a `file` of only separators, duplicates.
- Executed by hand (`"maintainer": true`).

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| A pin applies to the finding on its own file and line only | Every part of a pinned finding goes to pending | User's choice: a part on another file is fixed elsewhere and its fix cannot break the pinned line. |
| Correct `wp` to the owner of the first owned path, recording `wp_from` | Keep the reviewer's `wp` and only split | With the owner on the original, the line stays with the right package and `split_pinned` needs no change; the reviewer's choice stays visible. |
| `,` and `;` separate paths | Any whitespace | Paths with spaces exist; reviewers join with commas. |
| Unowned paths stay in the original's `scope` | Drop them | The re-review must still judge the finding in every file it names. |
| No change to `split_pinned` or the engines' call sites | A pin per `split_from` group | The corrected original carries the line. |
| Both engines in one package, then the release | One package per engine | The conformance test compares the engines' prompts: one engine alone fails it (precedent: design 0033). |
| A finding not corrected whose `wp` owns only a later path of a multi-path `file` loses its `line` (its `file` becomes that path) | Keep the line | The line belongs to the first path the reviewer wrote; on another file it would be wrong, and a wrong line could pin the wrong text. |
| `file` rewritten only for a corrected or multi-path finding | Always normalise it | A finding split only by its evidence keeps today's `file`, so its fix prompt and its pin are unchanged. |
| Version 2.22.3 | 2.23.0 | A fix. |

## 11. Risks and open questions

- **A reviewer that names the right package but the wrong file** is now moved to the file's owner. The evidence still names its files, which parts cover.
- **The field JSON was not checked** (issue 149 is an extract): case 1's cause (the WP-03 part without a line) is inferred from the code.

## Annex A · Conformance scenarios

WP-01 adds these to `.claude/bin/conformance.json`, at the end of `scenarios`, exactly.

```json
[
  {
    "name": "a pinned finding on a file its wp does not own goes to the owner",
    "plan": {"owners": {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["src/c.py"]}},
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-01", "file": "src/c.py", "line": 3, "problem": "OWNER-PROBLEM", "evidence": "src/c.py:3 is long",
         "fix": "split it", "if_skipped": "drift", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]}
    ],
    "gate_fail": [
      {"prefix": "pinned", "exit_code": 0, "output": {"pinned": [
        {"file": "src/c.py", "line": 3, "test": "acceptance/test_c.py", "test_line": 4, "text": "limit(10000"}], "skipped": []}}
    ]
  },
  {
    "name": "a finding whose file lists several paths is split by owner",
    "plan": {"owners": {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["src/c.py"]}},
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-01", "file": "src/c.py, src/b/x.py; acceptance/t.py", "line": 7, "problem": "MULTI-PROBLEM",
         "evidence": "e", "fix": "f", "if_skipped": "drift", "provenance": "read", "tier": "reflex",
         "rule": "No magic numbers"}]},
      {"status": "PASS", "axis": "standards", "findings": [], "not_checked": []}
    ]
  },
  {
    "name": "a part on another file is fixed although the original is pinned",
    "plan": {"owners": {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["src/c.py"]}},
    "standards": [
      {"status": "FAIL", "axis": "standards", "not_checked": [], "findings": [
        {"wp": "WP-01", "file": "src/a.py", "line": 3, "problem": "TWIN-PROBLEM", "evidence": "the same at src/c.py:9",
         "fix": "one constant", "if_skipped": "drift", "provenance": "read", "tier": "reflex", "rule": "No magic numbers"}]},
      {"status": "PASS", "axis": "standards", "findings": [], "not_checked": []}
    ],
    "gate_fail": [
      {"prefix": "pinned", "exit_code": 0, "output": {"pinned": [
        {"file": "src/a.py", "line": 3, "test": "acceptance/test_a.py", "test_line": 2, "text": "limit(10000"}], "skipped": []}}
    ]
  }
]
```
