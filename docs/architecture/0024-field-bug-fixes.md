# Architecture: field bug fixes — annexes, references, stale copies, network and a second session (agentic-flow 2.17.0)
Type: fix · Size: standard

## 1. Goal
Windows field runs and the first update of a GitLab project found five defects. The flow drops plan annexes from the agents' briefs (issue 122). `validate` refuses true `read` references to dotfiles and files without an extension, and splits a 4b cell on an escaped pipe (issue 123). `doctor` reports forever a "new version kept beside your edits" that install later made obsolete. The fallback launches every agent against an API it cannot reach when a terminal lacks the proxy variables (issue 125). A run can be broken by another Claude Code session working in the same folder (issue 124).

This design fixes the five. Every criterion is a test that fails on today's code. The release is 2.17.0, because `sessions-check` and the network check are new behaviour.

## 2. Scope
### Included
- **Briefs keep annexes (122).** Every `## ` heading that is not a numbered section (`## Annex A · Catalogue`, `## Anexo`) starts an annex. Every brief, the test-author's and each package's, keeps every annex. `/architect` documents the form.
- **`validate` references (123):**
  - a `read` row's reference may name a dotfile (`.gitignore:1-8`);
  - it may name a file without an extension (`Makefile:1`) when that file exists;
  - `\|` outside backticks is part of a cell, not a separator.
- **Stale kept copies:**
  - `install` deletes `.claude/state/upgrade/<path>` whenever it does not keep `<path>`, that is when the file is new, updated or unchanged;
  - `doctor` splits the kept copies into live ones (the installed file is still edited) and stale ones;
  - stale copies are a new `upgrade-stale` `auto` finding, and `doctor --fix` deletes them;
  - `upgrade-pending` counts only live copies.
- **Network pre-flight for the fallback (125):**
  - when `auth status` reports `apiProvider: "firstParty"`, `require_cli` sends one request to the API host through the agents' environment and proxy variables, before any agent;
  - DNS, connect or timeout failures and a proxy's 407 stop the run with exit 1, naming the host, the reason and the names of the proxy variables that are set, never their values;
  - other providers (Bedrock, Vertex) and an answer without `apiProvider` are not checked.
