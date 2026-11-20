# Architecture: guardrails that keep the flow lean, and a fast hook (agentic-flow 2.18.0)
Type: change · Size: standard

## 1. Goal
The flow doubled its code between 2.0.0 and 2.17.0, from 3,214 to 6,481 lines of Python outside the tests in `.claude/bin` (7,120 with the workflow's JavaScript, the measure of section 5), and its prompts grew 31 %. Nothing watched the totals. In 2.17.0 a regression slipped in unseen: the PreToolUse hook, which runs on every tool call of every agent, imports the whole of `agentic.py`, including `launch.py`, which now loads `http.client`.

This design adds four deterministic guardrails to the flow's own tests, so the flow cannot grow, slow down or take on debt without a visible decision:
- the standard library only;
- an import budget for the hook;
- a size budget;
- no unreferenced debt markers.

It also makes the hook load only the guard: 100 ms per call on today's code, against 58 ms with the guard alone, measured in this container. Measuring run cost with the bench and trimming prompts is the next release ("diet 2"), out of scope here.

## 2. Scope
### Included
- **Fast hook.** `agentic.py hook` (what `hook.py` runs) handles the `hook` command before the module-level imports of the other domains: it imports `core`'s `die`/`root_drift`, then `guardrail.hook`, and nothing else of the flow.
- **Guardrail 1: standard library only.** Every `import`/`from … import` in `.claude/bin/*.py` and every `require(...)`/`import … from` in `.claude/workflows/*.js` names a standard-library module, a module of `.claude/bin` itself, or a Node built-in.
- **Guardrail 2: hook import budget.** Running `hook.py` with a payload must not load any of `HOOK_FORBIDDEN_MODULES` (section 5), checked from `python3 -X importtime`.
- **Guardrail 3: size budget.** `.claude/flow-budget.json` records the code lines and prompt bytes of the flow, as measured in section 5:
  - a test fails when either measure is above its budget, or more than 5 % below it;
  - raising or lowering the budget is a one-file change, with a `why` that the test requires to be non-empty.
- **Guardrail 4: debt markers.** No `TODO`, `FIXME`, `XXX` or `HACK` in `.claude/bin/*.py` or `.claude/workflows/*.js` unless the same line names an issue (`#123` or `issue 123`).
- **Release 2.18.0:**
  - `test_acceptance_v218.py`;
  - `test_acceptance_v217.py`'s classes moved to `test_field_fixes.py`, and the old file deleted;
  - notes, version, docs.

### Excluded (non-goals)
- **Bench measurement of 2.17 against 2.14 and prompt trimming:** the next release.
- **Timing tests.** No test asserts milliseconds; CI timings are noisy. The import budget is the deterministic proxy.
- **Lazy imports for the other commands.** `agentic.py seq` and the rest keep loading every module.
- **A dead-code detector:** too many false positives (callers in tests and in JavaScript).
- **No change to `hook.py`**, which is never owned, or to the guard's decisions.

## 3. Stack
Python 3.9+ (the standard library only), Node 20+ for the workflow harness. Commands, as in CI:
- `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- `node .claude/bin/test_workflow.mjs`
- `python3 -m unittest discover -s bench -p "test_*.py"`
- `python3 -m unittest discover -s bench/acceptance`
- `python3 -m unittest discover -s acceptance`
- `python3 -m unittest discover -s qa`
- `python3 .claude/bin/agentic.py quality`, `docs-check` and `flow-history --check`

Run `export CLAUDE_PROJECT_DIR=$PWD` before them.

## 4. Repository structure
```
.claude/bin/agentic.py                   WP-01  the hook fast path
.claude/bin/test_hook_path.py            WP-01  guardrail 2 (new)
.claude/bin/test_lean.py                 WP-02  guardrails 1, 3 and 4 (new)
docs/how-it-works.md                     WP-03
docs/how-to/plugin.md                    WP-03  the maintainer's release steps
.claude-plugin/plugin.json               WP-03  2.18.0
.claude/bin/upgrade.py                   WP-03  NOTES["2.18.0"]
.claude/bin/test_field_fixes.py          WP-03  moved from test_acceptance_v217.py (new)
.claude/bin/test_acceptance_v217.py      WP-03  deleted
.claude/flow-budget.json                 WP-03  the size budget (new), written after every code change
.claude/flow-history.json                WP-03  regenerated as the PR's last commit
.claude/bin/test_acceptance_v218.py      AT     (new)
```

## 4b. Existing code context
| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| `hook.py` runs `agentic.py` through `runpy.run_path(script, run_name="__main__")` with `sys.argv = [script, "hook"]`; it never imports `agentic.py` itself | `.claude/bin/hook.py:1-29` | The fast path keys on `__name__ == "__main__"` and `sys.argv[1:2] == ["hook"]` | read |
| `agentic.py` puts its folder on `sys.path`, imports `compat`, then every domain module (core, manifest_check, repo_scan, verification, stage, installer, launch, guardrail) at module level | `.claude/bin/agentic.py:73-100` | Insert the fast path right after `import compat` (line 78), before `from core import` | read |
| `main()` calls `compat.utf8_stdio()`, refuses a `root_drift()` problem with `die`, then dispatches; `hook` is not in `ROOT_FREE_COMMANDS` | `.claude/bin/agentic.py:395-414` | The fast path must do the same two steps before `hook()`, so behaviour is unchanged | read |
| `guardrail.hook()` reads stdin, records the heartbeat, guards, and always ends in `sys.exit(0)` (or `block`, which exits 2) | `.claude/bin/guardrail.py:579-593` | The fast path never returns: no code after `hook()` runs | read |
| `guardrail` imports `stage`, which imports `reports` (xml) and `verification` for the stop gate | `.claude/bin/stage.py:14-23` | These stay on the hook path; they are not in the forbidden list | read |
| Measured in this container: `hook.py` loads brief, manifest_check, repo_scan, installer, findings, launch, ssl, http.client, urllib.request, email.parser; a guard-only path loads none of them; 100 ms against 58 ms per call (20 calls each) | not a file: `python3 -X importtime` and timing runs here | `HOOK_FORBIDDEN_MODULES` is that list | inferred |
| The quality ratchet's limits and baseline, which watch each function and file, not totals | `.claude/bin/quality.py:18-19`, `.claude/bin/quality.py:59` | The size budget is a separate, simpler file; do not extend `quality-baseline.json`, which only a person writes and the installer creates in projects | read |
| `test_definitions.py` imports `agentic`, defines `FLOW_REPO_ONLY` from `agentic.is_flow_repo(ROOT)` | `.claude/bin/test_definitions.py:8-28` | New test files define `FLOW_REPO_ONLY` the same way | read |
| The command table is pinned at 37 and to the docstring | `.claude/bin/test_definitions.py:504-507` | No command is added here: the count stays 37 | read |
| The previous release's acceptance file and how 2.17.0 moved 2.16.0's classes | test_acceptance_v217.py (its classes at lines 96-392 before this change deletes it), `.claude/bin/test_hook_diagnosis.py:1-10` | Move every class but `ReleaseTests`; `DocsTests` gets `FLOW_REPO_ONLY` | read |
| At most one `test_acceptance*.py` in `.claude/bin` | `.claude/bin/test_layout.py:1-22` | Delete `test_acceptance_v217.py` in the same change | read |
| Upgrade notes, newest first | `.claude/bin/upgrade.py:156-170` | Add `"2.18.0"` above `"2.17.0"` | read |
| The ratchet paragraph in the reference | `docs/how-it-works.md:253` | Add the flow's own guardrails after it | read |
| The maintainer's release steps (flow-history as the last commit) | `docs/how-to/plugin.md:110-120` | Add the budget step there | read |
| What install ships: `.claude/bin/*.py` modules listed by name, agents, commands, workflows, rules; the test suite where any part is present; no `.claude/*.json` at the root | `.claude/bin/installer.py:30-46` | `flow-budget.json` is not shipped; tests that read it are `FLOW_REPO_ONLY` | read |

What must **not** change:
- the hook's decisions, its exit codes and its heartbeat;
- what `hook.py` runs;
- any other command's behaviour or output.

## 5. Data model
```python
# test_hook_path.py
HOOK_FORBIDDEN_MODULES = ("launch", "installer", "manifest_check", "repo_scan", "brief", "findings",
                          "http.client", "ssl", "urllib.request", "email.parser")

# .claude/flow-budget.json
{"code_lines": 7130, "prompt_bytes": 99000, "why": "2.18.0: first budget, the flow as measured at 2.17.0 plus the fast hook"}
# The values above are an example; WP-03 writes it last, after the notes in upgrade.py, with the measured values
# rounded up to the next 10 (lines) and 100 (bytes).

# The measures (test_lean.py):
# code_lines   = lines of .claude/bin/*.py whose name does not start with "test" (testutil.py excluded too)
#                + lines of .claude/workflows/*.js
# prompt_bytes = bytes of .claude/agents/*.md + .claude/commands/*.md + .claude/rules-library/*.md
# Measured on this branch before any change: 21 code files, 7120 lines; 24 prompt files, 98956 bytes.
BUDGET_SLACK = 0.05
# budget_problems, for each measure m with budget b:
#   m > b                       -> "<name> is <m>, above its budget <b> in flow-budget.json: raise it, with a why"
#   m < b * (1 - BUDGET_SLACK)  -> "<name> is <m>, more than 5 % below its budget <b> in flow-budget.json: lower it"
#   a missing file              -> "flow-budget.json is missing"
#   a missing or blank "why"    -> "flow-budget.json needs a why"
DEBT_RE = r"\b(TODO|FIXME|XXX|HACK)\b"     # built from parts in the test so the test file never matches itself
ISSUE_RE = r"#\d+|\bissue \d+"
```

## 6. Contracts between modules
```python
# agentic.py, right after `import compat`:
if __name__ == "__main__" and sys.argv[1:2] == ["hook"]:  # every tool call runs this: load only the guard
    from core import die as _die, root_drift as _root_drift
    compat.utf8_stdio()
    _problem = _root_drift()
    if _problem:
        _die(_problem)
    from guardrail import hook as _hook
    _hook()  # never returns: it exits 0, or 2 when it blocks

# test_hook_path.py
def hook_copy(test):
    """A temporary git repo (git init, removed by test.addCleanup) holding copies of this branch's .claude/bin/,
    .claude/settings.json and .claude/agents/, and architecture.md with test_agentic.MANIFEST. Returns its Path.
    test_agentic.Repo does not copy .claude/bin, so this helper does."""

def hook_modules(project, payload, env=None):
    """(returncode, stderr, modules) of `python3 -X importtime <project>/.claude/bin/hook.py` with payload (a dict,
    sent as JSON on stdin) and CLAUDE_PROJECT_DIR=project. modules is a set of names, from the stderr lines that
    start with 'import time:', skipping the header line ('import time: self [us] | cumulative | imported package')
    and stripping each name's indentation; stderr is the other lines."""

# test_lean.py
def code_lines(root): ...      # section 5; len(text.splitlines()) per file; a missing folder counts 0
def prompt_bytes(root): ...    # section 5; a missing folder counts 0
def third_party_imports(root): # sorted [(file, module)], file posix relative to root: neither stdlib, local nor
                               # node built-ins. JS specifiers: the quoted string inside require( ... ), and the
                               # quoted string after `from` on a line starting with import; one starting with '.' is local
def unreferenced_markers(root):# [(file, line_no, text)]: file posix relative to root, text the line stripped
def budget_problems(root):    # [message] comparing code_lines/prompt_bytes with root/.claude/flow-budget.json (section 5)
```
The acceptance tests may import `test_hook_path` and `test_lean` and call these functions. Python's standard-library names come from `sys.stdlib_module_names` (3.10+); on 3.9 the stdlib test skips, because the other CI jobs run 3.12 and 3.14. Node built-ins come from `require("module").builtinModules`; the check reads the list by running `node -e`, and skips when `node` is missing.

## 7. Conventions
- **Python 3.9.** No `X | None` or `list[...]` in runtime annotations; types go in docstrings, as `.claude/bin` does. This overrides the Python rules' annotation rule for this repository.
- **The ratchet:** functions of 60 lines or fewer (100 in tests), nesting of 4 or fewer, lines of 120 characters or fewer, files of 800 lines or fewer.
- **No timing assertions.** Guardrails assert names and counts only.
- **Tests that read `flow-budget.json`, the flow's guides or bench files** are `FLOW_REPO_ONLY`. The stdlib, debt-marker and hook-import tests run everywhere the suite ships.
- **No personal paths in tests or docs.**
- **The guides cite no flow version numbers** (`acceptance/test_docs.py`).

## 8. Work packages and acceptance criteria
### Acceptance criteria
- AC-001 · The hook loads only the guard
  - Scenario: a temporary git repo holding copies of this branch's `.claude/bin/`, `.claude/settings.json` and `.claude/agents/`, `CLAUDE_PROJECT_DIR` pointing at it, and the payload `{"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "s1"}` on stdin.
  - Action: `python3 -X importtime .claude/bin/hook.py`.
  - Expected:
    - exit code 0;
    - none of `HOOK_FORBIDDEN_MODULES` among the loaded modules;
    - `guardrail` and `stage` among them;
    - `.claude/state/hook-seen.json` written, with `session_id` `s1`.
  - Must not: change the hook's result; leave a forbidden module loaded.
  - Check: `test_acceptance_v218.py`, `HookPathTests`.
  - WP: WP-01
- AC-002 · The fast hook keeps the guard's behaviour
  - Scenario: as AC-001, with `architecture.md` holding `test_agentic.MANIFEST` (WP-01 owns `src/a.py` and `tests/test_a.py`).
  - Action:
    - through `hook.py`: a `Write` of `<copy>/outside.py` by a fallback agent (`AGENTIC_WP=WP-01`);
    - directly as `python3 <copy>/.claude/bin/agentic.py hook`, bypassing `hook.py` (which would run the other repository's own script): the cwd outside both repositories and `CLAUDE_PROJECT_DIR` naming another git repository.
  - Expected:
    - the first exits 2 and stderr holds `WP-01 does not own outside.py`;
    - the second exits with the same code, and the same stderr, as `python3 <copy>/.claude/bin/agentic.py validate` in that environment (the `root_drift` refusal).
  - Must not: let the write through; ignore the root drift.
  - Check: `test_acceptance_v218.py`, `HookPathTests`.
  - WP: WP-01
- AC-003 · Only the standard library
  - Scenario: this repository; and a temporary copy of `.claude/bin` with one extra module, `extra.py`, containing `import requests`.
  - Action: `test_lean.third_party_imports(root)`.
  - Expected:
    - `[]` for this repository;
    - `[(".claude/bin/extra.py", "requests")]` for the copy;
    - local modules (`core`, `compat`) and `from . import x` are never reported.
  - Must not: report a stdlib module such as `xml.etree.ElementTree` or `http.client`.
  - Check: `test_acceptance_v218.py`, `LeanTests` (skips below Python 3.10).
  - WP: WP-02
- AC-004 · The size budget holds both ways
  - Scenario: this repository with its `.claude/flow-budget.json` (written by WP-03, so this case stays red until then); and temporary roots whose budget is below the measures, or loose beyond the band.
  - Action: the budget check, `test_lean.budget_problems(root)` returning a list of messages.
  - Expected:
    - `[]` here;
    - a budget lower than a measure gives the "above its budget" message of section 5;
    - a measure below `budget * (1 - BUDGET_SLACK)` gives the "lower it" message of section 5;
    - an empty `why` gives `flow-budget.json needs a why`.
  - Must not: pass a budget the code exceeds; pass a stale, loose budget.
  - Check: `test_acceptance_v218.py`, `LeanTests`.
  - WP: WP-02
- AC-005 · Debt markers name an issue
  - Scenario: this repository; and a temporary root whose `.claude/bin/a.py` has three lines: one marker with no issue, one with `#42`, one with `issue 42`.
  - Action: `test_lean.unreferenced_markers(root)`.
  - Expected:
    - `[]` here;
    - one entry for the temporary root, at line 1 of `.claude/bin/a.py`.
  - Must not: report a marker that names an issue; miss a marker in a `.js` file under `.claude/workflows/`.
  - Check: `test_acceptance_v218.py`, `LeanTests`.
  - WP: WP-02
- AC-006 · Docs and release 2.18.0
  - Scenario: the repository.
  - Action: read the files.
  - Expected:
    - `plugin.json` version `2.18.0`;
    - `NOTES["2.18.0"]` has at least 2 entries, naming `hook` and `flow-budget.json`;
    - `docs/how-it-works.md` names `flow-budget.json` and the standard-library rule;
    - `docs/how-to/plugin.md` names `flow-budget.json` among the release steps;
    - the only acceptance file is `test_acceptance_v218.py`;
    - `test_field_fixes.py` defines `AnnexTests`, `ReferenceTests`, `KeptCopyTests`, `NetworkTests`, `SessionTests` and `DocsTests`.
  - Must not: keep `test_acceptance_v217.py`.
  - Check: `test_acceptance_v218.py`, `ReleaseTests`.
  - WP: WP-03

### Work packages
#### WP-01 · The hook loads only the guard
- Wave 1.
- Files: `.claude/bin/agentic.py`, `.claude/bin/test_hook_path.py`.
- Contracts: the fast path and `hook_modules` (section 6).
- ACs: AC-001, AC-002.
- **Patterns to mirror:** `agentic.py:73-100`, `agentic.py:395-414` and `test_guardrail.py:44-67` (a `Repo`, its `run` and `hook`).
- **Gotchas:**
  - `test_definitions.py` checks that names `agentic.py` re-exports are the modules' own objects. The fast path must not shadow any of them: use underscore names (`_hook`, `_die`, `_root_drift`).
  - Tests that `import agentic` must not trigger the fast path: `__name__` is then `"agentic"`.
  - `-X importtime` writes to stderr; the hook also writes warnings there. Parse only lines starting with `import time:`.
  - The copy for the test holds `bin/`, `settings.json` and `agents/`. `test_guardrail.py` runs `agentic.py hook` directly; AC-001 goes through the copy's `hook.py`.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_hook_path.py"`, `python3 -m unittest discover -s .claude/bin -p "test_guardrail.py"`, `python3 -m unittest discover -s .claude/bin -p "test_definitions.py"`.

#### WP-02 · The lean guardrails
- Wave 1.
- Files: `.claude/bin/test_lean.py`.
- Contracts: `code_lines`, `prompt_bytes`, `budget_problems`, `third_party_imports`, `unreferenced_markers` (sections 5 and 6), as module-level functions so the acceptance tests can call them on temporary roots.
- ACs: AC-003, AC-004, AC-005.
- **Patterns to mirror:** `test_definitions.py:8-28` (imports, `ROOT`, `FLOW_REPO_ONLY`) and `test_layout.py:1-48` (a small file of one-purpose checks).
- **Gotchas:**
  - Parse imports with `ast`, never with regexes: a docstring that says "import requests" is not an import.
  - Relative imports (`level > 0`) are local.
  - Only the first part of the dotted name is checked.
  - `__future__` is stdlib.
  - In the JS harness, `node:`-prefixed specifiers are built-ins once the prefix is dropped.
  - `.claude/workflows/agentic-implement.js` may use no `require` at all. Then the JS part finds nothing, which is fine.
  - WP-02 does not write `flow-budget.json`: WP-03 does, last. Until then the budget test on this repository fails with `flow-budget.json is missing`, an expected failure (section 11); the tests on temporary roots must pass.
  - The acceptance file and `test_lean.py` itself live in `.claude/bin`, which the marker scan reads: build the marker words from parts, never write them literally.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_lean.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-03 · Docs, notes, release and the moved tests
- Wave 2: the docs and notes describe WP-01 and WP-02.
- Depends on: WP-01, WP-02.
- Files: `docs/how-it-works.md`, `docs/how-to/plugin.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/bin/test_field_fixes.py`, `.claude/bin/test_acceptance_v217.py`, `.claude/flow-budget.json`, `.claude/flow-history.json`.
- ACs: AC-006.
- **Patterns to mirror:** `docs/how-it-works.md:253`, `docs/how-to/plugin.md:110-120`, `upgrade.py:156-170` and `test_hook_diagnosis.py:1-10`.
- **Gotchas:**
  - Write `flow-budget.json` after the notes in `upgrade.py`, which `code_lines` counts: measure with `test_lean.code_lines(ROOT)` and `prompt_bytes(ROOT)`, round up to the next 10 and 100, and set `why`.
  - `flow-history.json` is regenerated last, after every other commit (`agentic.py flow-history`, then `--check`).
  - The moved file imports `InstallCase` and `commit` from `test_install`, as the acceptance file did.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_field_fixes.py"`, `python3 .claude/bin/agentic.py docs-check`, `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v218.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v218.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/agentic.py", ".claude/bin/test_hook_path.py"],
     "acs": ["AC-001", "AC-002"], "mirror": [".claude/bin/agentic.py:73-100", ".claude/bin/agentic.py:395-414", ".claude/bin/test_guardrail.py:44-67"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/test_lean.py"],
     "acs": ["AC-003", "AC-004", "AC-005"], "mirror": [".claude/bin/test_definitions.py:8-28", ".claude/bin/test_layout.py:1-48"]},
    {"id": "WP-03", "wave": 2, "depends_on": ["WP-01", "WP-02"], "files": ["docs/how-it-works.md", "docs/how-to/plugin.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/bin/test_field_fixes.py", ".claude/bin/test_acceptance_v217.py", ".claude/flow-budget.json", ".claude/flow-history.json"],
     "acs": ["AC-006"], "mirror": ["docs/how-it-works.md:253", "docs/how-to/plugin.md:110-120", ".claude/bin/upgrade.py:156-170", ".claude/bin/test_hook_diagnosis.py:1-10"]}
  ]
}
```

## 9. Test strategy
- **Unit:** each WP in its own test file, stdlib `unittest`. The guardrails are themselves tests; their helpers are module-level functions tested on temporary roots.
- **Acceptance:** `.claude/bin/test_acceptance_v218.py`, written from AC-001 to AC-006 before the code. It must be red today:
  - AC-001: the hook loads `launch` and `http.client`;
  - AC-003 to AC-005: `test_lean` does not exist;
  - AC-006: the release is missing.

  AC-002 guards behaviour and may already be green.
- **QA, by hand:**
  - every CI suite, `quality` and `docs-check`;
  - the installed-project run, as CI's `installed` job: there `test_lean`'s budget test skips and its other tests run;
  - the hook timing measured again (20 calls, `hook.py`), reported as a number, never asserted;
  - mutations, at least:
    - the fast path removed;
    - `root_drift` skipped in it;
    - a forbidden module dropped from the list;
    - the budget comparison flipped;
    - the 5 % band ignored;
    - an issue reference no longer recognised;
    - a relative import reported.

## 10. Decisions
| Decision | Discarded | Why |
|---|---|---|
| The fast path lives in `agentic.py`, keyed on `__main__` and `argv` | Edit `hook.py`; a new `guard.py` entry point | `hook.py` is never owned and is what `settings.json` names in every project; a new entry point would change every project's settings. |
| An import budget, not a time budget (user's choice of the four guardrails) | Assert the hook under N ms | Timings vary across CI machines; the forbidden modules are what made it slow. |
| `stage`, `verification` and `reports` stay on the hook path | Lazy-import them in `stage` | The stop gate needs them; the gain left is not measured and the change would reach the gate's code. |
| A separate `flow-budget.json`, with a two-sided 5 % band | Extend `quality-baseline.json`; a one-sided cap | The baseline is a project file written by install and only by people; a one-sided cap lets a release shrink the flow and keep the old room, so the diet would not stick. |
| Debt markers need an issue on the same line | Forbid them outright | A marker with an issue is tracked debt; one without is forgotten debt. |
| Guardrails, then the bench and prompt trimming in the next release (user's choice) | All at once | The bench spends real sessions and needs its own approval; trimming needs measurements per prompt. |

## 11. Risks and open questions
- **The timing gain is measured in one container only** (100 ms against 58 ms per call). Windows and other machines are not measured; the import budget holds everywhere.
- **`sys.stdlib_module_names` is missing on Python 3.9.** The stdlib test skips there; the other CI jobs run it.
- **The 5 % band makes every larger change touch `flow-budget.json`.** That is the point, but it adds one line to such PRs.
- **A fix cycle after WP-03.** Any code change after WP-03 wrote `flow-budget.json` can push a measure past it: WP-03 then measures and writes the budget again, as the last change before the release.
- **`verify` does not run `acceptance/`, `qa/`, `quality` or `docs-check`**, as in earlier designs; QA runs them by hand. Its phase labels do not match their suites, as before.
- **Expected failures between wave 0 and WP-03.** Once `test_acceptance_v218.py` exists, `test_layout.py` and v217's `ReleaseTests` fail until WP-03 deletes `test_acceptance_v217.py`; the budget test on this repository fails until WP-03 writes `flow-budget.json`. `flow-history --check` fails until the last commit.
- **Archive and index by hand.** On approval, the maintainer copies this file to `docs/architecture/0025-lean-guardrails.md` and adds its line to `docs/architecture/README.md`.
