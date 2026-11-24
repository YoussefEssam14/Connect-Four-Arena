import pytest
from ai.heurisitcs.evaluate import evaluate
from models.board import Board


def test_empty_board_scores_zero():
    b = Board()
    score, info = evaluate(b, 0)
    assert score == 0.0


def test_score_favours_me_over_opponent():
    b_mine = Board()
    b_mine.make_move(3)
    b_mine.make_move(6)
    b_mine.make_move(3)
    b_mine.make_move(6)
    b_mine.make_move(3)
    score_mine, _ = evaluate(b_mine, 0)

    b_opp = Board()
    b_opp.make_move(6)
    b_opp.make_move(3)
    b_opp.make_move(6)
    b_opp.make_move(3)
    b_opp.make_move(6)
    score_opp, _ = evaluate(b_opp, 0)

    assert score_mine > score_opp


def test_info_keys_present():
    b = Board()
    _, info = evaluate(b, 0)
    for key in ("fours_me", "fours_opp", "threes_me", "threes_opp",
                "twos_me", "twos_opp", "positional", "score"):
        assert key in info
