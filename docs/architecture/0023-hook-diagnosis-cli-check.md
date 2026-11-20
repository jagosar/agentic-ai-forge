# Architecture: make the guard run on Windows, and say why when it does not (agentic-flow 2.16.0)
Type: change · Size: standard

## 1. Goal
On Windows with Claude Desktop, `/implement` could not start because the guardrail hook did not run. A field report traced the likely cause:
- Claude Code did not find Git Bash, which was installed per user, outside Program Files.
- Without Git Bash, hooks run in PowerShell, where `"$CLAUDE_PROJECT_DIR/..."` is not expanded, so the hook pointed at `C:\.claude\bin\hook.py`.
- Setting `CLAUDE_CODE_GIT_BASH_PATH` fixed it.

This design makes the native workflow work there, with no CLI. `agentic.py doctor` detects the case on Windows, and `doctor --fix` writes the path into `.claude/settings.local.json`, the route the Claude Code docs give. A failed live `hooks-check` says which cause applies, Git Bash first. For the fallback, which the user wants only when needed, there are two changes:
- the agents' environment drops `CLAUDE_CODE_SIMPLE`, the one inherited variable documented to switch off the saved login, and nothing else;
- `require_cli` reads the documented exit code and `authMethod`, and stops repeating the false claim that Claude Desktop's sign-in is not shared.

Issues 120 and 121.

## 2. Scope
### Included
- **Git Bash detection.** `guardrail.git_bash_state()` is a pure function with injectable inputs. On Windows it reports:
  - whether `CLAUDE_CODE_GIT_BASH_PATH` is set, in the environment or in a settings file's `env`;
  - whether Git Bash is at a default Program Files path;
  - the `bash.exe` that belongs to the `git.exe` on the PATH.

  Off Windows it returns `None`.
- **`hooks-check` diagnosis** (already implemented in this branch, kept): it gains `git_bash` and a Git Bash hint first in the list.
- **`doctor`:**
  - a `git-bash` finding: `auto` when a Git Bash was found outside the defaults and nothing configures it, `mention` when none was found;
  - `doctor --fix` writes `env.CLAUDE_CODE_GIT_BASH_PATH` into `.claude/settings.local.json`, keeping the rest of that file.
- **`core.child_env`** drops `CLAUDE_CODE_SIMPLE`, and only that, in every mode.
- **`launch.require_cli`** (already implemented, kept and corrected):
  - logged out means a JSON answer with exit code 1, `authMethod: "none"` or `loggedIn: false`, and stops the run;
  - an answer that is not JSON warns and goes on;
  - the logged-out message lists the names of the inherited `CLAUDE_*` and `ANTHROPIC_*` variables, never their values, and makes no claim about Claude Desktop's sign-in.
- **The fake `claude`** answers logged out as the docs describe: `{"authMethod": "none"}`, exit 1.
- **Docs:**
  - `/implement`: `doctor --fix` for Git Bash, `AGENTIC_CLAUDE`, and the inherited variables;
  - the how-to hub, still at 260 lines or fewer, and `how-it-works.md`;
  - upgrade notes for 2.16.0, rewritten.
- **Release 2.16.0:** `test_acceptance_v216.py` rewritten for this design; `test_runner_reports.py` keeps v215's classes, as already done.

