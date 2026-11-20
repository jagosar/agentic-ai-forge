import unittest
from datetime import date

from acceptance.fakes import FakeMailer
from billing.reminders import Invoice, remind

OVERDUE = Invoice(number="F-7", email="ana@example.com", due=date(2026, 3, 1), paid=False)
PAID = Invoice(number="F-7", email="ana@example.com", due=date(2026, 3, 1), paid=True)
TODAY = date(2026, 3, 5)


class Reminders(unittest.TestCase):
    def test_ac_001_an_overdue_invoice_is_reminded_once(self):
        mailer = FakeMailer()
        remind(OVERDUE, TODAY, mailer)
        self.assertEqual(mailer.calls, 1)

    def test_ac_002_a_paid_invoice_is_never_reminded(self):
        mailer = FakeMailer()
        remind(PAID, TODAY, mailer)
        self.assertEqual(mailer.sent, [])

    def test_ac_002_a_paid_invoice_is_not_reminded_before_its_due_date(self):
        mailer = FakeMailer()
        remind(PAID, date(2026, 2, 1), mailer)
        self.assertEqual(mailer.sent, [])
