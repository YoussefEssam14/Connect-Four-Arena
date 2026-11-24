import pytest
from models.board import Board
from exceptions.exception import (
    OutOfBoundsException,
    FullColumnException,
    GameOverException,
    InvalidUndoException,
)
from configs.settings import ROWS, COLS


def test_initial_state():
    b = Board()
    assert b.moves == 0
    assert b.player_to_move == 0
    assert not b.full
    assert b.heights == [0] * COLS


def test_make_move_updates_state():
    b = Board()
    b.make_move(3)
    assert b.moves == 1
    assert b.player_to_move == 1
    assert b.heights[3] == 1


def test_make_move_alternates_players():
    b = Board()
    b.make_move(0)
    b.make_move(0)
    assert b.bb[0] & (1 << 0)
    assert b.bb[1] & (1 << 1)


def test_out_of_bounds_raises():
    b = Board()
    with pytest.raises(OutOfBoundsException):
        b.make_move(-1)
    with pytest.raises(OutOfBoundsException):
        b.make_move(COLS)


def test_full_column_raises():
    b = Board()
    for _ in range(ROWS):
        b.make_move(0)
        b.make_move(6)
    with pytest.raises(FullColumnException):
        b.make_move(0)


def test_undo_restores_state():
    b = Board()
    b.make_move(3)
    b.undo(3)
    assert b.moves == 0
    assert b.heights[3] == 0
    assert b.bb[0] == 0


def test_invalid_undo_raises():
    b = Board()
    with pytest.raises(InvalidUndoException):
        b.undo(0)


def test_to_grid_empty():
    b = Board()
    grid = b.to_grid()
    assert len(grid) == ROWS
    assert all(cell == "." for row in grid for cell in row)


def test_to_grid_shows_pieces():
    b = Board(symbols=["R", "Y"])
    b.make_move(0)
    grid = b.to_grid()
    assert grid[0][0] == "R"


def test_valid_moves_full_column_excluded():
    b = Board()
    for _ in range(ROWS):
        b.make_move(0)
        b.make_move(6)
    moves = b.valid_moves(list(range(COLS)))
    assert 0 not in moves
    assert 6 not in moves


def test_to_grid_roundtrip():
    b = Board(symbols=["R", "Y"])
    sequence = [3, 3, 2, 4, 1, 5]
    for col in sequence:
        b.make_move(col)
    grid = b.to_grid()
    assert grid[0][3] == "R"
    assert grid[1][3] == "Y"
