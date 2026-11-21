# Architecture: the native workflow records its token usage, and stops printing the rules Claude Code already injects (agentic-flow 2.20.0)
Type: feature · Size: standard

## 1. Goal

The native workflow is the engine in real use, and it is the one the flow knows least about: only the fallback engine records what each agent spends, so every cost figure so far comes from bench sessions on two small fixtures. This release reads Claude Code's own files after a workflow run and adds each agent's tokens to the saved result, so every real `/implement` becomes a measurement. It also stops printing, in the native workflow, the common rules that Claude Code already injects into every agent: in five real runs kept on disk, all 62 agents had received `.claude/rules/agentic/common.md` as project instructions and four agent types got it a second time in their prompt.

## 2. Scope

### Included

- **Usage of a native run.** A new module reads the workflow's run record and each agent's transcript, and builds `usage` in the fallback engine's format (tokens, turns, model; no dollars).
- **`save-result --run RUN_ID`.** The command `/implement` already runs after a workflow takes the run's id and adds `usage` to the result it saves. Without the option it does what it does today.
- **Clean degradation.** Claude Code's layout is internal: when the files are missing, unreadable or shaped differently, the result is saved without usage, the command exits 0 and says why in one line.
- **Rules in the native workflow.** When `pipeline-plan` runs inside a Claude Code session, the printed rules leave out the files Claude Code loads for every agent (those without a `paths` filter: `common.md`) and add one line saying where they are. The language rules are still printed.
- **`/implement`** passes the run id and presents the usage.
- **Release 2.20.0**: notes, docs, the budget, one acceptance file.

### Excluded (non-goals)

- Dollars. Prices change; tokens and the model are recorded, and a reader can price them.
- Usage while the workflow runs, or from inside the script: `agent()` returns only the report.
- The language rules in the native workflow. Claude Code injects a rule with a `paths` filter only into an agent that opens a matching file with the Read tool: in the run inspected, the implementer, the test-author, the test-auditor and QA received `python.md`, the reviewer did not. Not reliable for a judge, so they stay printed.
- Any change to the two engines' code. The plan carries the rules text; both engines use it as they do today.
- The fallback engine and the bench: `claude -p` agents keep the whole rules printed.
- Changing the agents' definitions.

## 3. Stack

Python 3.9+ (standard library only) and the Node.js the CI uses for `test_workflow.mjs`. No package manager, no new dependency.

- Unit and acceptance: `python3 -m unittest discover -s .claude/bin -p "test_*.py"`
- The workflow against the conformance scenarios: `node .claude/bin/test_workflow.mjs`
- Quality limits: `python3 .claude/bin/agentic.py quality`
- Bench: `python3 -m unittest discover -s bench -p "test_*.py"` and `python3 -m unittest discover -s bench/acceptance`

## 4. Repository structure

```
.claude/bin/workflow_usage.py        WP-01  new: the usage of a native run, from Claude Code's files
.claude/bin/agentic.py               WP-01  save-result [FILE] [--run RUN_ID]
.claude/bin/installer.py             WP-01  the new module is installed
.claude/bin/test_workflow_usage.py   WP-01  new
.claude/bin/repo_scan.py             WP-02  the rules a native plan prints
.claude/bin/launch.py                WP-02  pipeline_plan asks for them
.claude/bin/test_repo_scan.py        WP-02
.claude/commands/implement.md        WP-03  the run id, and how to present the usage
.claude/bin/test_definitions.py      WP-03
docs/how-it-works.md                 WP-04
.claude-plugin/plugin.json           WP-04  2.20.0
.claude/bin/upgrade.py               WP-04  NOTES["2.20.0"]
.claude/flow-budget.json             WP-04
.claude/bin/test_qa_recheck.py       WP-04  the classes moved from test_acceptance_v219.py
.claude/bin/test_acceptance_v219.py  WP-04  deleted
.claude/bin/test_acceptance_v220.py  AT
.claude/flow-history.json            by hand: regenerated as the last commit
```

## 4b. Existing code context

| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| `save-result`: reads `.agentic-result.json` (or stdin), refuses any other file, saves to `.claude/state/runs/workflow-result.json`, deletes the source only once saved, prints one line | `.claude/bin/agentic.py:243-260` | The handler to extend; every `die` message starts with `save-result:` | read |
| Usage errors are `die("Uso: …")`; a command's handler is `cmd_<name>(args)` in `COMMANDS` | `.claude/bin/agentic.py:120-135` | Design 0016 keeps the `Uso:` prefix | read |
| The fallback's usage format: `usage_summary(records)` returns `{"total": {input, cache_read, output, turns, cost_usd}, "by_agent": records}`; a record has `id`, `agent`, `label`, `input`, `cache_read`, `output`, `cost_usd`, `turns` | `.claude/bin/core.py:418-421` | Reuse `usage_summary`; `input` is new input plus cache creation, as the fallback counts it (`.claude/bin/launch.py:199-208`) | read |
| A module of `.claude/bin` reaches another with `sibling("name")`, loaded only when the command needs it | `.claude/bin/core.py:345-347` | `agentic.py` loads the new module that way, inside the handler, so the hook's fast path never imports it | read |
| What `install` copies: the names in `INSTALL_BIN` | `.claude/bin/installer.py:19-20` | Add `workflow_usage` | read |
| `/implement` writes the workflow's JSON to `.agentic-result.json` and runs `save-result .agentic-result.json` | `.claude/commands/implement.md:42-46` | The step that gains `--run` | read |
| How `/implement` presents a result, one bullet per part | `.claude/commands/implement.md:50-75` | Add a "Usage" bullet | read |
| The rule files of a project: `common` plus the stack's, those that are installed | `.claude/bin/repo_scan.py:58-63` | Unchanged | read |
| `render_rules(paths, root)` prints each file without its frontmatter under a header that starts "Rules you must follow (common and language). They are printed here, so do not read them from disk:" | `.claude/bin/repo_scan.py:65-76` | The function that gains the native case | read |
| `rules_text(manifest)` is `render_rules(rule_files(manifest), ROOT)`; the one-off commands print through it | `.claude/bin/repo_scan.py:78-79`, `.claude/bin/launch.py:302-307` | Stays the whole text: the one-off commands are the fallback | read |
| `pipeline_plan` puts `rules` (the paths), `rules_text` and `rules_sum` (a checksum of the text) in the plan | `.claude/bin/launch.py:661-675` | Only `rules_text` and its sum change, and only inside a Claude Code session | read |
| Both engines print `plan.rules_text` when its checksum holds, and fall back to naming the paths when it does not | `.claude/bin/pipeline.py:141-147`, `.claude/workflows/agentic-implement.js:544-550` | No change: the plan decides what is printed | read |
| "Inside a Claude Code tool call" is read from the `CLAUDECODE` environment variable | `.claude/bin/guardrail.py:564-566` | The same test tells a native plan from a fallback one | read |
| The fallback engine runs every step, `pipeline-plan` included, without `CLAUDECODE` | `.claude/bin/launch.py:613-620` | So a fallback plan always prints the whole rules, even when launched from a session | read |
| The tests' `Repo` runs commands without `CLAUDECODE` | `.claude/bin/test_agentic.py:54-57` | Existing tests keep seeing the whole rules; a native test passes `env={"CLAUDECODE": "1"}` | read |
| Tests that pin the printed rules' header and content | `.claude/bin/test_launcher.py:213-230`, `.claude/bin/test_repo_scan.py:50-65` | They run without `CLAUDECODE`: they stay green and are not edited | read |
| Tests of `save-result` | `.claude/bin/test_agentic.py:738-753`, `.claude/bin/test_review_fixes.py:130-139` | They call it without `--run`: they stay green | read |
| A test pins the number of commands at 37 | `.claude/bin/test_definitions.py:508-511` | No command is added | read |
| The guide's state tree says usage is recorded in fallback mode only, and its glossary says who receives the rules | `docs/how-it-works.md:360-364`, `docs/how-it-works.md:401` | Lines to bring up to date (WP-04) | read |
| `/implement`'s pre-flight says `rules-sync` leaves the rules "which the agents receive in their prompt" | `.claude/commands/implement.md:20-24` | Line to bring up to date (WP-03) | read |
| The bench isolates its sessions with `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` | `bench/bench.py:55-58` | The variable the flow also honours: with it nothing is injected | read |
| The acceptance file of the last release pins "the only acceptance file" | `.claude/bin/test_qa_recheck.py:1-8` (where that file's other classes end up; its `ReleaseTests` is dropped) | It fails from wave 0 until WP-04 moves the file: expected, not to be fixed in wave 1 | read |
| The release pattern | `.claude/bin/upgrade.py:156-170`, `.claude/bin/test_lean_hook.py:1-12` | Mirror for WP-04 | read |

What must not change: the engines, the conformance scenarios, the plan's other keys, what a fallback or bench run prints, `save-result` without `--run`, the agents' definitions.

## 5. Data model

Claude Code's files, as observed in version 2.1.316 (an internal layout, read defensively; see the annex for a sample):

```
<config>/projects/<project>/<session>/workflows/<runId>.json
    {"runId": "wf_…", "status": "completed", "workflowProgress": [
        {"type": "workflow_agent", "agentId": "a57c…", "agentType": "test-author", "label": "test-author",
         "model": "claude-sonnet-5-5", "durationMs": 91234, …}, {"type": "workflow_phase", …}, …]}
<config>/projects/<project>/<session>/subagents/workflows/<runId>/agent-<agentId>.jsonl
    one JSON object per line; an assistant line carries
    {"message": {"id": "msg_…", "usage": {"input_tokens": 3, "cache_creation_input_tokens": 1200,
                                          "cache_read_input_tokens": 45000, "output_tokens": 800}}}
```

`<config>` is the `CLAUDE_CONFIG_DIR` environment variable, or `~/.claude`. One API message is written on several lines (one per content block) with the same `message.id` and the same `usage`: it is counted once.

What the flow adds to the saved result:

```python
result["usage"] = {
    "total": {"input": int, "cache_read": int, "output": int, "turns": int, "cost_usd": None},
    "by_agent": [  # in the run record's order
        {"id": str, "agent": str, "label": str, "model": str | None,
         "input": int, "cache_read": int, "output": int, "turns": int, "cost_usd": None}],
    "source": "claude-code",
    "missing": int,  # agents of the record whose transcript could not be read
}
```

- `input` = `input_tokens` + `cache_creation_input_tokens`; `cache_read` = `cache_read_input_tokens`; `output` = `output_tokens`; `turns` = the number of distinct message ids with a usage.
- Odd shapes, one rule each: a `workflow_agent` entry whose `agentType` or `label` is not a string gets `""` for it; a usage line without a string `message.id` is skipped; a token value that is not an `int` (a `bool` is not one here) counts as 0.
- `id`: the package when the label starts with one (`WP-02 (fix)` gives `WP-02`); otherwise `AT` for `test-author`, `QA` for `qa`, `DOCS` for `doc-updater`, `gatekeeper` for `gatekeeper`, and `REVIEW` for any other type. The same idents the fallback uses.

## 6. Contracts between modules

**`workflow_usage.py`** (new; standard library, plus `core.usage_summary`):

```python
RUN_ID_RE = re.compile(r"wf_[A-Za-z0-9-]+")   # matched whole: nothing that could leave the folder
AGENT_ID_RE = re.compile(r"[A-Za-z0-9_-]+")   # matched whole: the record is not the flow's own file

def find_run(run_id, config_dir=None)   # -> Path or None
    """The run record <config>/projects/*/*/workflows/<run_id>.json, the newest if several; None when run_id does
    not match RUN_ID_RE or no such file exists. config_dir: CLAUDE_CONFIG_DIR, or ~/.claude."""

def usage_of_run(record)               # record: Path -> dict or None
    """The usage of section 5 for the run whose record this is. The run id is record.stem (find_run checked it),
    never the record's own "runId" field; the transcripts are record.parent.parent / "subagents" / "workflows" /
    record.stem / f"agent-{agentId}.jsonl". None when the record cannot be read, is not an object, or names no
    agent. An agent is left out and counted in "missing" when its agentId is not a string that matches
    AGENT_ID_RE whole, or its transcript is missing or unreadable; a line that is not JSON, or has no usage, is
    skipped. Never raises."""

def usage_for(run_id, config_dir=None)  # -> (dict or None, str)
    """(usage, reason). With a usage the reason is "". Without one it is, in order: "RUN_ID is not a workflow run
    id" (the id does not match), "no record of that run was found", or "the run's record could not be read" (also
    when it is not an object or names no agent)."""
```

**`agentic.py save-result [FILE] [--run RUN_ID]`:**

- Arguments: at most one file and at most one `--run RUN_ID`, in either order. Anything else: `die("Uso: save-result [FILE] [--run RUN_ID]")`. This is on purpose stricter than today, where an extra argument after the file is ignored.
- Everything it does today stays, in the same order.
- With `--run`, and when the result has no `usage` key of its own: `usage_for(RUN_ID)`. A usage is stored as `result["usage"]` before the file is written. The printed line ends with ` · usage: N agent(s)` (plus `, M without a transcript` when `missing` is not 0), or ` · usage: not recorded (REASON)`.
- A result that already has `usage` keeps it; the line ends with ` · usage: kept`.
- `--run` never changes the exit code: a result that can be saved is saved, with exit 0.

**The rules a plan prints** (`repo_scan.py`):

```python
POINTED_COMMON = ("\nThe common rules are already in your context, as project instructions ({paths}): follow them. "
                  "Read those files only if you cannot see them there.\n")

def always_loaded(path)               # -> bool
    """Whether Claude Code loads this rules file for every agent: it has no frontmatter, or its frontmatter has no
    `paths:` key. False when the file cannot be read."""

def injected_by_claude_code()         # -> bool
    """Whether this process runs inside a Claude Code session that loads project instructions: CLAUDECODE is set
    and CLAUDE_CODE_DISABLE_CLAUDE_MDS is not."""

def rules_text(manifest, native=False) # -> str
    """native=False: as today. native=True: the always-loaded files are not printed; POINTED_COMMON names them
    (their paths, joined with ", ") first, then render_rules of the rest. No rule files at all: ""."""
```

- The header `render_rules` prints over the rest ("Rules you must follow (common and language). They are printed here…") stays as it is, also when only language rules follow it.
- When the rest is empty, the text is `POINTED_COMMON` alone; when no file is always loaded, it is `render_rules` of all of them, as today.
- `launch.pipeline_plan` calls `rules_text(manifest, native=injected_by_claude_code())` and computes `rules_sum` from that text. `rules` stays the list of every file.
- Every other caller of `rules_text` keeps the default.

**`/implement`** runs `python3 .claude/bin/agentic.py save-result .agentic-result.json --run <runId>`, with the `runId` the Workflow tool returned when it launched the workflow, and presents `usage` when the saved result has it.

## 7. Conventions

- English everywhere; usage errors keep the `Uso:` prefix (design 0016).
- No type annotations in signatures, as in the rest of `.claude/bin`: the flow runs on Python 3.9, where `X | None` in a signature fails when the module is imported.
- A reader of somebody else's files never raises: it catches `OSError`, `ValueError` and wrong shapes where they occur, and returns what section 6 says.
- Nothing but token counts, turns, the label, the agent type and the model leaves a transcript: no prompt and no output text is copied into the result.
- No personal paths in tests or docs: the tests build a temporary config folder.
- The guides do not cite flow version numbers. Commit format `type: summary`; the flow history is regenerated as the last commit.

## 8. Work packages and acceptance criteria

### Acceptance criteria

- AC-001 · The usage of a run is read from Claude Code's files
  - Scenario: a temporary config folder with the run record and the two transcripts of the annex, under `projects/p/s/`.
  - Action: `workflow_usage.usage_for("wf_test-001", config_dir)`.
  - Expected: `by_agent` has two records, in the record's order: `{"id": "AT", "agent": "test-author", "label": "test-author", "model": "claude-sonnet-5-5", "input": 1203, "cache_read": 45000, "output": 800, "turns": 1, "cost_usd": None}` and `{"id": "WP-02", "agent": "implementer", "label": "WP-02 (fix)", "model": "claude-sonnet-5-5", "input": 510, "cache_read": 9000, "output": 150, "turns": 2, "cost_usd": None}`. `total` is `{"input": 1713, "cache_read": 54000, "output": 950, "turns": 3, "cost_usd": None}`. `source` is `"claude-code"`, `missing` is 0. The reason is `""`.
  - Must not: a message written on two lines counted twice; any text of a prompt or an answer in the result.
  - Check: `test_acceptance_v220.py`
  - WP: WP-01

- AC-002 · save-result adds the usage
  - Scenario: a temporary repo with `.agentic-result.json` holding `{"result": "OK"}`, and `CLAUDE_CONFIG_DIR` pointing at the folder of AC-001.
  - Action: `agentic.py save-result .agentic-result.json --run wf_test-001`; then the same file again with a result that already has `"usage": {"total": {}, "by_agent": []}`; then without `--run`.
  - Expected: first: exit 0, the saved result has the `usage` of AC-001, the source file is gone, the line ends with ` · usage: 2 agent(s)`. Second: the saved `usage` is the one the result had, the line ends with ` · usage: kept`. Third: the saved result has no `usage` key and the line is today's.
  - Must not: `save-result --run` (no id), or `--run a --run b`, do anything but exit 1 with `Uso: save-result [FILE] [--run RUN_ID]`.
  - Check: `test_acceptance_v220.py`
  - WP: WP-01

- AC-003 · Without the files, the result is still saved
  - Scenario: as AC-002, with each of: an id no record has (`wf_none-000`); an id that is not one (`../../x`); a record that is `[1]`; a record that is not JSON; the record of the annex with one transcript deleted; with one transcript holding a line that is not JSON among its valid lines; the record of the annex with the second agent's `agentId` changed to `../../../../outside`, a folder named `agent-..` created inside `subagents/workflows/wf_test-001/`, and a file `outside.jsonl` with a valid usage line (output 777) at `projects/p/s/subagents/outside.jsonl`, which is where `agent-../../../../outside.jsonl` resolves from that folder.
  - Action: `save-result .agentic-result.json --run <id>` each time.
  - Expected: exit 0 every time, the result saved, no `Traceback` on stderr. The first four end with ` · usage: not recorded (` and a reason; the fifth and the seventh with ` · usage: 1 agent(s), 1 without a transcript` and `missing` 1; the sixth with ` · usage: 2 agent(s)` and the totals of AC-001.
  - Must not: a file outside the run's transcript folder read: in the seventh case 777 appears nowhere in the result.
  - Check: `test_acceptance_v220.py`
  - WP: WP-01

- AC-004 · A native plan leaves the common rules to Claude Code
  - Scenario: a temporary repo with stack `python` and the rules installed (`rules-sync`): `common.md` without frontmatter, `python.md` with a `paths:` frontmatter.
  - Action: `agentic.py pipeline-plan` with `CLAUDECODE=1`; without it; and with `CLAUDECODE=1` and `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`.
  - Expected: with `CLAUDECODE=1`: `rules_text` starts with `\nThe common rules are already in your context, as project instructions (.claude/rules/agentic/common.md): follow them.`, contains `--- .claude/rules/agentic/python.md ---` and python's rules, and does not contain `--- .claude/rules/agentic/common.md ---` nor the sentence "No speculative abstractions"; `rules_sum` is the checksum of that text; `rules` lists both files. In the other two cases `rules_text` is exactly what it is today: it starts with the "They are printed here" header and contains both files.
  - Must not: `paths:` in any printed text. The test removes `CLAUDE_CODE_DISABLE_CLAUDE_MDS` from the environment of the first two cases itself: the suite may run where it is set.
  - Check: `test_acceptance_v220.py`
  - WP: WP-02

- AC-005 · The fallback keeps the whole rules, even from a session
  - Scenario: the repo of AC-004, with the fake `claude` of the tests.
  - Action: with `CLAUDECODE=1` in the environment: `agentic.py run-wave 1`; and `agentic.py run-pipeline` (the fallback engine, whose own `pipeline-plan` step runs without that variable).
  - Expected: in both, the implementer's first prompt contains "No speculative abstractions" and the "They are printed here" header.
  - Must not: the "already in your context" line in a fallback prompt.
  - Check: `test_acceptance_v220.py`
  - WP: WP-02

- AC-006 · /implement passes the run id and presents the usage
  - Scenario: `.claude/commands/implement.md`.
  - Action: read it.
  - Expected: it contains `save-result .agentic-result.json --run`, says the id is the `runId` the Workflow tool returned, and has a bullet that starts `- **Usage` and names `usage.by_agent`. Its pre-flight step about `rules-sync` no longer says the agents receive the rules "in their prompt" without more: it says the workflow leaves the common rules to Claude Code.
  - Must not: the old command line without `--run` as the step to run.
  - Check: `test_acceptance_v220.py`
  - WP: WP-03

- AC-007 · Docs and release 2.20.0
  - Scenario: this repository.
  - Action: read `plugin.json`, `upgrade.NOTES`, `docs/how-it-works.md`, the test files, the installer.
  - Expected: version `2.20.0`; `NOTES["2.20.0"]` has at least two notes that name "usage" and "rules"; `how-it-works.md` contains "save-result --run", its state-tree line for `usage.jsonl` still says "(fallback mode)" and a line next to it says where the workflow's usage is saved, and its glossary line "Stack and rules" contains "Claude Code"; `"workflow_usage" in installer.INSTALL_BIN.split()`; the only `test_acceptance*.py` is `test_acceptance_v220.py`; `test_qa_recheck.py` holds the classes `QaAfterAFixTests`, `RulesTests`, `EnginesTests` and `DefinitionTests`.
  - Must not: a version number of the flow in a guide.
  - Check: `test_acceptance_v220.py`
  - WP: WP-04

### Work packages

#### WP-01 · The usage of a native run
- Wave 1.
- Files: `.claude/bin/workflow_usage.py`, `.claude/bin/agentic.py`, `.claude/bin/installer.py`, `.claude/bin/test_workflow_usage.py`.
- Implements `workflow_usage` and `save-result --run` of section 6. Consumes `core.usage_summary` by implementation (it exists).
- ACs: AC-001, AC-002, AC-003.
- **Patterns to mirror:** `.claude/bin/agentic.py:243-260` (the handler, its messages, the order of its steps); `.claude/bin/reports.py:1-40` (a small module that reads somebody else's file defensively); `.claude/bin/core.py:418-421` (the summary); `.claude/bin/test_review_fixes.py:120-140` (how a test runs a command in a temporary repo and checks for no traceback).
- **Gotchas:**
  - The same API message is on several lines of a transcript: count each `message.id` once. A line without `message.usage` (a user turn, an attachment) is skipped.
  - `find_run` builds a glob from the id: match `RUN_ID_RE` whole first, so no id can name another folder.
  - The handler loads the module with `sibling("workflow_usage")` inside the `--run` branch only.
  - Every `open` and `read_text` names `encoding="utf-8"`: `test_quality.py`'s `EncodingTests` fails otherwise.
  - Update the help line of `save-result` in the module's docstring (`.claude/bin/agentic.py:25`) to `save-result [FILE] [--run RUN_ID]`.
  - `test_lean.py`'s budget check goes red as soon as lines or bytes are added, and stays red until WP-04 raises the budget: expected in wave 1.
  - `agentId` comes from a file the flow did not write: check it against `AGENT_ID_RE` before it goes into a path.
  - `test_acceptance_v219.py`'s `ReleaseTests` is red until wave 2 (4b): leave it.
  - The source file is still deleted only after the result is written.
  - A function may have at most 60 lines; `agentic.py` and its long-line count are under the quality ratchet.
- **Exact imports and APIs:** `from core import usage_summary, sibling`; `json`, `os`, `re`, `pathlib.Path`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_workflow_usage.py"`; `python3 -m unittest discover -s .claude/bin -p "test_agentic.py"`; `python3 .claude/bin/agentic.py quality`.

#### WP-02 · The rules a native plan prints
- Wave 1.
- Files: `.claude/bin/repo_scan.py`, `.claude/bin/launch.py`, `.claude/bin/test_repo_scan.py`.
- Implements `always_loaded`, `injected_by_claude_code`, `rules_text(manifest, native)` and the call in `pipeline_plan`.
- ACs: AC-004, AC-005.
- **Patterns to mirror:** `.claude/bin/repo_scan.py:65-79` (how a rules file's frontmatter is found and skipped); `.claude/bin/guardrail.py:564-566` (the `CLAUDECODE` test); `.claude/bin/test_launcher.py:213-230` (a test that installs the rules in a temporary repo and reads the plan).
- **Gotchas:**
  - Only `pipeline_plan` passes `native`; `render_prompt` (the one-off commands) must keep the default, or a fallback agent loses the rules.
  - `rules_sum` is computed from the text actually put in the plan, or both engines fall back to naming the paths.
  - The fallback engine already removes `CLAUDECODE` for its steps (4b): nothing to do there.
  - `launch.py` is 677 lines and under the quality ratchet: add `injected_by_claude_code` to the existing import from `repo_scan` (line 28) and change the one call in `pipeline_plan`.
  - `test_lean.py`'s budget check is red until WP-04 raises the budget: expected in wave 1.
- **Exact imports and APIs:** `os.environ`; `render_rules`, `rule_files`, `ROOT` in `repo_scan.py`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_repo_scan.py"`; `python3 -m unittest discover -s .claude/bin -p "test_launcher.py"`; `python3 -m unittest discover -s .claude/bin -p "test_pipeline.py"`; `node .claude/bin/test_workflow.mjs`.

#### WP-03 · /implement
- Wave 1.
- Files: `.claude/commands/implement.md`, `.claude/bin/test_definitions.py`.
- Consumes `save-result --run` by signature.
- ACs: AC-006.
- **Patterns to mirror:** `.claude/commands/implement.md:42-46` (the two steps that save the result); `.claude/commands/implement.md:50-75` (one bullet per part of the result).
- **Gotchas:** the pre-flight line about `rules-sync` (4b) changes too. `prompt_bytes` is budgeted and this file counts: keep the additions short. The fallback mode already saves its own result with usage: the `--run` step is for the workflow only. When the Workflow tool's result showed no `runId`, the step runs without `--run`.
- **WP validation:** `python3 -m unittest discover -s .claude/bin -p "test_definitions.py"`.

#### WP-04 · Docs, notes, release and the moved tests
- Wave 2.
- Files: `docs/how-it-works.md`, `.claude-plugin/plugin.json`, `.claude/bin/upgrade.py`, `.claude/flow-budget.json`, `.claude/bin/test_qa_recheck.py`, `.claude/bin/test_acceptance_v219.py`.
- ACs: AC-007.
- **Patterns to mirror:** `.claude/bin/upgrade.py:156-170`; `.claude/bin/test_lean_hook.py:1-12` (the header of a file of moved tests); `docs/how-it-works.md:360-364`.
- **Gotchas:**
  - In the guide's module tree (`docs/how-it-works.md:331-352`), add `workflow_usage.py` with one line, as every module has.
  - In the guide: the state tree's `usage.jsonl` line keeps "(fallback mode)" and gains a neighbour for the workflow (`runs/workflow-result.json`, through `save-result --run`); the glossary line "Stack and rules" (line 401) says the workflow leaves the common rules to Claude Code and prints the language ones.
  - Move the classes of `test_acceptance_v219.py` with their helpers and constants. Drop its `ReleaseTests` (it pins the version and "the only acceptance file"); the other four classes move as they are.
  - `flow-budget.json`: raise only what is exceeded, with its why.
  - `.claude/flow-history.json` is regenerated by the maintainer as the last commit, not by this package.
- **WP validation:** the four commands of section 3 and `python3 -m unittest discover -s acceptance`.

```json wp-manifest
{
  "maintainer": true,
  "stack": ["python", "typescript"],
  "allow_bash": ["Bash(python3 -m unittest:*)", "Bash(node .claude/bin/test_workflow.mjs)"],
  "acceptance": {"files": [".claude/bin/test_acceptance_v220.py"], "command": "python3 -m unittest discover -s .claude/bin -p test_acceptance_v220.py"},
  "verify": {"build": "python3 -m unittest discover -s bench -p \"test_*.py\"", "lint": "node .claude/bin/test_workflow.mjs", "types": "python3 -m unittest discover -s bench/acceptance", "tests": "python3 -m unittest discover -s .claude/bin -p \"test_*.py\""},
  "docs": {"files": ["docs/assets/"], "codemap": null},
  "work_packages": [
    {"id": "WP-01", "wave": 1, "depends_on": [], "files": [".claude/bin/workflow_usage.py", ".claude/bin/agentic.py", ".claude/bin/installer.py", ".claude/bin/test_workflow_usage.py"],
     "acs": ["AC-001", "AC-002", "AC-003"], "mirror": [".claude/bin/agentic.py:243-260", ".claude/bin/reports.py:1-40", ".claude/bin/core.py:418-421", ".claude/bin/test_review_fixes.py:120-140"]},
    {"id": "WP-02", "wave": 1, "depends_on": [], "files": [".claude/bin/repo_scan.py", ".claude/bin/launch.py", ".claude/bin/test_repo_scan.py"],
     "acs": ["AC-004", "AC-005"], "mirror": [".claude/bin/repo_scan.py:65-79", ".claude/bin/guardrail.py:564-566", ".claude/bin/test_launcher.py:213-230"]},
    {"id": "WP-03", "wave": 1, "depends_on": [], "files": [".claude/commands/implement.md", ".claude/bin/test_definitions.py"],
     "acs": ["AC-006"], "mirror": [".claude/commands/implement.md:42-46", ".claude/commands/implement.md:50-75"]},
    {"id": "WP-04", "wave": 2, "depends_on": ["WP-01", "WP-02", "WP-03"], "files": ["docs/how-it-works.md", ".claude-plugin/plugin.json", ".claude/bin/upgrade.py", ".claude/flow-budget.json", ".claude/bin/test_qa_recheck.py", ".claude/bin/test_acceptance_v219.py"],
     "acs": ["AC-007"], "mirror": [".claude/bin/upgrade.py:156-170", ".claude/bin/test_lean_hook.py:1-12", "docs/how-it-works.md:360-364"]}
  ]
}
```

## 9. Test strategy

- **Acceptance** (`test_acceptance_v220.py`, written first and red): AC-001 to AC-003 build the annex's files in a temporary folder and point `CLAUDE_CONFIG_DIR` at it; AC-004 and AC-005 install the rules in a temporary repo and read the plan and a fallback prompt; AC-006 and AC-007 read files. Nothing is spent and nothing outside temporary folders is read.
- **Unit:** each package extends the tests of its files.
- **Teeth:** each behaviour is broken once by hand (a message counted per line, the common rules printed in a native plan, the pointer in a fallback prompt, `usage` overwriting an existing one) and the acceptance test must fail.
- **Against real files, by hand, before the pull request:** `usage_of_run` on the run records Claude Code keeps on the maintainer's machine. The result is a table of tokens per agent type, reported in the pull request; the files themselves are not committed.
- **By hand, before the pull request:** `python3 -m unittest discover -s acceptance`, `python3 -m unittest discover -s qa`, the installed-project job, and `agentic.py flow-history` as the last commit with its `--check`.

## 10. Decisions

| Decision | Discarded | Why |
|---|---|---|
| Read the usage from Claude Code's files after the run | Measure inside the script with `budget.spent()` | The script sees only cumulative output tokens of the whole turn: no input, no cache, no split between agents running in parallel. The transcripts carry the exact usage of every message |
| `save-result --run RUN_ID` | A separate command | One step for `/implement` and no new command (chosen by the user). The run id is the one thing the launcher knows that the flow does not |
| Find the record by a glob on the run id | Derive the project and session folders | The project folder's name and the session id are Claude Code's business; the run id is unique and is validated before it is used in a path |
| Tokens, turns and model; no dollars | A price table | Prices change, and a wrong figure is worse than none. The fallback's own `cost_usd` comes from the CLI, not from the flow |
| Degrade to "not recorded" with exit 0 | Fail the command | The layout is internal and undocumented: a Claude Code update must never cost the user a saved result |
| An agent without a transcript is counted in `missing` | Drop the whole usage | A partial figure that says it is partial is still a measurement |
| The plan decides what is printed; the engines do not change | A switch in each engine | The plan is an input both engines already share, so they stay equivalent with no new scenario and no line added to a workflow script that is at its size limit |
| "Native" is read from `CLAUDECODE` | A `pipeline-plan --native` flag passed by the workflow | The flag would change the workflow's command line, pinned by tests in both engines. `hooks-check` already tells the two cases apart this way, and the fallback already removes the variable for its steps |
| Only the files without a `paths` filter are left out (chosen by the user) | Leave out the language rules too | Claude Code injected `common.md` into 62 of 62 agents of five real runs; it injected `python.md` only into agents that opened a matching file with the Read tool, and one reviewer did not get it |
| One line that names the files stays in the prompt | Print nothing | If a session does not load project instructions for a reason the flow cannot see, the agent still knows where the rules are; it costs one sentence |
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS` turns the omission off | Ignore it | With it Claude Code injects nothing, so the rules must be printed |
| The agents' definitions are not changed | Reword "the rules printed in your prompt" | They already say "if it names files instead, read them", which covers the pointer; and three tests pin the phrase |
| The manifest's `docs` zone stays `docs/assets/`, and `verify` does not run `acceptance/` or `qa/` | The guides in the doc-updater's zone; more verify phases | As in the last maintainer designs: the guides are part of the design (WP-04 owns the one that changes) and those two suites are run by hand before the pull request (section 9) |
| No bench run for this release | An A/B | The bench runs the fallback engine, which this release does not change. The first measurements of the native engine come from real runs, through the usage this release records |
| Written with Fable 5.2 | Pause to switch model | The user chose it at the model gate |

## 11. Risks and open questions

- **Claude Code's layout can change.** It is read in one module, defensively, and its absence only costs the usage. Observed in version 2.1.316; nothing says the next version keeps it.
- **The run record may not be on disk yet** when `/implement` runs `save-result`. In the five runs inspected the record was complete, with status `completed`; whether it is always written before the launcher's next step is not verified. The result of that case is "not recorded".
- **A resumed workflow** (`resumeFromRunId`) gets a new run id; whether its record lists the agents answered from the cache, and where their transcripts are, is not verified. Their usage may be missing or belong to the earlier run.
- **Cloud sessions** lose these files with their container: the usage must be read in the session that ran the workflow, which is what `/implement` does.
- **The saving from the rules is not measured.** `common.md` is 3,916 bytes; in a native run it is printed for the implementer, the test-author, the standards reviewer and QA. Its effect on a real run can be read from the recorded usage of runs before and after.
- **`CLAUDE_CODE_DISABLE_CLAUDE_MDS`** is the variable the bench sets to keep `CLAUDE.md` files out of its sessions; that it also stops `.claude/rules/` from being injected is assumed, not verified. If it does not, a session with it set gets the rules twice, as today.
- **If Claude Code stops injecting `.claude/rules/`** into workflow agents, those agents are left with the one-line pointer and must read the file. The definitions already tell them to.

## Annex A · Sample files for the tests

The run record, `projects/p/s/workflows/wf_test-001.json`:

```json
{"runId": "wf_test-001", "status": "completed", "workflowProgress": [
  {"type": "workflow_phase", "index": 1, "title": "Wave 0"},
  {"type": "workflow_agent", "agentId": "a1", "agentType": "test-author", "label": "test-author", "model": "claude-sonnet-5-5", "durationMs": 91234},
  {"type": "workflow_agent", "agentId": "a2", "agentType": "implementer", "label": "WP-02 (fix)", "model": "claude-sonnet-5-5", "durationMs": 40000}]}
```

`projects/p/s/subagents/workflows/wf_test-001/agent-a1.jsonl` (one message on two lines):

```
{"type": "user", "message": {"role": "user", "content": "PROMPT-TEXT"}}
{"type": "assistant", "message": {"id": "msg_1", "content": "ANSWER-TEXT", "usage": {"input_tokens": 3, "cache_creation_input_tokens": 1200, "cache_read_input_tokens": 45000, "output_tokens": 800}}}
{"type": "assistant", "message": {"id": "msg_1", "content": "ANSWER-TEXT", "usage": {"input_tokens": 3, "cache_creation_input_tokens": 1200, "cache_read_input_tokens": 45000, "output_tokens": 800}}}
```

`projects/p/s/subagents/workflows/wf_test-001/agent-a2.jsonl` (two messages):

```
{"type": "assistant", "message": {"id": "msg_2", "usage": {"input_tokens": 5, "cache_creation_input_tokens": 300, "cache_read_input_tokens": 4000, "output_tokens": 100}}}
{"type": "attachment", "attachment": {"type": "instructions"}}
{"type": "assistant", "message": {"id": "msg_3", "usage": {"input_tokens": 5, "cache_creation_input_tokens": 200, "cache_read_input_tokens": 5000, "output_tokens": 50}}}
```
