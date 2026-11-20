# Architecture: a friendlier cart summary
Type: change · Size: small

## 1. Goal
The line under the basket reads "3 items in your cart" instead of "Total: 3 items", and a single item reads "1 item in your cart".

## 2. Scope
### Included
- `lib/report.py`: the new wording, singular and plural.
### Excluded (non-goals)
- Prices and currencies.

## 3. Stack
Python 3.11, standard library only. Tests: `python3 -m unittest discover -s tests`.

## 4. Repository structure
```
lib/report.py              WP-01
tests/test_summary.py      WP-01 (new)
```

## 4b. Existing code context
| What an implementer needs to know | Where it is | Pattern or rule | Source |
|---|---|---|---|
| `summary(items)` builds the line from the number of items | `lib/report.py:4-6` | Module docstring, one function | read |

## 5. Data model
A list of item names.

## 6. Contracts between modules
```python
def summary(items: list) -> str: ...
```
- `summary([])` returns `"0 items in your cart"`, `summary(["a"])` returns `"1 item in your cart"`, three items return `"3 items in your cart"`.

## 7. Conventions
Standard library only; one behaviour per test.

## 8. Work packages and acceptance criteria
### Acceptance criteria
- AC-001 · The new wording
  - Scenario: no state.
  - Action: `summary(["a", "b", "c"])` and `summary(["a"])`.
  - Expected: `"3 items in your cart"` and `"1 item in your cart"`.
  - Must not: the word `Total`.
  - Check: `acceptance/test_summary.py::test_ac_001_new_wording`
  - WP: WP-01

### Work packages
#### WP-01 · The summary line
- Wave: 1.
- Files: `lib/report.py`, `tests/test_summary.py`.
- Implements: `summary` (section 6).
- ACs: AC-001.
- Patterns to mirror: `lib/report.py:1-6`.
- Validation: `python3 -m unittest discover -s tests`.

```json wp-manifest
{"stack": ["python"], "acceptance": {"files": ["acceptance/"], "command": "python3 -m unittest discover -s acceptance"},
 "verify": {"tests": "python3 -m unittest discover -s tests"},
 "work_packages": [{"id": "WP-01", "wave": 1, "depends_on": [], "files": ["lib/report.py", "tests/test_summary.py"],
   "acs": ["AC-001"], "mirror": ["lib/report.py:1-6"]}]}
```

## 9. Test strategy
Unit tests in `tests/`, acceptance in `acceptance/`.

## 10. Decisions
- Keep one function; no template engine.

## 11. Risks and open questions
- None.
