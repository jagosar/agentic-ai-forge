# Architecture: the hook and agentic.py resolve the same root inside a git worktree (agentic-flow 2.22.2)
Type: fix · Size: standard

## 1. Goal

A field session in a git worktree (2026-11-26, a PowerShell project) could not start native `/implement`: `hooks-check` exited 3, "the guardrail hook did not run for this call". Claude Code keeps `CLAUDE_PROJECT_DIR` at the main checkout after the session enters a worktree. It documents that the hook's stdin JSON `cwd` is the worktree root (https://code.claude.com/docs/en/worktrees.md). The hook command `python3 "$CLAUDE_PROJECT_DIR/.claude/bin/hook.py"` therefore ran the main checkout's guard, whose root was the main checkout. Its heartbeat, claims, ledger, manifest and git checks all belonged to the main checkout. `agentic.py` commands run from the worktree used the worktree as their root. Writes were broken too, though less visibly: a worktree under `.claude/worktrees/` is, for the main checkout's guard, a path under `.claude/`, which no flow agent may write.

After this fix, `hook.py` reads the call's `cwd`. When a call of the session's main thread has its `cwd` in a linked worktree of the same repository that has the flow installed, `hook.py` runs that worktree's guard with that worktree as its root, and records the choice for the session. An agent's call (one with `agent_id`) is judged in the root the main thread chose for its session, never by its own `cwd`, so an agent that changes directory cannot change guard; a fallback agent (`AGENTIC_WP`) keeps the root its launcher set. `core.ROOT` follows the same rule when `CLAUDE_PROJECT_DIR` names the main checkout but the running `agentic.py` lives in the worktree. Native `/implement` then works in a worktree with no move to the main folder and no fallback.

## 2. Scope

### Included

- `.claude/bin/hook.py`: `linked_worktree(start, project)`; the root and the guard chosen from the main thread's stdin `cwd` and remembered per session; agents pinned to it; stdin handed on unchanged.
- `.claude/bin/core.py`: `ROOT` is the worktree when `CLAUDE_PROJECT_DIR` names another checkout of the same repository and the running script lives in a linked worktree.
- `.claude/bin/guardrail.py`: the worktree hint of the hook diagnosis also says to update the flow in the checkout the session started from.
- Worktrees: any linked worktree of the same repository, under `.claude/worktrees/` or elsewhere (`git worktree add ../folder`, which `sessions-check` recommends). User's choice.
- Release 2.22.2: notes, `how-it-works.md`, the budget, the version pin of `test_acceptance_v222.py`.

### Excluded (non-goals)

