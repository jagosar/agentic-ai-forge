"""Test doubles for the acceptance tests."""


class FakeMailer:
    """Records every email it is asked to send."""

    def __init__(self):
        self.calls = 0
        self._sent = []

    def send(self, to, subject):
        self.calls += 1
        self.sent.append((to, subject))

    @property
    def sent(self):
        return list(self._sent)
