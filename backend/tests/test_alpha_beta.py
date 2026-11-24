import pytest
from ai.algorithms.alpha_beta import best_move
from models.board import Board


def test_best_move_returns_valid_column():
    b = Board()
    col, root, stats = best_move(b, 2, 0)
    assert 0 <= col <= 6
    assert b.can_play(col)


def test_stats_populated():
    b = Board()
    _, root, stats = best_move(b, 2, 0)
    assert stats.nodes > 0
    assert stats.leaves > 0
    assert stats.time > 0


def test_root_has_best_move():
    b = Board()
    col, root, _ = best_move(b, 2, 0)
    assert root.best_move == col


def test_tree_depth():
    b = Board()
    _, root, _ = best_move(b, 2, 0)
    assert root.depth == 0
    assert all(c.depth == 1 for c in root.children if not c.pruned)


def test_prefers_centre():
    b = Board()
    col, _, _ = best_move(b, 3, 0)
    assert col in (2, 3, 4)