- Running git to find worktrees: the rule reads `.git` files only.
- A worktree without the flow (no `.claude/bin/agentic.py`), a worktree of another repository, a submodule: the guard behaves as today.
- Changing `.claude/settings.json`'s hook command.
- A main checkout whose `hook.py` predates this release. It still runs its old logic; the diagnosis hint names the remedy.
- `sessions-check` behaviour and message.
- `waiting.py` (the other never-owned hook script, `.claude/bin/waiting.py:106-112`) still roots on `CLAUDE_PROJECT_DIR`: in a worktree its waiting record lands in the main checkout. It only observes; left for a later release.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency. `git` (for the tests' worktrees).

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The repository's suites CI also runs: `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`
- The workflow: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`

## 4. Repository structure

```
.claude/bin/hook.py                      by hand (never owned), committed first: linked_worktree, choose_root, the session's root
.claude/bin/test_worktree_root.py        WP-01  new: unit cases of linked_worktree and choose_root
.claude/bin/core.py                      WP-02  project_root(); ROOT = project_root()
.claude/bin/guardrail.py                 WP-02  the worktree hint's text
.claude/bin/test_core_root.py            WP-02  new: unit cases of project_root
docs/how-it-works.md                     WP-03  one paragraph on worktrees
.claude-plugin/plugin.json               WP-03  2.22.2
.claude/bin/upgrade.py                   WP-03  NOTES["2.22.2"]
.claude/flow-budget.json                 WP-03
.claude/bin/test_acceptance_v222.py      WP-03  its version pin (line 229): 2.22.2
.claude/bin/test_worktree_hook.py        AT
.claude/flow-history.json                by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| The hook launcher: chooses `agentic.py` from `CLAUDE_PROJECT_DIR` or its own location; fails closed (exit 2) when it cannot choose; runs it with `runpy` and `argv = [script, "hook"]` | `.claude/bin/hook.py:1-29` | Standard library only, Python 3.9, no annotations, never imports `agentic.py` at module level | read |
| `hook.py` is never owned by any package, and `validate` rejects a plan that gives it to one | `.claude/bin/core.py:50-54`, `.claude/bin/core.py:296-302` | It is edited by hand in this release | read |
| `ROOT` is `CLAUDE_PROJECT_DIR`, else `SOURCE_ROOT` (two levels above `core.py`), computed at import | `.claude/bin/core.py:18-24` | Every module reads `core.ROOT`; it must stay a module constant | read |
| `root_drift` refuses a command whose `CLAUDE_PROJECT_DIR` names another repository while the cwd is outside it; a worktree under `<main>/.claude/worktrees/` is inside main, so today it passes and acts on main | `.claude/bin/core.py:174-186` | With the new `ROOT` it sees `SOURCE_ROOT == ROOT` and returns None | read |
| The guard reads the hook's JSON with `compat.read_stdin_text()`, which reads `sys.stdin.buffer` | `.claude/bin/guardrail.py:639-652`, `.claude/bin/compat.py:112-114` | `hook.py` replaces `sys.stdin` with a `TextIOWrapper` over a `BytesIO` of the bytes it read | read |
| A write outside `ROOT` is refused; a path under `.claude/` is refused (`flow_path_refused`) | `.claude/bin/guardrail.py:322-347`, `.claude/bin/core.py:304-306` | Why every write in `<main>/.claude/worktrees/<n>/` is refused today | read |
| The heartbeat lives in `ROOT/.claude/state/hook-seen.json` | `.claude/bin/guardrail.py:382-397` | | read |
| The diagnosis: `_worktree` (git), heartbeats of ROOT, main and cwd's top level, the "different project roots" hint | `.claude/bin/guardrail.py:509-532`, `.claude/bin/guardrail.py:545-560` | Only the hint's text changes; keep the words `different project roots` and `hook-seen.json` (`.claude/bin/test_hook_diagnosis.py:141-143`) | read |
| A test that creates a worktree under `.claude/worktrees/` and runs `hooks-check` there | `.claude/bin/test_hook_diagnosis.py:120-145` | Copy its git setup (`GIT`, commit, `git worktree add`) | read |
| A test copy of the flow in a temporary git repo (`hook_copy`) | `.claude/bin/test_hook_path.py:27-40` | The AT and WP-01 build repos with `.claude/bin` committed, so a worktree has the flow | read |
| Running `hook.py` with a payload and `AGENTIC_WP` | `.claude/bin/test_guardrail.py:305-321` | | read |
| Install copies `.claude/bin/<name>.py` for the names in `INSTALL_BIN` (`hook` included) | `.claude/bin/installer.py:19-30` | No new module: nothing to add | read |
| The settings run the hook through `$CLAUDE_PROJECT_DIR/.claude/bin/hook.py`, pinned by a test | `.claude/bin/test_definitions.py:349-351` | Unchanged | read |
| Release notes go newest first, `2.22.1` at the top of the recent block | `.claude/bin/upgrade.py:156-165` | `2.22.2` right before `2.22.1` | read |
| `test_acceptance_v222.py` pins the plugin version on line 229 | `.claude/bin/test_acceptance_v222.py:226-229` | `"2.22.1"` → `"2.22.2"` | read |
| `test_pinned_conflict.py` (2.22.1) checks the version is ≥ 2.22.1 and that `"2.22.1"` is followed by `"2.22.0"` in `NOTES` | `.claude/bin/test_pinned_conflict.py:193-200` | Still true with `2.22.2` placed before `2.22.1` | read |
| Claude Code keeps `CLAUDE_PROJECT_DIR` at the main checkout and gives the worktree root as the stdin `cwd`; whether Bash commands get `CLAUDE_PROJECT_DIR` is not documented | https://code.claude.com/docs/en/worktrees.md | The field diagnosis showed `project_dir = null` in a Bash call | inferred |

What must NOT change: the hook's behaviour outside a linked worktree (same guard, same root, same exit codes); `settings.json`; the import budget of the hook (`test_hook_path.py`, `test_lean_hook.py`).

## 5. Data model

```python
# hook.py
GITDIR_PREFIX = "gitdir:"   # the first line of a linked worktree's .git file
WORKTREES_DIR = "worktrees"  # a linked worktree's git dir is <common>/worktrees/<name>
FLOW_ENTRY = Path(".claude") / "bin" / "agentic.py"
SESSION_ROOTS = Path(".claude") / "state" / "worktree-roots.json"  # under the project (CLAUDE_PROJECT_DIR)
SESSION_ROOTS_MAX = 20  # sessions remembered; the oldest are dropped
```

`<project>/.claude/state/worktree-roots.json`: `{"<session_id>": {"root": "<absolute path>", "ts": <epoch seconds>}}`, at most `SESSION_ROOTS_MAX` entries (the newest by `ts`). It lives under `.claude/state/`, which no agent may write (`.claude/bin/core.py:50-54`). Every other piece of state lives in `<root>/.claude/state/`, as for any root.

## 6. Contracts between modules

### C1 · `hook.linked_worktree(start, project) -> Path | None` (hook.py; used by core.py and the tests)

- `start`, `project`: `str` or `Path`. Never raises; on `OSError` or `ValueError` it returns `None`.
- From `Path(start).resolve()` up through its parents, the first directory `d` holding a `.git` entry decides:
  - `.git` is a directory → `None` (a main checkout).
  - `.git` is a file whose first line starts with `gitdir:` → `gd` = the rest, stripped, resolved against `d` when relative. When `gd.parent.name` is not `worktrees` → `None` (a submodule). Otherwise `common = gd.parent.parent`.
  - Anything else → `None`.
- No `.git` entry anywhere up the path → `None`.
- `project`'s common git dir: `project/.git` when it is a directory; when it is a file, the `common` computed from it the same way. When it has none → `None`.
- Returns `d` (resolved) when `common == project's common dir` (both resolved) and `d / ".claude/bin/agentic.py"` is a file; `None` otherwise.

### C2 · `hook.choose_root(raw, project, env) -> Path` (hook.py)

- `raw`: the bytes of stdin. `project`: today's root (`CLAUDE_PROJECT_DIR`, else two levels above `hook.py`). `env`: a mapping (the process environment; tests pass a dict).
- The payload: `json.loads(raw.decode("utf-8"))` when it is a dict; any decoding error or other shape → `Path(project)`. `cwd`, `session_id` and `agent_id` are read only when they are non-empty strings.
- `env.get("AGENTIC_WP")` set → `Path(project)` (a fallback agent: its launcher already set `CLAUDE_PROJECT_DIR` to the run's root, `.claude/bin/launch.py:236`).
- `agent_id` present (a subagent of the session) → the root remembered for `session_id` when it is still `linked_worktree(root, project) == root`; otherwise `Path(project)`. The agent's own `cwd` is never read.
- Otherwise (the main thread): `root = linked_worktree(cwd, project)` when `cwd` is given, else `None`; then `remember(project, session_id, root)` when `session_id` is given; returns `root` or `Path(project)`.
- `remember(project, session_id, root)`: writes `SESSION_ROOTS` under `project` with that session's entry set to `{"root": str(root), "ts": time.time()}` when `root` is not `None`, or removed when it is; it keeps the newest `SESSION_ROOTS_MAX`; writes a temporary file beside it and `os.replace`s it; writes nothing when the entry would not change; any `OSError` or `ValueError` is ignored (an agent then falls back to `project`, today's behaviour).
- `remembered(project, session_id) -> Path | None`: the entry's `root`, or `None` when the file, the entry or its shape is missing.

### C3 · `hook.main()` (the launcher)

1. `raw = sys.stdin.buffer.read()`.
2. `project` as today; `root = choose_root(raw, project, os.environ)`.
3. When `root` differs from `Path(project)`: `os.environ["CLAUDE_PROJECT_DIR"] = str(root)`. Otherwise the environment is left as it is.
4. `sys.stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")`; `sys.argv = [str(script), "hook"]` with `script = root / ".claude/bin/agentic.py"`; `runpy.run_path(str(script), run_name="__main__")`.
- `runpy.run_path` leaves `hook.py`'s own folder (the main checkout's `.claude/bin`) as `sys.path[0]`; the worktree's `agentic.py` and `core.py` insert their own folder first (`.claude/bin/agentic.py:79`, `.claude/bin/core.py:15`), so `import hook` inside the worktree's `core` loads the worktree's copy.
- Steps 1-2 inside the existing `try`: any exception prints today's `[agentic hook.py] cannot choose the guard, blocked for safety: ...` and exits 2.

