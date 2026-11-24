"""
Connect Four API endpoints
"""
from fastapi import APIRouter, HTTPException, Query

from dtos.schemas import NewGameRequest, MoveRequest, GameState
from services.game_service import new_game, get_game
from exceptions.exception import (
    FullColumnException,
    OutOfBoundsException,
    GameOverException,
    NotCurrentPlayerMoveException,
    NoActiveGameException,
)

router = APIRouter(prefix="/game", tags=["game"])

_CLIENT_ERRORS = (
    FullColumnException,
    OutOfBoundsException,
    GameOverException,
    NotCurrentPlayerMoveException,
    NoActiveGameException,
)


def _guard(fn, *args, **kwargs):
    """Catch game exceptions and convert to HTTP 400."""
    try:
        return fn(*args, **kwargs)
    except _CLIENT_ERRORS as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/new", response_model=GameState, summary="Start a new game")
def start_game(req: NewGameRequest):
    """
    Initialize a new game with specified parameters.
    
    If human is not playing first, AI will move automatically.
    """
    game = new_game(k=req.k, human_color=req.human_color)
    return GameState(**game.state())


@router.post("/move", response_model=GameState, summary="Human drops a piece")
def human_move(req: MoveRequest):
    """
    Drop a piece in the specified column and let AI respond if game continues.
    """
    game = _guard(get_game)
    _guard(game.human_move, req.column)
    return GameState(**game.state())


@router.get("", response_model=GameState, summary="Current board snapshot")
def get_state():
    """Get current game state without making a move."""
    game = _guard(get_game)
    return GameState(**game.state())


@router.get("/tree", summary="Last AI minimax tree")
def get_tree(max_depth: int = Query(2, ge=0, le=6)):
    """
    Retrieve the minimax tree from the last AI move.
    
    max_depth: Limit tree depth in response (0 = root only)
    """
    game = _guard(get_game)
    tree = game.tree(max_depth)
    if tree is None:
        raise HTTPException(status_code=404, detail="No AI move has been made yet")
    return tree