### Excluded (non-goals)
- **No change to the hook commands** (exec form). The minimum Claude Code version that supports it is unknown.
- **No stripping of other variables.** This cloud container authenticates through variables that a full strip would remove; the user is wary of it.
- **No auto-detection of Claude Desktop's bundled CLI.** The user prefers the native workflow, and `AGENTIC_CLAUDE` is documented.
- **No writing of settings outside `doctor --fix`.** `install` does not write them, and `hooks-check` only points at the fix.
- **Separate issues:** briefs that drop annexes, the dotfile reference regex, a branch or worktree lock for `/implement`, and a network check.

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
.claude/bin/guardrail.py                       WP-01
.claude/bin/test_guardrail.py                  WP-01
.claude/bin/doctor.py                          WP-02
.claude/bin/test_doctor.py                     WP-02
.claude/bin/core.py                            WP-03
.claude/bin/launch.py                          WP-03
.claude/bin/testutil.py                        WP-03
.claude/bin/test_launcher.py                   WP-03
.claude/commands/implement.md                  WP-04
docs/how-to/README.md                          WP-04
docs/how-it-works.md                           WP-04
.claude-plugin/plugin.json                     WP-04 (already 2.16.0)
.claude/bin/upgrade.py                         WP-04
.claude/bin/test_runner_reports.py             WP-04 (already moved from v215)
.claude/bin/test_acceptance_v216.py            AT (rewritten)
.claude/flow-history.json                      regenerated by hand as the PR's last commit
```

## 4b. Existing code context
The branch `claude/release-2-16-0` already holds the first version of this design's code, uncommitted: `hook_diagnosis`, `require_cli`, the fake's `auth status`, the docs and the release. This design keeps it and changes what section 2 lists.

| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| The diagnosis: `_json_file`, `_declares_hook`, `_settings_entries`, `_hook_command`, `_git`, `_worktree`, `_heartbeat(s)`, `_hints`, `hook_diagnosis`, and its use in `hooks_check` | `.claude/bin/guardrail.py:349-470` | Small private helpers that never raise; `_hints` returns a list in a fixed order, with the "/hooks" fallback last | read |
| The dead-hook message, which already names python3 and worktrees | `.claude/bin/guardrail.py:69-77` | It gains "Git Bash not found" | read |
| The operating-system layer: `IS_WINDOWS`, `resolve` | `.claude/bin/compat.py:17`, `.claude/bin/compat.py:73-79` | Windows decisions read `compat.IS_WINDOWS`; tests inject instead of patching the OS | read |
| `doctor`: findings as dicts (`auto`, `route`, `mention`), a fixed order in `diagnose()`, repairs keyed by code in `REPAIRS`, `report(fix)` re-diagnoses after repairing | `.claude/bin/doctor.py:22-130` | A new `auto` finding needs an entry in `REPAIRS`; `diagnose()` never writes | read |
| `doctor` tests run the command in a temporary `Repo` and parse its last JSON line | `.claude/bin/test_doctor.py:37-60` | On Linux no `git-bash` finding may appear | read |
| `.claude/settings.local.json` is written by `sync-permissions`, merging into what is there | `.claude/bin/installer.py:127-141` | Same: read the JSON, change one key, write it back with `indent=2` | read |
| The agents' environment (also used by `verification.py` for the verify commands, which lose `CLAUDE_CODE_SIMPLE` too) | `.claude/bin/core.py:321-326` | `dict(os.environ, **extra)`, minus `API_AUTH_VARS` under `subscription`. Add `CLAUDE_CODE_SIMPLE` to what is always removed | read |
| `require_cli`, `_auth_status`, `_cli_argv`, the memo and `AUTH_TIMEOUT_S` | `.claude/bin/launch.py:49-92` | `_auth_status` returns the parsed JSON or None; it must now also return the exit code | read |
| The fake's `auth status` answer and `auth.log` | `.claude/bin/testutil.py:51-70` | `FAKE_AUTH=out` changes to `{"authMethod": "none"}`, exit 1 | read |
| The acceptance file of the first version | `.claude/bin/test_acceptance_v216.py:43-267` | Rewritten by the test-author for this design; its fixed PATH/HOME setup for the diagnosis stays | read |
| Claude Code on Windows runs hook commands in Git Bash, or in PowerShell when Git Bash is not installed | code.claude.com/docs/en/hooks.md ("Git Bash on Windows, or PowerShell when Git Bash isn't installed") | Without Git Bash, a shell-form hook "can fail" | inferred |
| `CLAUDE_CODE_GIT_BASH_PATH`: "Windows only: path to the Git Bash executable (bash.exe). Use when Git Bash is installed but not in your PATH"; the setup page shows it in a settings file's `env` | code.claude.com/docs/en/env-vars.md, code.claude.com/docs/en/setup.md | The route `doctor --fix` takes. Whether it applies without a restart is not documented: the message says to restart Claude Code | inferred |
| `CLAUDE_CODE_SIMPLE=1`: "OAuth tokens and keychain credentials aren't read" | code.claude.com/docs/en/env-vars.md | Why it is dropped for the agents | inferred |
| `claude auth status`: "Exits with code 0 if logged in, 1 if not"; `authMethod` is one of `none`, `claude.ai`, `oauth_token`, `api_key`, `api_key_helper`, `third_party`. `loggedIn` is not documented, but CLI 2.1.329 prints it here | code.claude.com/docs/en/cli-reference.md; `claude auth status --json` run here | Read all three | inferred |
| How Claude Code itself searches for Git Bash (PATH, Program Files, the registry) | not documented | `git_bash_state` checks the two Program Files defaults and the `bash.exe` next to the `git.exe` on PATH; the field case had none set and Git under `AppData\Local\Programs\Git` | inferred |
| Tests that pin wording this plan changes | `.claude/bin/test_acceptance_v216.py:233-252` (Claude Desktop sign-in text), `.claude/bin/test_launcher.py:343-382` (`CliBeforeStateTests`, `RequireCliTests`) | The AT rewrites the first; WP-03 keeps the second green | read |

What must not change:
- the live and static success output of `hooks-check`, and the keys its failure JSON already has;
- `doctor`'s existing findings and their order, apart from the new one appended last;
- the agents' environment, apart from `CLAUDE_CODE_SIMPLE`;
- one `auth status` call per process.

## 5. Data model
```python
# guardrail.git_bash_state(...) returns None off Windows, else:
{
  "configured": str | None,   # CLAUDE_CODE_GIT_BASH_PATH from the environment, else from the first settings env that sets it
                              # (counted even if that file does not exist: the person set it on purpose)
  "default": str | None,      # the first existing of DEFAULT_GIT_BASH
  "derived": str | None,      # the bash.exe that belongs to the git.exe on PATH, when that file exists
  "needs_path": bool,         # not configured, no default, derived found: doctor --fix can write it
  "missing": bool,            # not configured, no default, nothing derived: Git Bash not found
}
DEFAULT_GIT_BASH = ("C:\\Program Files\\Git\\bin\\bash.exe", "C:\\Program Files (x86)\\Git\\bin\\bash.exe")
# derived: from which("git") = <root>\cmd\git.exe, <root>\bin\git.exe or <root>\mingw64\bin\git.exe,
# the candidate is <root>\bin\bash.exe (ntpath, so the logic runs and is tested on any OS).

