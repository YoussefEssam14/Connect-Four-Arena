from typing import Literal
from configs.settings import COLS, DEFAULT_K, MAX_SEARCH_DEPTH
from pydantic import BaseModel, Field
from models.color import Color


class NewGameRequest(BaseModel):
    k: int = Field(DEFAULT_K, ge=1, le=MAX_SEARCH_DEPTH, description="Alpha-beta search depth")
    human_color: Color = "R"


class MoveRequest(BaseModel):
    column: int = Field(ge=0, le=COLS - 1)


class StatsResponse(BaseModel):
    nodes: int
    leaves: int
    cutoffs: int
    time: float


class MoveEvidence(BaseModel):
    role: str
    value: float | str | None
    alpha: float | str
    beta: float | str
    best_move: int | None
    pruned: bool
    cutoffs: int = 0


class MoveHistoryEntry(BaseModel):
    ply: int
    actor: Literal["initial", "human", "ai"]
    color: Color | None = None
    column: int | None = None
    grid: list[list[str]]
    human_score: int
    ai_score: int
    evidence: MoveEvidence | None = None


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
    history: list[MoveHistoryEntry] = Field(default_factory=list)
