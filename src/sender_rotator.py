"""Rotate display names for the From header.

Gmail lets you set any display name even though the address stays fixed.
This module cycles through a list of sender names so each recipient (or
each batch) sees a different "From" name — useful for deliverability
testing and A/B experiments.
"""

from itertools import cycle


class SenderRotator:
    """Round-robin through *names* for every call to :meth:`next`."""

    def __init__(self, names: list[str]):
        if not names:
            raise ValueError("At least one sender name is required.")
        self._cycle = cycle(names)
        self._names = names
        self._index = -1  # no name emitted yet

    def next(self) -> str:
        self._index = (self._index + 1) % len(self._names)
        return next(self._cycle)

    def current(self) -> str:
        """Return the name most recently produced by :meth:`next`."""
        if self._index < 0:
            return self._names[0]
        return self._names[self._index]

    @classmethod
    def from_config(cls, config: dict) -> "SenderRotator":
        """Build from a settings dict with key ``sender_names``."""
        names = config.get("sender_names", [])
        if isinstance(names, str):
            names = [n.strip() for n in names.split(",") if n.strip()]
        return cls(names)