# hook_diagnosis() gains "git_bash": git_bash_state() (None off Windows), read with the settings it already reads.

# doctor finding (appended last in diagnose()):
{"code": "git-bash", "severity": "auto", "message": "...<derived>...", "fix": "write CLAUDE_CODE_GIT_BASH_PATH=<derived> to .claude/settings.local.json"}
{"code": "git-bash", "severity": "mention", "message": "Git Bash was not found: install Git for Windows, or set CLAUDE_CODE_GIT_BASH_PATH"}
```

## 6. Contracts between modules
```python
# .claude/bin/guardrail.py  (WP-01)
DEFAULT_GIT_BASH = ("C:\\Program Files\\Git\\bin\\bash.exe", "C:\\Program Files (x86)\\Git\\bin\\bash.exe")
def git_bash_state(is_windows=None, environ=None, settings_envs=None, which=shutil.which, exists=os.path.isfile):
    """Section 5. Defaults: compat.IS_WINDOWS, os.environ, the "env" objects of ROOT/.claude/settings.json,
    ROOT/.claude/settings.local.json and ~/.claude/settings.json (in that order; a missing or malformed file or env
    is skipped). Never raises."""
# _hints gains, first, when d["git_bash"] is not None:
#   needs_path: "Claude Code may not find Git Bash (it is at <derived>, outside Program Files): without it hooks run in
#                PowerShell and the hook command breaks. Run `python3 .claude/bin/agentic.py doctor --fix` (it writes
#                CLAUDE_CODE_GIT_BASH_PATH to .claude/settings.local.json) and restart Claude Code"
#   missing:    "Git Bash was not found: install Git for Windows, or set CLAUDE_CODE_GIT_BASH_PATH"
# and either of these counts as an explanation (no "/hooks" fallback hint with it).

# .claude/bin/doctor.py  (WP-02)
SETTINGS_LOCAL = ROOT / ".claude" / "settings.local.json"  # module level, so tests can point it at a temporary file
def git_bash_finding(state):
    """The "git-bash" finding for a git_bash_state() result, or None (None state, configured, or default)."""
def write_git_bash_path(settings_local, bash):
    """Sets env.CLAUDE_CODE_GIT_BASH_PATH = bash in the JSON file settings_local (a Path), creating the file or the
    "env" object when missing and keeping every other key. A file that is not a JSON object is left alone and
    raises ValueError."""
