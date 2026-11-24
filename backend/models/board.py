from configs.settings import ROWS, COLS, H, CELLS
from exceptions.exception import (
    OutOfBoundsException,
    GameOverException,
    FullColumnException,
    InvalidUndoException,
)


class Board:
    def __init__(self, symbols: list[str] = ["R", "Y"]):
        self.symbols = symbols
        self.bb = [0, 0]
        self.moves = 0
        self.heights = [0] * COLS

    @property
    def player_to_move(self) -> int:
        return self.moves & 1

    @property
    def full(self) -> bool:
        return self.moves == CELLS

    def can_play(self, column: int) -> bool:
        return self.heights[column] < ROWS

    def make_move(self, column: int) -> None:
        if not (0 <= column < COLS):
            raise OutOfBoundsException(f"Column {column} out of bounds (0–{COLS - 1})")
        if self.full:
            raise GameOverException("Game is already over")
        if not self.can_play(column):
            raise FullColumnException(f"Column {column} is full")

        player = self.player_to_move
        row = self.heights[column]
        self.bb[player] |= 1 << (column * H + row)
        self.moves += 1
        self.heights[column] += 1

    def undo(self, column: int) -> None:
        if not (0 <= column < COLS) or self.heights[column] == 0:
            raise InvalidUndoException(f"Cannot undo column {column}")

        self.heights[column] -= 1
        self.moves -= 1
        player = self.player_to_move
        row = self.heights[column]
        self.bb[player] &= ~(1 << (column * H + row))

    def to_grid(self) -> list[list[str]]:
        grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
        for player, symbol in enumerate(self.symbols):
            for r in range(ROWS):
                for c in range(COLS):
                    if self.bb[player] & (1 << (c * H + r)):
                        grid[r][c] = symbol
        return grid

    def valid_moves(self, order: list[int]) -> list[int]:
        return [c for c in order if self.can_play(c)]
