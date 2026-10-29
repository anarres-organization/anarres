# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Exception types shared by the docvault modules."""


class Denied(Exception):
    """A request resolved to a location outside the user's folder."""


class CommandError(Exception):
    """A request could not be carried out; the message is shown to the user."""
