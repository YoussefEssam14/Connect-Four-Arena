import pytest
import services.game_service as gs_module
from services.game_service import GameService, new_game, get_game
from exceptions.exception import (
    NotCurrentPlayerMoveException,
    GameOverException,
    NoActiveGameException,
)


@pytest.fixture(autouse=True)
def reset_game():
    gs_module._game = None
    yield
    gs_module._game = None


def test_new_game_creates_instance():
    game = new_game(k=2)
    assert isinstance(game, GameService)


def test_get_game_raises_when_none():
    with pytest.raises(NoActiveGameException):
        get_game()


def test_get_game_returns_active():
    new_game()
    game = get_game()
    assert isinstance(game, GameService)


def test_human_move_updates_grid():
    game = new_game(k=2, human_color="R")
    game.human_move(3)
    grid = game.board.to_grid()
    assert grid[0][3] != "."


def test_ai_moves_after_human():
    game = new_game(k=2, human_color="R")
    game.human_move(3)
    assert game.board.moves >= 2


def test_not_human_turn_raises():
    game = new_game(k=2, human_color="R")
    game.board.make_move(3)
    with pytest.raises(NotCurrentPlayerMoveException):
        game.human_move(3)


def test_state_shape():
    game = new_game(k=2)
    state = game.state()
    for key in ("k", "grid", "human_score", "ai_score", "human_color",
                "ai_color", "winner", "is_game_over", "is_human_turn",
                "ai_column", "stats"):
        assert key in state


def test_winner_none_at_start():
    game = new_game(k=2)
    assert game.winner() is None


def test_human_color_r_goes_first_no_ai_stats():
    game = new_game(k=2, human_color="R")
    assert game.is_human_turn is True
    assert game.last_stats is None
    assert game.last_ai_column is None


def test_human_color_y_ai_opens():
    game = new_game(k=2, human_color="Y")
    assert game.is_human_turn is True
    assert game.last_ai_column is not None
    assert game.last_stats is not None
    assert game.board.moves == 1
