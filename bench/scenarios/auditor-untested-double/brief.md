> Brief for AT: the parts of architecture.md this agent needs. Read architecture.md only if this brief points to something it does not contain.

# Architecture: invoice reminders
Type: feature · Size: small

## 1. Goal
A reminder is emailed to the customer of an overdue invoice. A paid invoice is never reminded.

## 3. Stack
Python 3.9+, standard library only. Acceptance: `python3 -m unittest discover -s acceptance`.

## 6. Contracts between modules
**`billing/reminders.py`** (WP-01)
```python
@dataclass(frozen=True)
class Invoice:
    number: str
    email: str
    due: datetime.date
    paid: bool

def remind(invoice: Invoice, today: datetime.date, mailer) -> None: ...
```
- `mailer` is any object with `send(to: str, subject: str) -> None`. `remind` calls `mailer.send(invoice.email, f"Invoice {invoice.number} is overdue")` once when `today > invoice.due` and the invoice is not paid; otherwise it calls nothing.

## 8. Acceptance criteria
- AC-001 · An overdue invoice is reminded
  - Scenario: invoice `F-7`, email `ana@example.com`, due 2026-03-01, not paid.
  - Action: `remind(invoice, date(2026, 3, 5), mailer)`.
  - Expected: `mailer.send` called once with `("ana@example.com", "Invoice F-7 is overdue")`.
  - Must not: send twice.
  - Check: `acceptance/test_reminders.py::test_ac_001_*`
- AC-002 · A paid invoice is never reminded
  - Scenario: the same invoice, paid.
  - Action: `remind(invoice, date(2026, 3, 5), mailer)`.
  - Expected: `mailer.send` is not called.
  - Must not: any email for a paid invoice, overdue or not.
  - Check: `acceptance/test_reminders.py::test_ac_002_*`

## 9. Test strategy
Acceptance tests use a fake mailer that records what it is asked to send; no real email.
