"""Tests for the round-robin sender-name rotator."""

import pytest

from src.sender_rotator import SenderRotator


def test_rotates_round_robin():
    r = SenderRotator(["A", "B", "C"])
    assert [r.next() for _ in range(4)] == ["A", "B", "C", "A"]


def test_current_matches_last_next():
    r = SenderRotator(["A", "B", "C"])
    assert r.current() == "A"  # sensible default before any next()
    r.next()  # -> A
    assert r.current() == "A"
    r.next()  # -> B
    assert r.current() == "B"


def test_empty_names_raises():
    with pytest.raises(ValueError):
        SenderRotator([])


def test_from_config_accepts_list():
    r = SenderRotator.from_config({"sender_names": ["X", "Y"]})
    assert r.next() == "X"


def test_from_config_accepts_comma_string():
    r = SenderRotator.from_config({"sender_names": "X, Y , Z"})
    assert [r.next() for _ in range(3)] == ["X", "Y", "Z"]