def diagnose(git_bash=git_bash_state): ...   # appends git_bash_finding(git_bash()) last, when not None
def repair(findings, git_bash=git_bash_state): ...
#   "git-bash" is handled inside repair, not in REPAIRS (whose entries take no argument): it calls git_bash(), and
#   when its "derived" is a path, write_git_bash_path(SETTINGS_LOCAL, derived). A None derived, an OSError or a
#   ValueError leaves the file alone and the code out of "fixed"; no traceback reaches the user (the finding stays in
#   the re-diagnosis). The other codes keep using REPAIRS as today.
def report(fix=False, git_bash=git_bash_state): ...  # passes git_bash to repair and to both diagnoses
# `git_bash` is a callable returning a git_bash_state() result: tests pass one that reads their temporary
# SETTINGS_LOCAL, so after --fix the re-diagnosis sees the path configured and the finding is gone.

# .claude/bin/core.py  (WP-03)
CHILD_ENV_DROPPED = ("CLAUDE_CODE_SIMPLE",)  # documented to stop the saved login from being read
# child_env(cfg, **extra): as today, and every name in CHILD_ENV_DROPPED is removed, whatever cfg["auth"] is.

# .claude/bin/launch.py  (WP-03)
def _auth_status(argv, cfg):
    """(returncode, parsed JSON object) of `<cli> auth status --json` with child_env(cfg); (None, None) when it cannot
    run or times out; the object is None when stdout is not a JSON object."""
# require_cli: logged out = a JSON object AND (returncode == 1 or authMethod == "none" or loggedIn is False) -> die(1).
#   The message names the binary, `auth login`, '"auth": "inherit"', and the inherited variables: the names in
#   child_env(cfg) that start with CLAUDE_ or ANTHROPIC_, sorted, at most 10 then "and N more". No values.
#   It never says Claude Desktop's sign-in is not shared.
#   No JSON object -> the warning, and it goes on. Anything else -> logged in.
# The missing-CLI message keeps its first sentences and ends with exactly: "Claude Desktop bundles its own CLI but
#   does not put it on the PATH: point AGENTIC_CLAUDE at it." (no claim about its sign-in).

