# Field report: 2.14.0 on a PowerShell 5.1 / Pester 3.4 repo (November 2026)

These notes cover two standard cycles (D and E, 2026-11-18/19) on a Windows repo. The repo is a PowerShell 5.1 and WinForms toolkit tested with Pester 3.4.0, and the cycles ran the native `agentic-implement` workflow. Cycle D took 2 runs. Cycle E took 6 launches before it reached verification. Another session that ran the cycles reported the incidents. Each one below was checked against this repository's code; that session's run records were not available here.

Verdicts:
- **Fixed**: fixed in this branch, with a test that fails without the fix.
- **Design**: needs a maintainer design before code.
- **Rules**: belongs in the language rules or the prompts.
- **Not reproduced**: could not be confirmed here.

## A. The flow itself

| # | Incident | Cause found | Verdict |
|---|---|---|---|
| 1 | Prepare stopped with "pipeline-plan failed: the manifest is not valid" while `validate` said the manifest was valid | Both engines gave that message whenever they had no usable `pipeline-plan` step, including a garbled `seq` reply (the gatekeeper ran `hooks-check pipeline-plan briefs` without `seq`). | **Fixed.** A lost or garbled reply now reports the gatekeeper's `LOST` message. An empty `pipeline-plan` reports "produced no readable output". Only a `pipeline-plan` that ran and failed reports an invalid manifest. |
| 2 | `open-stage 2` exited 5 when Git Bash failed to start, and the run ended | A crash before Python starts is treated like any failed step. | **Design.** `open-stage` can be repeated safely: it resets the gate counters and takes the snapshot again. A crash with no JSON output could get one automatic retry, reported as an environment error. Today a garbled reply is never retried, on purpose (`test_workflow.mjs`, "a garbled gatekeeper reply is never retried"), so this decision needs a maintainer. `close-stage` must stay without retry. |
| 3 | A test already red on `main` made verification report "regression" with no suspect | `verification.py` already compares failure lines with the baseline, not just the phase result. But it read a runner's **summary line** as a failure line, and those counts change whenever a cycle adds passing tests: `Passed: 100 Failed: 1` becomes `Passed: 112 Failed: 1`, and pytest's `1 failed, 10 passed` becomes `1 failed, 14 passed`. That line is new, no package owns it, and the run stops. Pester's failing `[-] It` lines did not count as failure lines at all. | **Fixed**, for every framework. Counts next to a runner's summary words read as `N`, and Pester's `[-]` marks a failure line. A new failure beside an old one is still a regression: the tests cover pytest and Pester. |
| 4 | A fix cycle went to a package (WP-05) that did not own the failing QA test | `attribute()` searches the last 200 output lines for AC ids and owned paths, **including lines of tests that passed**. Pester prints every `Describing AC-…` heading, and `pytest -v` prints every `PASSED` line, so a failure is blamed on every package whose AC appears anywhere in the output. | **Design.** Attribution should read only the lines of failing tests. The heading context needs care (in Pester the AC is in the `Describe`, not in the `[-]` line), and the robust source is the runner's report: NUnit XML for Pester, JUnit XML for pytest and jest. |
| 5 | The stop gate refused a DONE twice, citing only the heading "Describing AC-313 …" | Same cause, in `stage.own_failure`. It keeps every line that names the package's AC, including the heading of a `Describe` whose `It`s all passed, while another package's `Describe` failed. | **Design**, together with item 4. |
| 6 | Auto mode blocked an implementer's `powershell` test run, and the code arrived untested | `sync-permissions` allows the manifest's `allow_bash` patterns. Whether the auto-mode classifier respects them for this command line was not reproduced. | **Not reproduced.** The proposal to answer `BLOCKED` when the tests cannot run is not adopted. Verification runs the full suite after the wave anyway, and `BLOCKED` sends the package to a person as a design gap. The implementer must list the unrun check in `not_checked`. |

## B. Acceptance tests that were wrong (Pester 3.4 / PS 5.1)

| # | Trap | Verdict |
|---|---|---|
| 7 | Mocks with `-ModuleName` keep their call history across the `It`s of one `Describe`, and `Import-Module -Force` inside an `It` leaves later mocks stale, so `Assert-MockCalled` counts carry over. | **Rules** |
| 8 | Array unrolling: a helper returning `@(...)` with one element comes back unrolled, so `.Count` counts the hashtable's keys. `@($list)` on a `List[object]` throws "argument types do not match" on 5.1.26100. | **Rules** |
| 9 | Scope: a global test double that reads `$script:Vin` finds it empty inside the script under test. | **Rules** |

The rules library has no PowerShell file (`.claude/rules-library/` covers python, typescript, go, rust, java, kotlin, csharp, ruby, php and swift). Proposal:
- Add `powershell.md` with these three traps, and teach `agentic.py stack` to detect `.ps1`, `.psm1` and `.psd1`.
- Have the test-auditor require that every new helper or double is exercised once against a trivial double before wave 0 ends.

That auditor rule is a prompt change, so it should be measured with a `bench/scenario.py` scenario before shipping.

## C. Design gaps /architect could catch

| # | Gap | Verdict |
|---|---|---|
| 10 | The plan's list of old tests to update missed a test that pins a file the plan changes: it compared the CI Pester line with a base commit. | **Rules**, for the architect prompt: grep `acceptance/` and `qa/` for every file and literal the plan changes, and list each hit in 4b. Measure with a scenario before shipping. |

## D. Guarding against concurrent work

| # | Incident | Verdict |
|---|---|---|
| 11 | Another session and the operator committed in the same tree while a wave ran. The guard stopped it correctly ("git state changed during the stage"). | **Fixed** (launch message): `/implement` now tells the user that nobody may commit, switch branches or edit files in the folder until the workflow ends. Running each cycle in its own worktree is **Design**: the guard, the ledger and `.claude/state` assume the repo root. |

## Proposed next design

One design could cover items 2, 4 and 5, plus the PowerShell rules (7–9), as "runner reports and environment errors":
- attribute failures, and run the stop gate, from the runner's XML report when the manifest names one, falling back to failure lines only;
- retry a stage-opening step once on an interpreter crash;
- add `powershell.md` with stack detection.

Items 6 and 10 are prompt changes that need a scenario each.