### C4 · `core.project_root() -> Path` (core.py); `ROOT = project_root()`

- `env = os.environ.get("CLAUDE_PROJECT_DIR")`.
- When `env` is set and `hook.linked_worktree(SOURCE_ROOT, env)` equals `SOURCE_ROOT.resolve()`: `SOURCE_ROOT`.
- Otherwise: `Path(env or SOURCE_ROOT)` (today's value).
- `core` imports `linked_worktree` from the sibling `hook` module (`from hook import linked_worktree`). `hook.py` has no side effect at import.

### C5 · The diagnosis hint (guardrail.py `_hints`)

The worktree hint becomes: `the hook ran, but wrote its heartbeat in <path>: the hook and this command see different project roots (a git worktree?). The hook comes from the checkout the session started in: update the flow there (agentic.py install), or start the session in this folder`.

## 7. Conventions

- English for code, comments and docs; the repository's existing style.
- Standard library only. `hook.py` stays Python 3.9, no annotations, no flow import.
- No line over 120 characters; functions ≤ 60 lines; nesting ≤ 4 (`agentic.py quality`).
- Every literal that decides behaviour is a named module constant with a comment.
- Docs and notes name no flow version outside `upgrade.NOTES` and `plugin.json`.
- Commits: `type: summary` in lowercase, ending with the session's attribution lines.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · In a worktree under `.claude/worktrees/`, the hook writes its heartbeat in the worktree and `hooks-check` passes (the bug)
  - Scenario: a temporary git repo with `.claude/bin` (a copy of this checkout's, without tests), `.claude/settings.json`, `.claude/agents` and `architecture.md` holding `test_agentic.MANIFEST`, all committed; `git worktree add <repo>/.claude/worktrees/w -b w`.
  - Action: run `<repo>/.claude/bin/hook.py` with `CLAUDE_PROJECT_DIR=<repo>`, cwd `<repo>` and stdin `{"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "s1", "cwd": "<repo>/.claude/worktrees/w"}`; then, from the worktree, `python3 .claude/bin/agentic.py hooks-check` with `CLAUDECODE=1` and no `CLAUDE_PROJECT_DIR`.
  - Expected: the hook exits 0; `<worktree>/.claude/state/hook-seen.json` exists with `tool` `Bash`; `hooks-check` exits 0 with `"mode": "live"`.
  - Must not: `<repo>/.claude/state/hook-seen.json` created or changed.
  - Check: `test_worktree_hook.py`, AC-001 tests.
  - WP: WP-01
- AC-002 · A package's write in the worktree is judged against the worktree's manifest and paths
  - Scenario: the repo of AC-001; the worktree's architecture.md is the committed one.
  - Action: (a) the fallback: `hook.py` with `AGENTIC_WP=WP-01`, `CLAUDE_PROJECT_DIR=<worktree>` (what the launcher sets) and a `Write` payload for `<worktree>/src/a.py`, then for `<worktree>/src/c.py`, each with `"cwd": "<worktree>"` and `content` `"x = 1\n"`. (b) the native engine: with `CLAUDE_PROJECT_DIR=<repo>`, first a main-thread call (AC-001's payload, `session_id` `s1`), then an agent call `{"tool_name": "Bash", "tool_input": {"command": "python3 .claude/bin/agentic.py claim WP-01"}, "session_id": "s1", "agent_id": "a1", "agent_type": "implementer", "cwd": "<worktree>"}`, then the two `Write` payloads with the same `session_id`, `agent_id` and `agent_type`.
  - Expected: in (a) and (b), the write to `src/a.py` exits 0 and the write to `src/c.py` exits 2 with `does not own src/c.py` in stderr; in (b) `<worktree>/.claude/state/claims.json` names `a1`.
  - Must not: either stderr containing `.claude/worktrees`.
  - Check: `test_worktree_hook.py`, AC-002 tests.
  - WP: WP-01
- AC-003 · A worktree outside the main checkout works the same way
  - Scenario: the repo of AC-001 plus `git worktree add <tmp>/outside -b o`, `<tmp>` another temporary folder.
  - Action: AC-001's hook call with `"cwd": "<tmp>/outside"`.
  - Expected: `<tmp>/outside/.claude/state/hook-seen.json` exists; the main checkout's does not.
  - Must not: the main checkout's heartbeat.
  - Check: `test_worktree_hook.py`, AC-003 test.
  - WP: WP-01
- AC-004 · Outside a linked worktree of the same repository with the flow, nothing changes
  - Scenario: the repo of AC-001; another git repo `<other>` with a worktree `<other>/wt` holding a copy of `.claude/bin`; a worktree `<repo>/.claude/worktrees/bare` from which `.claude/bin/agentic.py` was deleted; a submodule-like folder whose `.git` file says `gitdir: ../.git/modules/m`.
  - Action: `hook.choose_root(raw, <repo>, {})` (main-thread payloads, no `session_id`) for `cwd` = `<repo>`, `<repo>/src`, `<other>/wt`, `<repo>/.claude/worktrees/bare`, the submodule folder, a folder with no git, and for `raw` = `b"not json"`, `b"[]"`, `b'{"cwd": 3}'`; and `hook.py` run with `AGENTIC_WP=WP-01` and stdin `not json`.
  - Expected: every `choose_root` call returns `<repo>`; `choose_root` with `cwd` = `<repo>/.claude/worktrees/w/src` returns the `w` worktree. The `hook.py` run exits 2 with `guardrail error, blocked for safety` in stderr (today's answer).
  - Must not: an exception from `choose_root` or `linked_worktree`.
  - Check: `test_worktree_hook.py`, AC-004 tests.
  - WP: WP-01
- AC-008 · An agent cannot change guard by changing directory
  - Scenario: the repo of AC-001 with a second worktree `<repo>/.claude/worktrees/x -b x`; with `CLAUDE_PROJECT_DIR=<repo>`, a main-thread call of session `s1` with `cwd` = the `w` worktree.
  - Action: (a) AC-002 (b)'s claim call (`agent_id` `a1`, `agent_type` `implementer`, `AGENTIC_WP` unset), then a call of the same agent with `cwd` = `<repo>/.claude/worktrees/x` and a `Write` for `<repo>/.claude/worktrees/x/src/a.py`; (b) an agent call of a session with no main-thread call (`session_id` `s2`) with `cwd` = the `w` worktree; (c) `AGENTIC_WP=WP-01`, `CLAUDE_PROJECT_DIR=<repo>` and `cwd` = the `w` worktree; (d) `choose_root` for (a), (b) and (c).
  - Expected: (a) exits 2 with `you cannot write outside the repo` (judged in `w`); `<repo>/.claude/worktrees/x/.claude/state/` has no `hook-seen.json`. (d) returns the `w` worktree for (a) and `<repo>` for (b) and (c). `<repo>/.claude/state/worktree-roots.json` holds `s1` with the `w` worktree's root.
  - Must not: the `x` worktree's guard judging an agent of `s1`; an agent call writing `worktree-roots.json`.
  - Check: `test_worktree_hook.py`, AC-008 tests.
  - WP: WP-01
- AC-005 · `core.ROOT` is the worktree when `CLAUDE_PROJECT_DIR` names the main checkout but the script lives in the worktree
  - Scenario: the repo and worktree of AC-001.
  - Action: `python3 -c "import sys; sys.path.insert(0, '<dir>/.claude/bin'); import core; print(core.ROOT)"` run (a) with `<dir>` = the worktree, `CLAUDE_PROJECT_DIR=<repo>`; (b) with `<dir>` = `<repo>`, `CLAUDE_PROJECT_DIR=<repo>`; (c) with `<dir>` = the worktree and no `CLAUDE_PROJECT_DIR`; (d) with `<dir>` = a copy of `.claude/bin` outside any repo, `CLAUDE_PROJECT_DIR=<repo>`.
  - Expected: (a) the worktree; (b) `<repo>`; (c) the worktree; (d) `<repo>` (each compared resolved).
  - Must not: (a) printing `<repo>`.
  - Check: `test_worktree_hook.py`, AC-005 tests.
  - WP: WP-02
- AC-006 · The diagnosis says where to update the flow
  - Scenario: `test_hook_diagnosis.py`'s worktree setup (the worktree's heartbeat absent, the main one fresh).
  - Action: `hooks-check` from the worktree with `CLAUDECODE=1`.
  - Expected: exit 3; one hint contains `different project roots`, `hook-seen.json` and `update the flow there`.
  - Must not: the hint missing.
  - Check: `test_worktree_hook.py`, AC-006 test.
  - WP: WP-02
- AC-007 · Release 2.22.2
  - Scenario: the repository.
  - Action: read the release files; run `agentic.py quality`.
  - Expected: `plugin.json`'s version as a tuple of ints ≥ `(2, 22, 2)`; `upgrade.NOTES["2.22.2"]` exists, comes right before `"2.22.1"`, and some note contains `worktree`; `docs/how-it-works.md` contains `worktree` and `cwd` and does not contain `2.22.2`; `quality` exits 0.
  - Must not: a line of `test_acceptance_v222.py` containing both `plugin[` and `"2.22.1"`.
  - Check: `test_worktree_hook.py`, AC-007 test (flow repo only).
  - WP: WP-03

### Work packages

#### WP-01 · The hook follows the call's worktree
- Wave 1.
- Files: `.claude/bin/test_worktree_root.py`; and `.claude/bin/hook.py`, by hand (never owned: no package may own it).
- Implements C1, C2, C3.
- ACs: AC-001, AC-002, AC-003, AC-004, AC-008.
- **Patterns to mirror:** `.claude/bin/hook.py:1-29` (style, fail closed); `.claude/bin/test_hook_diagnosis.py:120-145` (worktrees in tests); `.claude/bin/test_hook_path.py:27-40` (a repo with the flow).
- **Gotchas:**
  - Read stdin as bytes once (`sys.stdin.buffer.read()`); the guard reads `sys.stdin.buffer` again, so hand it a `TextIOWrapper(BytesIO(raw), encoding="utf-8")`.
  - Set `CLAUDE_PROJECT_DIR` only when the worktree was chosen, before `runpy`: `core.ROOT` is computed when the worktree's `core` is imported.
  - A worktree's `.git` file uses forward slashes on Windows too (`gitdir: C:/…/.git/worktrees/w`); `Path` reads both.
  - `Path.resolve()` on Windows may change the drive letter's case: compare resolved paths only.
  - Keep `hook.py` free of flow imports; `json`, `io`, `runpy` and `time` are standard.
  - Only main-thread calls write `worktree-roots.json`; an agent's call only reads it.
  - Commit `hook.py` first: WP-02's `core.py` imports `linked_worktree` from it, so the order is a dependency, not a style.
- **Exact imports and APIs:** `import io, json, os, runpy, sys, time`; `from pathlib import Path`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p test_worktree_root.py`; `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · `core.ROOT` and the diagnosis follow the worktree
- Wave 2 (`core.py` imports `linked_worktree` from WP-01's `hook.py` at module level: without it every flow module fails to import).
- Files: `.claude/bin/core.py`, `.claude/bin/guardrail.py`, `.claude/bin/test_core_root.py`.
- Implements C4, C5. Consumes C1 by implementation (`depends_on`: WP-01).
- ACs: AC-005, AC-006.
- **Patterns to mirror:** `.claude/bin/core.py:18-24` (the root constants); `.claude/bin/core.py:174-186` (`root_drift`, unchanged); `.claude/bin/guardrail.py:545-560` (the hints).
- **Gotchas:**
  - `core` is imported by every flow module and by the hook: the import of `hook` must stay cheap (no git, a few `stat` calls).
  - `from hook import linked_worktree` works because `core.py` already puts its folder on `sys.path` (`.claude/bin/core.py:15`).
  - Known red until WP-03: `test_lean` (the budget) and AC-007.
- **Exact imports and APIs:** `from hook import linked_worktree  # noqa: E402` after the `compat` import.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p test_core_root.py`; `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-03 · Documentation and release 2.22.2
- Wave 3 (it measures the budget after WP-01 and WP-02).
- Files: `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_acceptance_v222.py`.
- Depends on WP-01 and WP-02 by implementation.
- ACs: AC-007.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-165`.
- **What to write:** a paragraph in `how-it-works.md` (section 4, guardrails): in a worktree the hook reads the call's `cwd` and judges with that worktree's guard and root; `CLAUDE_PROJECT_DIR` names the checkout the session started in, so that checkout's `hook.py` must be this release or later. `NOTES["2.22.2"]`: one note naming `worktree`. The budget: measured with `test_lean.code_lines(Path('.'))` and `test_lean.prompt_bytes(Path('.'))`, with a `why`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_*.py"`; `python3 -m unittest discover -s acceptance`; `python3 -m unittest discover -s qa`; `python3 .claude/bin/agentic.py quality`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)", "Bash(python3 .claude/bin/agentic.py quality)"],
  "acceptance": {"files": [".claude/bin/test_worktree_hook.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_worktree_hook.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/test_worktree_root.py"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-008"], "mirror": [".claude/bin/hook.py:1-29", ".claude/bin/test_hook_diagnosis.py:120-145", ".claude/bin/test_hook_path.py:27-40"]},
    {"id": "WP-02", "wave": 2, "depends_on": ["WP-01"], "files": [".claude/bin/core.py", ".claude/bin/guardrail.py", ".claude/bin/test_core_root.py"],
     "acs": ["AC-005", "AC-006"], "mirror": [".claude/bin/core.py:18-24", ".claude/bin/core.py:174-186", ".claude/bin/guardrail.py:545-560"]},
    {"id": "WP-03", "wave": 3, "depends_on": ["WP-01", "WP-02"], "files": ["docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_acceptance_v222.py"],
     "acs": ["AC-007"], "mirror": [".claude/bin/upgrade.py:156-165"]}
  ]
}
```

## 9. Test strategy

- **Unit:** WP-01 in `test_worktree_root.py` (`linked_worktree` over real `git worktree add` folders and hand-written `.git` files; `choose_root` over byte payloads); WP-02 in `test_core_root.py` (`project_root` in subprocesses, since `ROOT` is fixed at import).
- **Acceptance (AT, wave 0):** `.claude/bin/test_worktree_hook.py`, red today: AC-001's heartbeat lands in the main checkout, AC-002's writes are refused as `.claude/` paths, `choose_root` does not exist. Repos are built in temporary folders with `git init`, a copy of `.claude/bin` without `test_*.py` and `__pycache__`, `.claude/settings.json`, `.claude/agents`, and `architecture.md` holding `test_agentic.MANIFEST`, committed with `GIT` from `test_hook_diagnosis.py`. `hook.py` is run with `sys.executable`. AC-007 is skipped outside the flow repo. The AT must not write `"2.21.2"`, `"2.22.0"` or `"2.22.1"` on a line containing `version`: the earlier acceptance files forbid it.
- **QA:** a real `claude --worktree` session is out of reach in CI; QA checks a Windows-style `.git` file (`gitdir: C:/…`) and a relative `gitdir`.
- Executed by hand (`"maintainer": true`).

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| Root from the stdin `cwd` | The hook process's cwd; `git rev-parse` | The stdin `cwd` is documented as the worktree root; the process cwd is not. git costs a process per tool call (the hook's budget, design 0025). |
| Any linked worktree of the same repository | Only `.claude/worktrees/` | User's choice: `sessions-check` recommends `git worktree add ../folder`. |
| Also fix `core.ROOT` when `CLAUDE_PROJECT_DIR` names the main checkout | Only the hook | User's choice: whether Bash commands get the variable is not documented; if they did, a worktree's `agentic.py` would act on the main checkout (`root_drift` does not catch a worktree inside it). |
| One implementation in `hook.py`, imported by `core` | A new module; two copies | A new module that `hook.py` imports would have to be never owned and installed too; `hook.py` already is both. |
| Only a worktree with the flow installed, of the same repository | Any `.git` file | A worktree without `agentic.py` has no guard to run; another repository's guard must not judge this session's calls. |
| Only the main thread follows the `cwd`; an agent uses the root its session's main thread chose (remembered in the project's state), a fallback agent the one its launcher set | Every call follows its own `cwd`; only `AGENTIC_WP` pinned | User's choice: an agent that ran `cd` into another worktree would otherwise be judged by that worktree's plan and guard, where today its writes are refused as outside the root. |
| Three waves (WP-01 → WP-02 → WP-03) | WP-01 and WP-02 in one wave | `core.py` imports from `hook.py` at module level; the release measures both. |
| Fall back to today's root on any doubt | Fail closed | Falling back is today's behaviour, never less safe; the guard still fails closed on its own errors. |
| Version 2.22.2 | 2.23.0 | A fix. |

## 11. Risks and open questions

- **An old `hook.py` in the main checkout** keeps today's behaviour: the session starts there, so the hook comes from there. The diagnosis hint names the remedy (C5).
- **Bash and `CLAUDE_PROJECT_DIR`**: not documented. C4 covers the variable being set; without it, `ROOT` is already the worktree.
- **Desktop worktree sessions**: the docs say hook commands run in the main checkout root there; the stdin `cwd` is still documented as the worktree. Not measured on desktop.
- **A real `claude --worktree` run** is not in the tests; the AT reproduces the documented values.
- **Subagents' `session_id`** is inferred to be the parent session's (design 0024 calls it not verified). If it were another id, a native agent would fall back to the main checkout's root: today's behaviour, so its writes in the worktree are refused (a visible stop, not a hole).
- **The `verify` phases** run the bench, the workflow and `.claude/bin`'s suite; the root `acceptance/` and `qa/` suites CI also runs are only in WP-03's validation.
- **`waiting.py`** still writes its waiting record to the main checkout from a worktree (Excluded).