- **A second session refuses `/implement` (124):**
  - the hook records the `session_id` of every main-thread call (no `agent_type`, no `AGENTIC_WP`) in the heartbeat, with its time, keeping only the last 10 minutes;
  - a new `agentic.py sessions-check`, run inside a Claude tool call, exits 3 when another session called the hook in this root within 10 minutes;
  - `/implement` runs it in its pre-flight. On 3 it shows the other sessions and asks the user whether they are closed (a restart of Claude Code or `/clear` leaves the previous session's calls behind, under another id). If the user says so, it runs `sessions-check --ignore <id>` for each one, which forgets those ids and passes; otherwise it stops and recommends a git worktree.
- **Release 2.17.0:**
  - `test_acceptance_v217.py`;
  - the unique checks of `test_acceptance_v216.py` moved to `test_hook_diagnosis.py` and the old file deleted;
  - upgrade notes, `plugin.json`, the docs.

### Excluded (non-goals)
- **Issue 118** (auto mode blocking an implementer's tests): not reproduced.
- **No lock and no worktree automation for 124.** The check refuses and recommends; it does not create worktrees. A session that has made no tool call in the last 10 minutes is not seen.
- **The native workflow and the engines do not call `sessions-check`.** Only the `/implement` launcher does, before the workflow starts. The workflow's gatekeeper is a subagent whose `session_id` is not verified.
- **No network check in the native workflow.** Its agents are subagents of a session that already works.
- **No change to how `install` classifies files** (new, updated, unchanged, kept), only the cleanup of kept copies.

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
.claude/bin/brief.py                     WP-01  annex sections
.claude/bin/test_brief.py                WP-01
.claude/bin/manifest_check.py            WP-02  references and cells of section 4b
.claude/bin/test_manifest_check.py       WP-02
.claude/bin/installer.py                 WP-03  deletes kept copies it no longer needs
.claude/bin/doctor.py                    WP-03  upgrade-stale finding and repair
.claude/bin/test_install.py              WP-03
.claude/bin/test_doctor.py               WP-03
.claude/bin/launch.py                    WP-04  network pre-flight
.claude/bin/testutil.py                  WP-04  FAKE_PROVIDER in the fake auth status
.claude/bin/test_launcher.py             WP-04
.claude/bin/core.py                      WP-05  SESSION_WINDOW_S
.claude/bin/guardrail.py                 WP-05  sessions in the heartbeat, sessions_check()
.claude/bin/agentic.py                   WP-05  the sessions-check command
.claude/bin/test_guardrail.py            WP-05
.claude/bin/test_definitions.py          WP-05  the command count and the docstring
.claude/commands/implement.md            WP-06
.claude/commands/architect.md            WP-06
docs/how-to/README.md                    WP-06
docs/how-it-works.md                     WP-06
.claude-plugin/plugin.json               WP-06  2.17.0
.claude/bin/upgrade.py                   WP-06  NOTES["2.17.0"]
.claude/bin/test_hook_diagnosis.py       WP-06  moved from test_acceptance_v216.py (new)
.claude/bin/test_acceptance_v216.py      WP-06  deleted
.claude/flow-history.json                WP-06  regenerated as the last commit
.claude/bin/test_acceptance_v217.py      AT     (new)
```

## 4b. Existing code context
| What an implementer needs to know | Where it is (`file:lines`) | Pattern or rule | Source |
|---|---|---|---|
| `split()` cuts a plan at `## N. ` only (`SECTION_RE`); any other `## ` line stays inside the previous section, and fenced lines never start one | `.claude/bin/brief.py:10-28` | Add a third kind, `("annex", heading, lines)`, for an unfenced `## ` line that does not match `SECTION_RE`; keep `pre` and `section` as they are | read |
| `slice_architecture` keeps `pre` and the sections in `WP_SECTIONS`/`AT_SECTIONS`, reduces section 8, drops the rest; an annex after section 8, 10 or (for the test-author) 11 is lost today | `.claude/bin/brief.py:80-104` | Keep every `annex` part in every brief, in document order | read |
| `manifest_check` imports `split` for section 4b; it only looks at `kind == "section"`, so a new kind does not disturb it | `.claude/bin/manifest_check.py:17`, `.claude/bin/manifest_check.py:420-433` | No change needed there | read |
| Brief tests build a small plan text (`TEXT`) and a manifest, and call `slice_architecture` | `.claude/bin/test_brief.py:36-60` | Same style: in-memory text, assertIn/assertNotIn | read |
| `REF_TOKEN_RE` needs a character before an extension's dot, so a dotfile reference (.gitignore, lines 1 to 8) and an extensionless one (Makefile, line 1) are not references; `table_cells` splits on every `|` outside backticks, including `\|`; `reference_ok` checks existence and range | `.claude/bin/manifest_check.py:393-430` | A token is a candidate when it matches `path:start[-end]` and its path holds a `/` or a `.` or names an existing file; `localhost:8080` stays ignored | read |
| Provenance tests call `table_cells` and `provenance_problems` on texts built in the test | `.claude/bin/test_manifest_check.py:125-153` | Same style; references are relative to the project root, which is this repo in tests | read |
| `install_write` writes a kept file's new version to `.claude/state/upgrade/<rel>` and never deletes an old one; `unchanged` files are not written at all | `.claude/bin/installer.py:212-230` | After the loop, for every `rel` whose kind is not `kept`, delete `target/.claude/state/upgrade/<rel>` if it exists (not in a dry run) | read |
| The install record maps each shipped path to the hash it recorded; for a kept file it keeps the previous hash, which differs from the edited file's | `.claude/bin/installer.py:212-226` | A kept copy is stale when the installed file is missing, the path is not in the record, or the installed file's hash equals the recorded one | read |
| `compat.content_hash(path)` is the hash install uses (CRLF-insensitive); the record is `{"version", "files": {rel: hash}}` | `.claude/bin/installer.py:226`, `.claude/bin/installer.py:244-245` | Use it in doctor too, never `hashlib` directly | read |
| doctor: findings in a fixed order in `diagnose()`, `upgrade-pending` counted from every file under `UPGRADE_DIR`, repairs keyed by code in `REPAIRS`, `report()` re-diagnoses after repairing | `.claude/bin/doctor.py:20`, `.claude/bin/doctor.py:104-136`, `.claude/bin/doctor.py:138-179` | `diagnose()` never writes; a new `auto` code needs a `REPAIRS` entry | read |
| doctor tests: a temporary `Repo` with an install record, run `doctor`, parse the last JSON line; one test pins `upgrade-pending` for a copy the record does not know | `.claude/bin/test_doctor.py:39-60`, `.claude/bin/test_doctor.py:222-227` | Same style; that test changes (WP-03) | read |
| `InstalledCopyTests` installs into a temporary target from a temporary source and runs the target's own `agentic.py` | `.claude/bin/test_install.py:292-332` | Same fixture for the kept-copy tests | read |
| `require_cli`: once per process, the binary, then `auth status` with the agents' environment; logged out stops with `die`, an unreadable status warns | `.claude/bin/launch.py:49-110` | Add the network step after the login check, inside the same once-per-process memo; reuse `child_env(cfg)` for the environment | read |
| This container's proxy re-signs TLS with its own CA (`/root/.ccr/ca-bundle.crt`); Node gets it, Python's default context may not | not a file: environment | A certificate error counts as reachable | inferred |
| The real `auth status --json` prints `apiProvider: "firstParty"` (seen in this container with Claude Code 2.1.329), and answers in 0.26 s with a dead proxy: it does not reach the network | not a file: command output | The check keys on `apiProvider`, and must make its own request | inferred |
| The fake `claude` answers `auth status` without `apiProvider`, so existing tests never trigger a network request | `.claude/bin/testutil.py:55-66` | Add `FAKE_PROVIDER`: when set, the logged-in answer carries `"apiProvider": <value>` | read |
| Launcher unit tests patch `os.environ` and `launch.subprocess.run`, and clear `_CLI_CHECKED` | `.claude/bin/test_launcher.py:357-381` | Same style; inject the opener instead of touching the network | read |
| `child_env` copies `os.environ`, drops `CLAUDE_CODE_SIMPLE` and, under `subscription`, the API keys; proxy variables pass through | `.claude/bin/core.py:322-329` | Read proxy variables from `child_env(cfg)`, never from `os.environ` directly | read |
| The heartbeat file and its constants | `.claude/bin/core.py:32-34` | Add `SESSION_WINDOW_S = 600` beside them | read |
| `locked_json(path, fn)` reads, calls `fn`, writes what `fn` returns; a corrupt file is set aside | `.claude/bin/core.py:353-372` | The hook's update stays one `locked_json` call | read |
| `record_hook_seen` rewrites the heartbeat on every hook call with `ts`, `tool`, `command`, `agent_type`, `guarded_ts`; `is_flow_agent` decides flow-agent calls | `.claude/bin/guardrail.py:314-333` | Add `session_id` (of this call, any caller) and `sessions` (`{id: ts}`, main-thread calls only, pruned to `SESSION_WINDOW_S`) | read |
| `hooks_check` live mode reads the heartbeat with `locked_json(HOOK_SEEN, lambda s: None)`, prints one JSON line, returns 0 or 3; outside a Claude call (`CLAUDECODE` unset) it checks the settings | `.claude/bin/guardrail.py:499-525` | `sessions_check` follows the same shape: one JSON line on stdout, the explanation on stderr, 0 or 3 | read |
| `hook()` calls `record_hook_seen(data)` with the raw payload | `.claude/bin/guardrail.py:527-541` | The payload's `session_id` is a documented common hook input field; that subagent calls carry the parent's is not verified, which is why only main-thread calls are recorded | inferred |
| The command table is pinned: count 36 and one docstring line per command | `.claude/bin/test_definitions.py:504-507` | WP-05 updates it to 37 and adds `sessions-check` to the docstring | read |
| Command table and a simple handler | `.claude/bin/agentic.py:113-114`, `.claude/bin/agentic.py:368-377` | `"sessions-check": cmd_sessions_check`, returning the function's code | read |
| Hook-check tests: `RepoCase` with `put_seen`, `hook(payload)`, `check(live)` | `.claude/bin/test_guardrail.py:44-67`, `.claude/bin/test_guardrail.py:95-101` | Same helpers for `sessions-check` | read |
| `/implement` pre-flight steps | `.claude/commands/implement.md:15-22` | Insert the sessions check as step 2, renumber the rest | read |
| `/architect`'s document skeleton, inside a fence, ends at section 11 | `.claude/commands/architect.md:119-190` | Add one sentence after the skeleton on annexes | read |
| The how-to hub is capped at 260 lines and is at 260 | `docs/how-to/README.md:181` | Edit in place: the `hooks-check` line of the command list also names `sessions-check` | read |
| The previous release's acceptance file (test_acceptance_v216.py, its ReleaseTests at lines 417-431 before this change deletes it) and how 2.16.0 moved 2.15.0's classes | `.claude/bin/test_runner_reports.py:1-27` | Move every class but `ReleaseTests`; the docs class gets `FLOW_REPO_ONLY` | read |
| Upgrade notes, newest first | `.claude/bin/upgrade.py:156-168` | Add `"2.17.0"` above `"2.16.1"` | read |
| At most one `test_acceptance*.py` in `.claude/bin` | `.claude/bin/test_layout.py:1-22` | Delete `test_acceptance_v216.py` in the same change | read |

What must **not** change:
- the classification in `install_plan`;
- `hooks-check`'s output and exit codes;
- `require_cli`'s login messages;
- the engines;
- a brief's content for a plan without annexes (byte for byte).

## 5. Data model
The heartbeat, `.claude/state/hook-seen.json`, gains two keys:
```python
{
  "ts": 1763650000.0, "tool": "Bash", "command": "...", "agent_type": None, "guarded_ts": None,  # as today
  "session_id": "abc123...",          # the session of this (latest) call, whoever made it; absent if the payload had none
  "sessions": {"abc123...": 1763650000.0, "def456...": 1763649800.0},
  # main-thread calls only (no agent_type, AGENTIC_WP unset), entries older than SESSION_WINDOW_S dropped on each write
}
```
`sessions-check` JSON line:
```python
{"ok": True, "mode": "live", "session": "abc12345", "others": []}
{"ok": False, "mode": "live", "session": "abc12345", "others": [{"session": "def45678", "age_s": 200}],
 "reason": "another Claude Code session used this folder within the last 10 minutes"}
{"ok": True, "mode": "not checked", "reason": "outside a Claude Code tool call" | "the hook recorded no session id"}
```
Session ids are shown cut to 8 characters.

## 6. Contracts between modules
```python
# brief.py
def split(text):
    """[(kind, key, lines)]: ("pre", None, lines) first; ("section", "4b", lines) for '## N. ' headings;
    ("annex", "<heading text without '## '>", lines) for any other unfenced '## ' heading. Concatenating every
    part's lines gives back the text."""

def slice_architecture(text, ident, manifest):  # unchanged signature; every "annex" part is kept, in order

# manifest_check.py
REF_TOKEN_RE  # matches "path:start" or "path:start-end", path = one or more of [\w./-]
def reference_candidate(token):
    """True when token is path:start[-end] and its path holds "/" or "." or names an existing file under ROOT."""
def table_cells(line):  # unchanged signature; "\|" outside backticks is kept in the cell as "\|"

# installer.py: install_write(target, prep, dry_run) also deletes target/.claude/state/upgrade/<rel>
# for every rel whose plan kind is "new", "updated" or "unchanged" (never in a dry run). No new public name.

# doctor.py
def kept_copies():
    """(stale, live): sorted relative paths (posix, relative to UPGRADE_DIR) of the files under UPGRADE_DIR.
    Stale: ROOT/<rel> missing, <rel> not in record["files"], or content_hash(ROOT/<rel>) == record["files"][<rel>].
    Without a readable record every copy is live."""
def remove_stale_copies():  # deletes the stale ones; REPAIRS["upgrade-stale"]
# findings: {"code": "upgrade-stale", "severity": "auto",
#            "message": "N kept version(s) in .claude/state/upgrade/ are obsolete: the installed file is no longer edited",
#            "fix": "delete them"}  placed just before "upgrade-pending", which now counts only live copies.

# launch.py
NETWORK_TIMEOUT_S = 10
DEFAULT_API_URL = "https://api.anthropic.com"
PROXY_VARS = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy",
              "NO_PROXY", "no_proxy")
def _api_url(env):        # env.get("ANTHROPIC_BASE_URL") or DEFAULT_API_URL
def _reachable(url, env, opener=None):
    """A HEAD request to url within NETWORK_TIMEOUT_S, through the proxies named in env. Result by outcome:
      - any HTTP answer (HTTPError included) other than 407   -> (True, "")
      - HTTPError 407                                          -> (False, "proxy asks for credentials (407)")
      - URLError/OSError whose text holds "Tunnel connection failed: 407" (an https URL through HTTPS_PROXY)
                                                               -> (False, "proxy asks for credentials (407)")
      - ssl.SSLError or ssl.CertificateError (also as a URLError's reason): a TLS peer answered; Python may lack the
        proxy's CA that the Node CLI gets from NODE_EXTRA_CA_CERTS   -> (True, "")
      - socket.gaierror (also as a URLError's reason)          -> (False, "name not resolved")
      - ConnectionRefusedError                                 -> (False, "connection refused")
      - socket.timeout / TimeoutError                          -> (False, "timed out")
      - any other URLError, OSError or http.client.HTTPException -> (False, "connection failed")
    A URLError's reason is unwrapped first and classified by the rows above (a real closed port raises
    URLError(ConnectionRefusedError)). reason never holds a URL or a credential. The opener is called as
    opener(request, timeout=NETWORK_TIMEOUT_S); it defaults to build_opener(ProxyHandler(proxies)).open with
    proxies from env: https from https_proxy/HTTPS_PROXY, http from http_proxy/HTTP_PROXY, each falling back to
    all_proxy/ALL_PROXY when unset (ProxyHandler has no "all" key)."""
def _proxy_names(env):    # "HTTPS_PROXY, NO_PROXY" (names set in env, in PROXY_VARS order) or "none"
# require_cli(cfg): after the login check, when status.get("apiProvider") == "firstParty":
#   ok, reason = _reachable(_api_url(env), env); if not ok: die(message)
#   message names: the host of the URL (never the full URL), the reason, the word "proxy", _proxy_names(env), and
#   "ANTHROPIC_BASE_URL" when that variable is set in env; it never contains a proxy variable's value.

# core.py
SESSION_WINDOW_S = 600  # sessions-check: another session's hook call newer than this blocks /implement

# guardrail.py
def record_hook_seen(data):  # unchanged signature; also writes "session_id" and "sessions" (section 5)
def sessions_check():
    """Inside a Claude tool call (CLAUDECODE): the own session is CLAUDE_CODE_SESSION_ID when set, else the
    heartbeat's "session_id". 3 when "sessions" holds another id with a time within SESSION_WINDOW_S of now, else 0.
    Outside a call, or with no own session id: 0, mode "not checked". Prints one JSON line (section 5); on 3 the
    explanation goes to stderr."""
def sessions_check(ignore=()):
    """As above; ignore holds 8-character id prefixes the user confirmed closed. Matching entries are removed from
    "sessions" in the heartbeat (one locked_json write) and do not count. Inside a call only."""

# agentic.py: "sessions-check [--ignore ID]..." -> cmd_sessions_check(args) -> sessions_check(ignore)
#   any other argument, or --ignore without an ID: die("Uso: sessions-check [--ignore ID]...")
```
Exit codes: `sessions-check` 0 or 3. `require_cli`'s network failure exits 1, through `die`.

## 7. Conventions
- **Python 3.9.** No `X | None` or `list[...]` in runtime annotations; types go in docstrings, as `.claude/bin` does. This overrides the Python rules' annotation rule for this repository.
- **The ratchet:** functions of 60 lines or fewer (100 in tests), nesting of 4 or fewer, lines of 120 characters or fewer, files of 800 lines or fewer.
- **Never print a variable's value**, above all a proxy URL, which may carry credentials. Name variables only.
- **Never raise** where a file, the environment, git or the network is read: catch `OSError`, `ValueError`, `urllib.error.URLError`, `http.client.HTTPException` and `socket.timeout`, and turn them into a result.
- **Tests never reach the real network.** Network tests use an injected opener, or a local `http.server` on `127.0.0.1`, or a closed local port, and remove every `PROXY_VARS` name from the environment they pass (`test_agentic.Repo` copies `os.environ`, `test_agentic.py:54`).
- **No personal paths in tests or docs.**
- **Messages** name the command, file or variable to change.

## 8. Work packages and acceptance criteria
### Acceptance criteria
- AC-001 · An annex reaches every brief
  - Scenario: a plan with sections 1-11 and two annexes: `## Annex A · Catalogue` after section 10, holding `ANNEX-A-ROW`, and `## Anexo B` after section 8, holding `ANNEX-B-ROW`; a fenced block in section 6 holds the line `## Annex Z`.
  - Action: `brief.slice_architecture(text, "WP-01", manifest)` and `brief.slice_architecture(text, "AT", manifest)`.
  - Expected: both briefs are sliced (second value `True`) and contain `ANNEX-A-ROW` and `ANNEX-B-ROW`. The WP brief still lacks section 10's text. `split(text)` has exactly two `annex` parts, keyed `Annex A · Catalogue` and `Anexo B`, and `"".join` of every part's lines equals the text.
  - Must not: drop an annex; take the fenced `## Annex Z` for a heading; change a brief of a plan without annexes.
  - Check: `test_acceptance_v217.py`, `AnnexTests`.
  - WP: WP-01
- AC-002 · References to dotfiles and files without an extension
  - Scenario: this repository (it has `.gitignore` and `.claude/bin/agentic.py`); section 4b texts built in the test.
  - Action: `manifest_check.provenance_problems(text)`.
  - Expected:
    - a `read` row citing `` `.gitignore:1-2` `` has no error;
    - `` `.gitignore:1-99999` `` gives `section 4b, row 1: .gitignore:1-99999 does not exist or is out of range`;
    - a row citing only `` `localhost:8080` `` gives `section 4b, row 1: read needs a file:line`;
    - `reference_candidate("Makefile:1")` is `False` here, where no `Makefile` exists, and `True` when the test writes a file without an extension at the root (in a temporary `ROOT`).
  - Must not: accept a missing dotfile; treat `localhost:8080` as a file reference.
  - Check: `test_acceptance_v217.py`, `ReferenceTests`.
  - WP: WP-02
- AC-003 · An escaped pipe stays in its cell
  - Scenario: the row ``| a \| b | `x` | read |``.
  - Action: `manifest_check.table_cells(row)`.
  - Expected: `["a \\| b", "`x`", "read"]` (three cells). The existing ``| a | `x | y` | read |`` still gives three cells.
  - Must not: split on `\|`.
  - Check: `test_acceptance_v217.py`, `ReferenceTests`.
  - WP: WP-02
- AC-004 · Install deletes kept copies it does not need
  - Scenario: an installed target (as in `InstalledCopyTests`) in which:
    - `.claude/state/upgrade/.claude/agents/qa.md` exists while `.claude/agents/qa.md` is intact;
    - `.claude/agents/reviewer.md` is edited and committed.
  - Action: run `install` again from the source.
  - Expected:
    - the qa copy is gone;
    - `.claude/state/upgrade/.claude/agents/reviewer.md` exists and holds the source's version;
    - `install --dry-run` deletes nothing.
  - Must not: delete the kept copy of an edited file; delete anything in a dry run.
  - Check: `test_acceptance_v217.py`, `KeptCopyTests`.
  - WP: WP-03
- AC-005 · doctor tells stale kept copies from live ones and fixes them
  - Scenario: an installed target whose `.claude/state/upgrade/` holds:
    - a copy of an intact file, `qa.md` (stale);
    - a copy of an edited file, `reviewer.md` (live);
    - a copy of a path the record does not know (stale).
  - Action: `agentic.py doctor`, then `agentic.py doctor --fix`.
  - Expected:
    - `doctor`: one `upgrade-stale` finding (`auto`), whose message starts with `2 kept version(s)`, and an `upgrade-pending` finding whose message starts with `1 new version(s)`;
    - `doctor --fix`: `"fixed": ["upgrade-stale"]`, the two stale files are gone and the live one remains;
    - the second report has no `upgrade-stale`.
  - Must not: delete the live copy; write anything in `doctor` without `--fix`.
  - Check: `test_acceptance_v217.py`, `KeptCopyTests`.
  - WP: WP-03
- AC-006 · The fallback stops when the API cannot be reached
  - Scenario: a project with the fake `claude`, every name of `PROXY_VARS` removed from the environment first (the host's own proxy must not take part), then `FAKE_PROVIDER=firstParty`, `ANTHROPIC_BASE_URL=http://127.0.0.1:<a port just closed>` and `HTTPS_PROXY=http://user:s3cret@127.0.0.1:<closed port>`.
  - Action: `agentic.py run-acceptance`.
  - Expected:
    - exit code 1;
    - stderr names `127.0.0.1`, the word `proxy` and the variable names `HTTPS_PROXY` and `ANTHROPIC_BASE_URL`;
    - the fake's log has `auth.log` and no agent call (`call-*.json`);
    - nothing is created under `.claude/state/runs/`.
  - Must not: print `s3cret` or the proxy URL; launch an agent.
  - Check: `test_acceptance_v217.py`, `NetworkTests`.
  - WP: WP-04
- AC-007 · The network check passes on any answer and is skipped off the first-party API
  - Scenario: a local `http.server` on `127.0.0.1` that answers 404 to everything.
  - Action and expected, in-process with `launch._reachable` and `launch.require_cli` (subprocess and opener patched):
    - `_reachable("http://127.0.0.1:<port>", {})` is `(True, "")`;
    - an opener raising a `URLError` whose reason is a `socket.gaierror` gives `(False, "name not resolved")`;
    - an `HTTPError` 407, and a `URLError(OSError("Tunnel connection failed: 407 Proxy Authentication Required"))`, both give `(False, "proxy asks for credentials (407)")`;
    - a `URLError` whose reason is an `ssl.SSLError` (certificate verify failed) gives `(True, "")`;
    - `ConnectionRefusedError`, `socket.timeout` and a plain `OSError("x")` give `connection refused`, `timed out` and `connection failed`;
    - `require_cli` with `apiProvider` `"bedrock"` or absent never calls `launch._reachable` (the tests patch `launch._reachable`, the only seam, since `require_cli` passes no opener);
    - `_reachable` with an opener raising `URLError(ConnectionRefusedError())` gives `connection refused`.
  - Must not: treat a 401, 403 or 404 as unreachable; stop on a certificate error; check under Bedrock or Vertex.
  - Check: `test_acceptance_v217.py`, `NetworkTests`.
  - WP: WP-04
- AC-008 · The hook records main-thread sessions only
  - Scenario: a temporary repo with the flow's hook.
  - Action: `agentic.py hook` with these payloads:
    - `{"session_id": "s-main", "tool_name": "Bash", "tool_input": {"command": "ls"}}`;
    - one with `"agent_type": "implementer"` and `"session_id": "s-agent"`;
    - one with `AGENTIC_WP=WP-01` and `"session_id": "s-wp"`;
    - one without `session_id`.
  - Expected:
    - `hook-seen.json`'s `sessions` holds `s-main` only;
    - its `session_id` is that of the last payload that carried one;
    - an entry older than 600 s, written there beforehand, is gone after the next main-thread call.
  - Must not: record agent sessions; fail or block when `session_id` is missing.
  - Check: `test_acceptance_v217.py`, `SessionTests`.
  - WP: WP-05
- AC-009 · sessions-check refuses when another session is active
  - Scenario: `hook-seen.json` with `session_id` `"me-000000"` and `sessions` `{"me-000000": now, "other-11111": now - 120}`; `CLAUDE_CODE_SESSION_ID` removed from the environment unless a case sets it.
  - Action: `agentic.py sessions-check` with `CLAUDECODE=1`.
  - Expected:
    - exit 3, JSON `ok` false and `others` `[{"session": "other-11", "age_s": 120±5}]`;
    - stderr says `git worktree`;
    - with `other-11111` at `now - 700` the exit is 0 and `others` is `[]`;
    - with `CLAUDE_CODE_SESSION_ID=other-11111` the own session is `other-11111`, so `me-000000` (age 0) is the other one and the exit is 3;
    - without `CLAUDECODE`, or with neither `CLAUDE_CODE_SESSION_ID` nor `session_id`, the exit is 0 with mode `"not checked"`.
  - Must not: count the own session; refuse outside a Claude call.
  - Check: `test_acceptance_v217.py`, `SessionTests`.
  - WP: WP-05
- AC-012 · A closed session can be let through
  - Scenario: as AC-009, with `other-11111` at `now - 120`, `CLAUDE_CODE_SESSION_ID` removed and `CLAUDECODE=1`.
  - Action: `agentic.py sessions-check --ignore other-11`, then `agentic.py sessions-check`.
  - Expected:
    - the first exits 0 with `others` `[]`;
    - `hook-seen.json`'s `sessions` no longer holds `other-11111`;
    - the second exits 0;
    - `sessions-check --ignore` (no ID) and `sessions-check --bogus` exit 1 with `Uso: sessions-check`.
  - Must not: forget a session whose prefix was not given; pass without the user's ids.
  - Check: `test_acceptance_v217.py`, `SessionTests`.
  - WP: WP-05
- AC-010 · The docs say how
  - Scenario: the repository.
  - Action: read the files.
  - Expected:
    - `.claude/commands/implement.md` runs `agentic.py sessions-check` in its pre-flight; on exit 3 it asks the user whether the listed sessions are closed, reruns with `--ignore` if so, and otherwise stops and recommends a git worktree;
    - `.claude/commands/architect.md` says that an unnumbered `## ` heading is an annex every brief keeps;
    - `docs/how-to/README.md` names `sessions-check` and is at most 260 lines;
    - `docs/how-it-works.md` names `sessions-check` and the network check.
  - Must not: exceed the hub's line cap.
  - Check: `test_acceptance_v217.py`, `DocsTests`.
  - WP: WP-06
- AC-011 · Release 2.17.0
  - Scenario: the repository.
  - Action: read `plugin.json`, `upgrade.NOTES` and `.claude/bin`.
  - Expected:
    - version `2.17.0`;
    - `NOTES["2.17.0"]` has at least 4 entries, naming `annex`, `sessions-check`, `upgrade-stale` and `proxy`;
    - the only acceptance file is `test_acceptance_v217.py`;
    - `test_hook_diagnosis.py` defines `DiagnosisTests`, `GitBashTests`, `DoctorGitBashTests`, `CliTests` and `DocsTests`.
  - Must not: keep `test_acceptance_v216.py`.
  - Check: `test_acceptance_v217.py`, `ReleaseTests`.
  - WP: WP-06

### Work packages
#### WP-01 · Briefs keep annexes
- Wave 1.
- Files: `.claude/bin/brief.py`, `.claude/bin/test_brief.py`.
- Contracts: implements `split` and `slice_architecture` (section 6).
- ACs: AC-001.
- **Patterns to mirror:** `brief.py:10-28` (the fence toggle and the parts list) and `test_brief.py:36-60`.
- **Gotchas:**
  - A `## ` heading inside section 8 currently ends up inside a subsection. Splitting it out as an annex must not break `section_eight`, which receives only section 8's own lines.
  - `### ` and `#### ` are not annexes.
  - The preamble's `# Architecture:` line is `# `, not `## `.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_brief.py"`, `python3 -m unittest discover -s .claude/bin -p "test_manifest_check.py"`.

#### WP-02 · validate references and cells
- Wave 1.
- Files: `.claude/bin/manifest_check.py`, `.claude/bin/test_manifest_check.py`.
- Contracts: implements `REF_TOKEN_RE`, `reference_candidate` and `table_cells`.
- ACs: AC-002, AC-003.
- **Patterns to mirror:** `manifest_check.py:393-430` and `test_manifest_check.py:125-153`.
- **Gotchas:**
  - `row_problem` filters tokens through the regex today. Use `reference_candidate` instead.
  - The existence test for a path without `/` or `.` uses `ROOT`, which tests can patch (`mock.patch.object(manifest_check, "ROOT", tmp)`).
  - `\|` inside backticks stays as it is too.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_manifest_check.py"`.

#### WP-03 · Stale kept copies
- Wave 1.
- Files: `.claude/bin/installer.py`, `.claude/bin/doctor.py`, `.claude/bin/test_install.py`, `.claude/bin/test_doctor.py`.
- Contracts: the `install_write` cleanup; `kept_copies`, `remove_stale_copies` and the `upgrade-stale` finding.
- ACs: AC-004, AC-005.
- **Patterns to mirror:** `installer.py:212-230`, `doctor.py:104-179`, `test_install.py:292-332` and `test_doctor.py:39-60`.
- **Gotchas:**
  - `install_write` is shared by dry runs: no deletion when `dry_run`.
  - Leave empty folders under `.claude/state/upgrade/`. `doctor` counts files only.
  - The record's path is `ROOT / INSTALL_RECORD`.
  - In the flow repo itself (`is_flow_repo`), `doctor` skips the record check; `kept_copies` may still run.
  - `test_doctor.py:222-227` expects a copy `a.md` with an empty record to give only `upgrade-pending` and `ok` true. Under this design that copy is stale (not in the record): update the test so it expects `upgrade-stale`, `ok` false and exit code 3 (it asserts 0 today), and add a live copy for the `upgrade-pending` case.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_install.py"`, `python3 -m unittest discover -s .claude/bin -p "test_doctor.py"`.

#### WP-04 · Network pre-flight
- Wave 1.
- Files: `.claude/bin/launch.py`, `.claude/bin/testutil.py`, `.claude/bin/test_launcher.py`.
- Contracts: `NETWORK_TIMEOUT_S`, `DEFAULT_API_URL`, `PROXY_VARS`, `_api_url`, `_reachable`, `_proxy_names`, and the `require_cli` step.
- ACs: AC-006, AC-007.
- **Patterns to mirror:** `launch.py:49-110`, `testutil.py:55-66` and `test_launcher.py:357-381`.
- **Gotchas:**
  - Build the opener with `urllib.request.build_opener(urllib.request.ProxyHandler(proxies))`.
  - `proxies` comes from the env's `https_proxy`/`HTTPS_PROXY`, `http_proxy`/`HTTP_PROXY` and `all_proxy`/`ALL_PROXY` (lower case wins, as urllib does).
  - When `urllib.request.proxy_bypass_environment(host, {"no": <NO_PROXY>})` says bypass, use `ProxyHandler({})`.
  - Never use the process's own `os.environ` for this; use `child_env(cfg)`.
  - `HTTPError` is a subclass of `URLError`: catch it first.
  - The `die` message must not contain the URL of a proxy. `ANTHROPIC_BASE_URL` may be named as a variable but its value is shown only as its host.
  - Keep `require_cli` under 60 lines: put the step in its own function.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_launcher.py"`.

#### WP-05 · A second session refuses /implement
- Wave 1.
- Files: `.claude/bin/core.py`, `.claude/bin/guardrail.py`, `.claude/bin/agentic.py`, `.claude/bin/test_guardrail.py`, `.claude/bin/test_definitions.py`.
- Contracts: `SESSION_WINDOW_S`, `record_hook_seen`, `sessions_check` and `cmd_sessions_check`.
- ACs: AC-008, AC-009, AC-012.
- **Patterns to mirror:** `guardrail.py:314-333`, `guardrail.py:499-525`, `agentic.py:113-114`, `agentic.py:368-377` and `test_guardrail.py:44-67`.
- **Gotchas:**
  - The hook must never fail because of this. A missing or non-string `session_id` records nothing, and a `sessions` value that is not a dict starts again from `{}`.
  - Main thread means no `agent_type` in the payload and `AGENTIC_WP` unset.
  - `sessions_check` reads with `locked_json(HOOK_SEEN, lambda s: None)` only when the file exists, as `hooks_check` does.
  - `test_definitions.py:504-507` pins the command table: every command must have a line in the `Subcommands:` docstring of `agentic.py` (add `  sessions-check` there), and the count goes from 36 to 37.
  - `test_agentic.Repo` (`test_agentic.py:56`) strips `AGENTIC_WP` and `CLAUDECODE` but not `CLAUDE_CODE_SESSION_ID`: every test that runs `sessions-check` must remove it (or set it) itself, since the suite may run inside a real session.
  - The own session is `CLAUDE_CODE_SESSION_ID` from the environment when it is set (Claude Code sets it in a tool call's shell; seen here), else the heartbeat's `session_id`. The environment is preferred because another session's hook call can overwrite the heartbeat between this call and the check.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_guardrail.py"`, `python3 -m unittest discover -s .claude/bin -p "test_definitions.py"`.

#### WP-06 · Docs, notes, release and the moved tests
- Wave 2 (the docs name what WP-04 and WP-05 build).
- Depends on: WP-01, WP-04, WP-05.
- Files: `.claude/commands/implement.md`, `.claude/commands/architect.md`, `docs/how-to/README.md`, `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/bin/test_hook_diagnosis.py`, `.claude/bin/test_acceptance_v216.py`, `.claude/flow-history.json` (regenerated with `agentic.py flow-history` as the PR's last commit).
- ACs: AC-010, AC-011.
- **Patterns to mirror:** `implement.md:15-22`, `architect.md:119-190`, `upgrade.py:156-168` and `test_runner_reports.py:1-27`.
- **Gotchas:**
  - The hub is at 260 lines: edit the `hooks-check` line at 181 in place, so the line count does not grow.
  - The moved file keeps the classes as they are, with a docstring saying where they came from. Its `DocsTests` reads this repo's docs: decorate it with `FLOW_REPO_ONLY` (`unittest.skipUnless(core.is_flow_repo(ROOT), ...)`), as `test_runner_reports.py:27` does.
  - The guides may not cite flow version numbers (`acceptance/test_docs.py`).
  - `implement.md:13` says `fallback` means "use the fallback mode without checking anything". Rewrite that line: `fallback` skips the workflow's availability check, while the pre-flight, `sessions-check` included, runs in both modes, because a second session breaks a fallback run the same way.
  - `test_definitions.py:596-601` requires `hooks-check` to stay step 1: insert `sessions-check` as step 2 and do not reorder.
- **Validation:** `python3 -m unittest discover -s .claude/bin -p "test_hook_diagnosis.py"`, `python3 .claude/bin/agentic.py docs-check`, `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v217.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v217.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/brief.py", ".claude/bin/test_brief.py"],
     "acs": ["AC-001"], "mirror": [".claude/bin/brief.py:10-28", ".claude/bin/test_brief.py:36-60"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/manifest_check.py", ".claude/bin/test_manifest_check.py"],
     "acs": ["AC-002", "AC-003"], "mirror": [".claude/bin/manifest_check.py:393-430", ".claude/bin/test_manifest_check.py:125-153"]},
    {"id": "WP-03", "wave": 1, "depends_on": [], "files": [".claude/bin/installer.py", ".claude/bin/doctor.py", ".claude/bin/test_install.py", ".claude/bin/test_doctor.py"],
     "acs": ["AC-004", "AC-005"], "mirror": [".claude/bin/installer.py:212-230", ".claude/bin/doctor.py:104-179", ".claude/bin/test_install.py:292-332", ".claude/bin/test_doctor.py:39-60"]},
    {"id": "WP-04", "wave": 1, "depends_on": [], "files": [".claude/bin/launch.py", ".claude/bin/testutil.py", ".claude/bin/test_launcher.py"],
     "acs": ["AC-006", "AC-007"], "mirror": [".claude/bin/launch.py:49-110", ".claude/bin/testutil.py:55-66", ".claude/bin/test_launcher.py:357-381"]},
    {"id": "WP-05", "wave": 1, "depends_on": [], "files": [".claude/bin/core.py", ".claude/bin/guardrail.py", ".claude/bin/agentic.py", ".claude/bin/test_guardrail.py", ".claude/bin/test_definitions.py"],
     "acs": ["AC-008", "AC-009", "AC-012"], "mirror": [".claude/bin/guardrail.py:314-333", ".claude/bin/guardrail.py:499-525", ".claude/bin/agentic.py:368-377", ".claude/bin/test_guardrail.py:44-67"]},
    {"id": "WP-06", "wave": 2, "depends_on": ["WP-01", "WP-04", "WP-05"], "files": [".claude/commands/implement.md", ".claude/commands/architect.md", "docs/how-to/README.md", "docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/bin/test_hook_diagnosis.py", ".claude/bin/test_acceptance_v216.py", ".claude/flow-history.json"],
     "acs": ["AC-010", "AC-011"], "mirror": [".claude/commands/implement.md:15-22", ".claude/commands/architect.md:119-190", ".claude/bin/upgrade.py:156-168", ".claude/bin/test_runner_reports.py:1-27"]}
  ]
}
```

## 9. Test strategy
- **Unit:** each WP adds tests to its own test file, with stdlib `unittest`.
  - Network tests inject the opener or use a local `http.server` on `127.0.0.1`.
  - Hook tests run `agentic.py hook` in a temporary `Repo`.
- **Acceptance:** `.claude/bin/test_acceptance_v217.py`, written from AC-001 to AC-011 before the code. It must be red today for each AC: annexes dropped, `.gitignore:1-2` refused, `\|` split, copies kept, no network check, no `sessions`, no `sessions-check`, docs and release missing. Nothing is spent, and nothing reaches the network.
- **QA, by hand:**
  - every CI suite, `quality`, `docs-check`;
  - the installed-project run, as CI's `installed` job;
  - mutations, at least:
    - annexes kept only in the WP brief;
    - a fenced `## ` taken as an annex;
    - `reference_candidate` without the existence check;
    - `\|` split;
    - the dry run deleting;
    - stale and live swapped;
    - a 404 treated as unreachable;
    - the check run with `apiProvider` absent;
    - agent sessions recorded;
    - the own session counted;
    - the window ignored;
  - a real `auth status` through `require_cli` here, reaching the API through this container's proxy.

## 10. Decisions
| Decision | Discarded | Why |
|---|---|---|
| Every unnumbered `## ` heading is an annex kept in every brief | Only annexes a criterion names | A name match is fragile (a catalogue cited as "the table below"); annexes are rare and short compared with the sections a brief already holds. |
| Extensionless references count only when the file exists | Any `word:number` | `localhost:8080`, `step:3` and the like would turn into false "does not exist" errors. |
| Delete kept copies in `install`, and let `doctor --fix` clean old ones | Only `doctor` | The root cause is in `install`; projects that already hold stale copies need the repair. |
| Network check keyed on `apiProvider: "firstParty"` | An environment switch to turn it off in tests | The real CLI reports the provider (seen here); the fake does not, so no existing test reaches the network, and Bedrock or Vertex hosts are never guessed. |
| Any HTTP answer but 407 means reachable | Require 2xx | The API answers 404 to a bare HEAD; reaching it is what matters. A 407 means the agents would fail at the proxy too. |
| Stop with exit 1 on an unreachable API (user's choice) | Warn and go on | Every agent would fail one by one, as in the field report. |
| `sessions-check` refuses at 10 minutes (user's choice), only from the `/implement` launcher | A lock file; `git worktree list`; a check inside the engines | The hook already sees every call with its `session_id`; a lock left by a crash would need cleanup; the workflow's gatekeeper is a subagent whose session id is not verified, so a check inside the run could refuse its own session. |
| Only main-thread calls are recorded | Every call | Fallback agents are separate `claude -p` sessions and would look like other sessions right after a run. |
| `test_acceptance_v216.py`'s classes move to `test_hook_diagnosis.py` | Delete them | They are the only end-to-end checks of the diagnosis and the login check. |

## 11. Risks and open questions
- **The session id of subagent calls is not verified.** This design does not depend on it: only main-thread calls are recorded, and `sessions-check` runs from the main thread. If the payload had no `session_id`, the check reports "not checked" and lets the run start.
- **A restart or `/clear` changes the session id** (the restart is documented in step 1 of `/implement`; `/clear` is not verified). The previous id looks like another session for up to 10 minutes: the launcher asks the user and lets it through with `--ignore` (AC-012).
- **A quiet second session is not seen.** A session that made no tool call in the last 10 minutes passes the check. The guard's git-state comparison during the run still stops a run that another session disturbs.
- **The proxy behaviour of urllib** (`ProxyHandler`, `proxy_bypass_environment`) is not exercised against a real corporate proxy. The tests cover a closed port, a local server and injected errors. The field case (no proxy variables in a new terminal) shows up as a DNS or connect failure, which the check reports.
- **`apiProvider` is undocumented output.** If a future CLI drops it, the check is skipped and the flow behaves as in 2.16.
- **`verify` does not run `acceptance/`, `qa/`, `quality` or `docs-check`**, as in earlier designs; QA runs them by hand.
- **Expected failures between wave 0 and WP-06.** Once `test_acceptance_v217.py` exists, `test_layout.py` (at most one acceptance file) and v216's `ReleaseTests` (line 426 pins the only acceptance file) fail until WP-06 deletes `test_acceptance_v216.py`. `verify` runs after wave 2, so this does not block.
- **Expected failures until the last commit.** `flow-history --check` fails until WP-06 regenerates `.claude/flow-history.json` as the PR's last commit.
- **The `verify` labels do not match their suites** (build = bench, lint = the node harness, types = bench/acceptance), as in earlier designs of this repo: the commands are right, the phase names in a report are not.
- **Archive and index by hand.** On approval, the maintainer copies this file to `docs/architecture/0024-field-bug-fixes.md` and adds its line to `docs/architecture/README.md`; no WP owns them.
