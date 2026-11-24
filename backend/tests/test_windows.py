import pytest
from ai.heurisitcs.build_windows import WINDOWS, _build_windows
from configs.settings import ROWS, COLS


def test_windows_is_tuple():
    assert isinstance(WINDOWS, tuple)


def test_windows_count():
    expected = len(_build_windows())
    assert len(WINDOWS) == expected


def test_all_windows_are_nonzero():
    assert all(w > 0 for w in WINDOWS)


def test_windows_have_exactly_4_bits():
    for w in WINDOWS:
        assert w.bit_count() == 4


def test_no_duplicate_windows():
    assert len(set(WINDOWS)) == len(WINDOWS)