# .claude/bin/testutil.py  (WP-03): FAKE_AUTH="out" prints {"authMethod": "none"} and exits 1; "in" (default) prints
#   {"loggedIn": true, "authMethod": "fake"}, exit 0; "none" as today.
```

## 7. Conventions
- **Python 3.9.** No `X | None` or `list[...]` in runtime annotations; types go in docstrings, as `.claude/bin` does. This overrides the Python rules' "type annotations on every public signature" for this repository.
- **The ratchet:** functions of 60 lines or fewer (100 in tests), nesting of 4 or fewer, lines of 120 characters or fewer, files of 800 lines or fewer.
- **Windows paths** are built with `ntpath`, so the logic runs and is tested on Linux. Tests inject `is_windows=True` with fake `which` and `exists` instead of patching the OS.
- **Messages** name the file, the command or the variable to change. Never print a variable's value.
- **Never raise** where a file, the environment or git is read: `OSError`, `ValueError`, `subprocess.SubprocessError`, and `AttributeError` or `TypeError` on a JSON object of the wrong shape.
- **No personal paths in tests.** Use fake Windows paths such as `%LOCALAPPDATA%\Programs\Git`.

## 8. Work packages and acceptance criteria
### Acceptance criteria
- AC-001 · A failed live check carries the diagnosis
  - Scenario: a temporary project (`Repo`) with the flow's settings and no heartbeat. `PATH` holds a fake `python3` and git; `HOME` and `USERPROFILE` point to a temporary folder.
  - Action: `hooks-check` with `CLAUDECODE=1`.
  - Expected:
    - exit 3;
    - `diagnosis` has the keys of the first version plus `git_bash`: `null` when `compat.IS_WINDOWS` is false; on Windows (the CI's `windows-latest` runner) a dict with the five keys of section 5;
    - stderr still says "did not run for this call" and lists hints as `- ` lines.
  - Must not: a `diagnosis` in a passing or static check, or a traceback.
  - Check: `test_acceptance_v216.py::DiagnosisTests`
  - WP: WP-01
- AC-002 · A heartbeat under the main checkout of a worktree is found
  - Scenario, action and expected: as in the first version (a real `git worktree`, a fresh heartbeat in the main checkout, `hooks-check` run inside the worktree).
  - Must not: `ok: true`.
  - Check: `DiagnosisTests`
  - WP: WP-01
- AC-003 · python3, settings and the "/hooks" fallback in the hints
  - Scenario, action and expected: as in the first version (no `python3`, a `WindowsApps` `python3`, `disableAllHooks`, a settings file of the wrong shape; with no cause, the only hint is "/hooks").
  - Must not: the "/hooks" hint beside another one.
  - Check: `DiagnosisTests`
  - WP: WP-01
- AC-004 · Git Bash state on Windows
  - Scenario: `git_bash_state(is_windows=True, environ=…, settings_envs=…, which=…, exists=…)` with fakes, in five cases:
    1. `which("git")` = `%LOCALAPPDATA%\Programs\Git\cmd\git.exe`, that Git's `bin\bash.exe` exists, nothing configured, no default;
    2. the same, with `environ={"CLAUDE_CODE_GIT_BASH_PATH": "D:\\Git\\bin\\bash.exe"}`;
    3. the same, with `settings_envs=[{}, {"CLAUDE_CODE_GIT_BASH_PATH": "D:\\x.exe"}]`;
    4. `C:\Program Files\Git\bin\bash.exe` exists;
    5. no git on PATH and nothing exists.
  - Expected:
    1. `needs_path` true, `derived` = `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`;
    2. `configured` = `D:\Git\bin\bash.exe`, `needs_path` false;
    3. `configured` = `D:\x.exe`;
    4. `default` set, `needs_path` false and `missing` false;
    5. `missing` true.

    With `is_windows=False` the result is `None`. A `git.exe` under `<root>\mingw64\bin\` gives `<root>\bin\bash.exe`.
  - Must not: raise on a settings env that is not an object.
  - Check: `GitBashTests`
  - WP: WP-01
- AC-005 · The diagnosis puts Git Bash first
  - Scenario: `guardrail._hints(d)` with `d = {"python3": "C:\\Python312\\python.exe", "settings": [{"path": "s", "exists": True, "declares_hook": True, "disable_all_hooks": False}], "heartbeats": [{"path": "h", "exists": False, "age_s": None}], "git_bash": <state>}`, with the state of case 1 of AC-004, then of case 5.
  - Expected:
    - case 1: the first hint contains "Git Bash", the derived path and "doctor --fix", and no "/hooks" hint follows;
    - case 5: a hint contains "Git Bash was not found".
  - Must not: a Git Bash hint when `d["git_bash"]` is None.
  - Check: `GitBashTests`
  - WP: WP-01
- AC-006 · doctor reports and fixes Git Bash
  - Scenario:
    - `doctor.git_bash_finding(state)` for the states of AC-004 cases 1, 2, 4 and 5, and for None;
    - `doctor.write_git_bash_path(path, bash)` on four files: a missing file, a `settings.local.json` that holds `{"permissions": {"allow": ["Bash(x)"]}}`, one whose `env` holds another key, and a file that is a JSON list.
  - Expected:
    - findings: case 1 is `auto` with the derived path in its message and "settings.local.json" in its fix; cases 2 and 4 give None; case 5 is a `mention`; None gives None;
    - writes: the file ends with `env.CLAUDE_CODE_GIT_BASH_PATH` set and every other key kept, and the list file raises `ValueError` and is unchanged;
    - `agentic.py doctor` in a temporary `Repo` has no `git-bash` finding when `compat.IS_WINDOWS` is false (on Windows CI, where Git is under Program Files, `default` is set and there is no finding either: assert that only when `git_bash_state()["default"]` is set, else skip).
    - `report(fix=True, git_bash=…)` with `SETTINGS_LOCAL` pointing at a file that is a JSON list returns without raising, `fixed` empty and the finding still listed.
  - Must not: `write_git_bash_path` dropping `permissions` or another `env` key.
  - Check: `DoctorGitBashTests`
  - WP: WP-02
- AC-007 · The agents lose CLAUDE_CODE_SIMPLE and nothing else
  - Scenario: an environment with `CLAUDE_CODE_SIMPLE=1`, `CLAUDE_CODE_SESSION_ID=s`, `ANTHROPIC_BASE_URL=u` and `HTTPS_PROXY=p`.
  - Action: `core.child_env({"auth": "subscription"})` and `core.child_env({"auth": "inherit"})`.
  - Expected: neither result has `CLAUDE_CODE_SIMPLE`; both keep `CLAUDE_CODE_SESSION_ID`, `ANTHROPIC_BASE_URL` and `HTTPS_PROXY`.
  - Must not: any other variable removed, apart from the API keys under `subscription`, as today.
  - Check: `CliTests`
  - WP: WP-03
- AC-008 · The CLI check before the fallback
  - Scenario, action and expected: as in the first version.
    - A missing CLI: `run-wave 1`, `run-pipeline` and `run-wave 1 WP-01 --fix` each exit 1 before any state.
    - `FAKE_AUTH=out`, which now prints `{"authMethod": "none"}` and exits 1: exit 1, one `auth.log` line, no agent.
    - `FAKE_AUTH=none`: one warning, and the agents run.
    - One auth call per run, with the API key stripped.
  - Also: the logged-out stderr lists `ANTHROPIC_AAA_FAKE_INHERITED` when the test sets that variable (its name sorts before every other `ANTHROPIC_*` and `CLAUDE_*`, so the cap of 10 never hides it, whatever the host sets), and never contains its value. It does not contain "not signed in" or "not shared".
  - Must not: a value printed, or an agent started when logged out.
  - Check: `CliTests`
  - WP: WP-03
- AC-009 · The docs say how to fix Git Bash and point the fallback at a CLI
  - Scenario: the checkout.
  - Action: read the files.
  - Expected:
    - `.claude/commands/implement.md` names `doctor --fix`, `CLAUDE_CODE_GIT_BASH_PATH`, `AGENTIC_CLAUDE` and `diagnosis`, and its fallback section says the inherited `CLAUDE_*`/`ANTHROPIC_*` variables are listed when a CLI reports no login;
    - `docs/how-to/README.md` names `CLAUDE_CODE_GIT_BASH_PATH` and `AGENTIC_CLAUDE`, and has 260 lines or fewer;
    - `docs/how-it-works.md` names `git_bash` or "Git Bash", `diagnosis` and `auth status`.
  - Must not: any of those files saying Claude Desktop's sign-in is not shared ("not shared", "not signed in").
  - Check: `DocsTests`
  - WP: WP-04
- AC-010 · Release 2.16.0
  - Scenario: the checkout.
  - Action: read `plugin.json`, `upgrade.NOTES` and the test files.
  - Expected:
    - version `2.16.0`;
    - `NOTES["2.16.0"]` has at least three entries: one with `hooks-check`, one with `doctor --fix` and `CLAUDE_CODE_GIT_BASH_PATH`, and one with `auth status` and `CLAUDE_CODE_SIMPLE`;
    - the only acceptance file is `test_acceptance_v216.py`;
    - `test_runner_reports.py` holds v215's nine classes.
  - Must not: two acceptance files of releases at once.
  - Check: `ReleaseTests`
  - WP: WP-04

- AC-011 · The dead-hook message names Git Bash
  - Scenario: `guardrail.HOOKS_DEAD_MSG`.
  - Action: read it.
  - Expected: it contains "Git Bash", "doctor --fix", "python3" and "worktree", and still "did not run for this call" and `/implement fallback`.
  - Must not: lose any of the causes it named before.
  - Check: `DiagnosisTests`
  - WP: WP-01

### Work packages

#### WP-01 · Git Bash in the hook diagnosis
- Wave 1.
- Files: `.claude/bin/guardrail.py`, `.claude/bin/test_guardrail.py`.
- Implements: `DEFAULT_GIT_BASH`, `git_bash_state`, the `git_bash` key of `hook_diagnosis`, the two hints of section 6, and "Git Bash not found" in `HOOKS_DEAD_MSG`. The rest of the diagnosis stays as built.
- ACs: AC-001, AC-002, AC-003, AC-004, AC-005, AC-011.
- **Patterns to mirror:**
  - `guardrail.py:349-442`: the helpers' style;
  - `guardrail.py:417-431`: the hint order;
  - `test_guardrail.py:350-384`: the diagnosis unit tests.
- **Gotchas:**
  - Use `ntpath.dirname`, `ntpath.basename` and `ntpath.join`. The `git.exe` path from `which` has backslashes even in the fakes.
  - Compare folder names case-insensitively (`Cmd`, `BIN`).
  - Settings `env` values that are not non-empty strings are ignored.
  - Split `_settings_entries()` (`guardrail.py:367-375`) into `_settings_data()` returning `[(path, parsed or None), ...]` for the three files, used by both `_settings_entries()` and the default `settings_envs` of `git_bash_state` (each parsed object's `env` when it is a dict).
  - `guardrail.py` is at 485 lines; stay under 800.
- **Imports:** `ntpath`, `os`, `shutil`; `compat.IS_WINDOWS`.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_guardrail.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-02 · doctor finds and writes the Git Bash path
- Wave 2, after WP-01: it imports `git_bash_state`, and `doctor.py` would not import without it.
- Files: `.claude/bin/doctor.py`, `.claude/bin/test_doctor.py`.
- Implements: `SETTINGS_LOCAL`, `git_bash_finding`, `write_git_bash_path`, the `git-bash` finding appended last in `diagnose()`, and its repair inside `repair()` (section 6).
- ACs: AC-006.
- **Patterns to mirror:**
  - `doctor.py:22-28`: the finding builders;
  - `doctor.py:75-104`: the order in `diagnose`;
  - `doctor.py:106-130`: repairs;
  - `installer.py:127-141`: merging into `settings.local.json`;
  - `test_doctor.py:37-60`.
- **Gotchas:**
  - The repair calls `git_bash()` to get the derived path; the finding's text is not parsed. Tests patch `doctor.SETTINGS_LOCAL` to a temporary file and pass `git_bash`: they never touch the real checkout's settings.
  - `report()` re-diagnoses after repairing, and the env written goes into a settings file that `git_bash_state` reads, so after `--fix` the finding is gone. A test should show that with injected inputs.
  - `.claude/settings.local.json` may hold permissions written by `sync-permissions`: keep them.
- **Imports:** `from guardrail import git_bash_state`.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_doctor.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-03 · The agents' environment and the login check
- Wave 1.
- Files: `.claude/bin/core.py`, `.claude/bin/launch.py`, `.claude/bin/testutil.py`, `.claude/bin/test_launcher.py`.
- Implements: `CHILD_ENV_DROPPED` and its use in `child_env`; `_auth_status` returning `(returncode, data)`; the logged-out rule and message of section 6; the fake's new `out` answer.
- ACs: AC-007, AC-008.
- **Patterns to mirror:**
  - `core.py:321-326`;
  - `launch.py:49-92`;
  - `testutil.py:51-70`;
  - `test_launcher.py` `RequireCliTests` and `CliBeforeStateTests`.
- **Gotchas:**
  - `child_env` is used for every agent: change only the drop list.
  - The message's variable names come from `child_env(cfg)`, after the drop.
  - In this cloud environment dozens of `CLAUDE_*` names are set: the cap of 10 keeps the message short.
  - Keep the memo, the warning text and the state-free order (before snapshot, ledger and briefs).
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_launcher.py"`, `... -p "test_agentic.py"`, `... -p "test_fix_cycles.py"`, `python3 .claude/bin/agentic.py quality`.

