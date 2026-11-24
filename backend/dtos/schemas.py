from configs.settings import COLS, DEFAULT_K
from pydantic import BaseModel, Field
from models.color import Color


class NewGameRequest(BaseModel):
    k: int = Field(DEFAULT_K, ge=1, le=9, description="Alpha-beta search depth")
    human_color: Color = "R"


class MoveRequest(BaseModel):
    column: int = Field(ge=0, le=COLS - 1)


class StatsResponse(BaseModel):
    nodes: int
    leaves: int
    cutoffs: int
    time: float


class GameState(BaseModel):
    k: int
    grid: list[list[str]]
    human_score: int
    ai_score: int
    human_color: Color
    ai_color: Color
    winner: str | None
    is_game_over: bool
    is_human_turn: bool
    ai_column: int | None
    stats: StatsResponse | None