#### WP-04 · Docs and release notes
- Wave 1.
- Files: `.claude/commands/implement.md`, `docs/how-to/README.md`, `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/bin/test_runner_reports.py`.
- ACs: AC-009, AC-010.
- **Patterns to mirror:**
  - `.claude/commands/implement.md:13-20` and `.claude/commands/implement.md:74-80`;
  - `docs/how-to/README.md:20-30`;
  - `upgrade.py:156-170`.
- **Gotchas:**
  - The first version's text claims Claude Desktop's sign-in is not shared. Remove it everywhere: `implement.md`, the hub's line 25, the notes.
  - The hub is at 260 lines: edit in place.
  - In `implement.md` step 1, say that on Windows a failed `hooks-check` usually means Git Bash, and that `doctor --fix` fixes it.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_runner_reports.py"`, `python3 .claude/bin/agentic.py docs-check`, `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v216.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v216.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/guardrail.py", ".claude/bin/test_guardrail.py"],
     "acs": ["AC-001", "AC-002", "AC-003", "AC-004", "AC-005", "AC-011"], "mirror": [".claude/bin/guardrail.py:349-442", ".claude/bin/test_guardrail.py:350-384"]},
    {"id": "WP-02", "wave": 2, "depends_on": ["WP-01"], "files": [".claude/bin/doctor.py", ".claude/bin/test_doctor.py"],
     "acs": ["AC-006"], "mirror": [".claude/bin/doctor.py:22-130", ".claude/bin/installer.py:127-141", ".claude/bin/test_doctor.py:37-60"]},
    {"id": "WP-03", "wave": 1, "depends_on": [], "files": [".claude/bin/core.py", ".claude/bin/launch.py", ".claude/bin/testutil.py", ".claude/bin/test_launcher.py"],
     "acs": ["AC-007", "AC-008"], "mirror": [".claude/bin/core.py:321-326", ".claude/bin/launch.py:49-92", ".claude/bin/testutil.py:51-70"]},
    {"id": "WP-04", "wave": 1, "depends_on": [], "files": [".claude/commands/implement.md", "docs/how-to/README.md", "docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/bin/test_runner_reports.py"],
     "acs": ["AC-009", "AC-010"], "mirror": [".claude/commands/implement.md:13-20", "docs/how-to/README.md:20-30", ".claude/bin/upgrade.py:156-170"]}
  ]
}
```

## 9. Test strategy
- **Unit:** each WP in its own test file, with stdlib `unittest`. Windows logic runs with `is_windows=True` and fake `which` and `exists`. doctor's write runs on temporary files.
- **Acceptance:** `.claude/bin/test_acceptance_v216.py`, rewritten from AC-001 to AC-011 and red before the code.
  - It keeps the first version's `DiagnosisTests` setup: `PATH` with a fake `python3` and git, and a temporary `HOME` and `USERPROFILE`.
  - It adds `GitBashTests` and `DoctorGitBashTests` (in-process, injected inputs) and rewrites `CliTests` and `DocsTests`.
  - Nothing is spent.
- **QA, by hand:**
  - all CI suites, including `acceptance/` and `qa/`;
  - mutations, at least:
    - the Git Bash hint dropped;
    - mingw64 not handled;
    - configured in settings ignored;
    - the write dropping keys;
    - `CLAUDE_CODE_SIMPLE` kept;
    - another variable dropped;
    - exit code 1 ignored;
    - a value printed;
  - the installed-project run as CI's `installed` job;
  - a real `auth status` through `require_cli` here.

Windows CI (`windows-latest`) runs the default branch for real: Git is under Program Files there, so `default` is set, with no Git Bash hint and no finding. The per-user case (`needs_path`) is only exercised with injected inputs. The next session on the field machine should run `doctor`, then `doctor --fix`, restart, and run `hooks-check`.

## 10. Decisions
| Decision | Discarded | Why |
|---|---|---|
| `doctor --fix` writes `CLAUDE_CODE_GIT_BASH_PATH` into `.claude/settings.local.json` (user's choice) | Exec-form hook commands; diagnosis only | It is the documented route, it is per machine and never committed, it keeps today's hook commands, and a fallback CLI reads it too. Exec form changes every project, and its minimum Claude Code version is unknown. |
| Detection: the variable (environment or settings), the two Program Files defaults, the `bash.exe` beside the `git.exe` on PATH | Copy Claude Code's own search | That search is not documented; these three cover the field case and the standard install. |
| Drop only `CLAUDE_CODE_SIMPLE` from the agents' environment (user's choice) | Strip every `CLAUDE_*`/`ANTHROPIC_*`; touch nothing | It is the only inherited variable documented to stop the saved login. A full strip breaks environments whose authentication travels in variables, such as this cloud container. |
| Logged out = JSON with exit 1, `authMethod: "none"` or `loggedIn: false` | `loggedIn` only | The docs specify the exit code and `authMethod`, not `loggedIn`. |
| The logged-out message lists inherited variable names (at most 10) | Print them all, or print values | Names point at the cause; values may be secrets. |
| No auto-detection of Claude Desktop's CLI | Search `%APPDATA%\Claude\claude-code\` | The user wants the native workflow; `AGENTIC_CLAUDE` covers the rest. |
| The first version's code is kept and corrected | Start again | `hook_diagnosis`, `require_cli` and the docs were verified (13+1 mutations); only their claims and two rules change. |

## 11. Risks and open questions
- **The per-user Git case is not tested on a real Windows machine.** Windows CI covers only the default install. The detection and the written setting follow the docs and the field report, but whether Claude Code picks up `env.CLAUDE_CODE_GIT_BASH_PATH` from `settings.local.json` without a restart is not documented. The hint says to restart.
- **Claude Code's own Git Bash search is not documented.** If it finds Git Bash some way this design does not check, doctor may suggest a path that is not needed. The written setting is harmless when it points at a real `bash.exe`.
- **`CLAUDE_CODE_SIMPLE` may not be the field report's only culprit.** If a CLI still reports no login, the message lists the inherited names so the next step can be found.
- **The logged-out JSON was not seen here.** This environment injects its credentials. The rule follows the documented exit code and `authMethod`.
- **Archive and index by hand.** The maintainer replaces `docs/architecture/0023-hook-diagnosis-cli-check.md` with this version and updates its line in `docs/architecture/README.md` when the design is approved; no WP owns them. The root `README.md` needs no change.
- **`verify` does not run `acceptance/`, `qa/`, `quality` or `docs-check`** (as in earlier designs, and its labels do not match the suites); QA runs them by hand.
- **Expected failures until WP-04 and the last commit.** `flow-history --check` fails until the PR's last commit. `test_layout.py` passes already: the old acceptance file is gone.
