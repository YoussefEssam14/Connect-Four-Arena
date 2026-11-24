from models.board import Board
from models.color import Color
from models.tree_node import TreeNode, serialize_bound, tree_to_dict
from models.stats import Stats
from ai.algorithms.alpha_beta import best_move
from configs.settings import DEFAULT_K
from exceptions.exception import (
    NotCurrentPlayerMoveException,
    NoActiveGameException,
    GameOverException,
)



class GameService:
    """
    One game session.

    Color determines turn order — R is always player 0 in the bitboard,
    so R always moves first. If the human picks Y, the AI (R) opens.
    """

    def __init__(self, k: int = DEFAULT_K, human_color: Color = "R"):
        self.k = k
        self.human_color: Color = human_color
        self.ai_color: Color = "Y" if human_color == "R" else "R"

        self.human_idx = 0 if human_color == "R" else 1
        self.ai_idx = 1 - self.human_idx

        self.board = Board(symbols=["R", "Y"])
        self.last_stats: Stats | None = None
        self.last_tree: TreeNode | None = None
        self.last_ai_column: int | None = None
        self.history: list[dict] = []
        self._record_initial()

        if not self.is_human_turn:
            self._run_ai()

    @property
    def is_human_turn(self) -> bool:
        return self.board.player_to_move == self.human_idx

    @property
    def game_over(self) -> bool:
        return self.board.full

    def _record_initial(self) -> None:
        self.history.append({
            "ply": 0,
            "actor": "initial",
            "color": None,
            "column": None,
            "grid": self.board.to_grid(),
            "human_score": 0,
            "ai_score": 0,
            "evidence": None,
        })

    def _record_ply(
        self,
        actor: str,
        color: Color,
        column: int,
        evidence: dict | None = None,
    ) -> None:
        human_score, ai_score = self.scores()
        self.history.append({
            "ply": len(self.history),
            "actor": actor,
            "color": color,
            "column": column,
            "grid": self.board.to_grid(),
            "human_score": human_score,
            "ai_score": ai_score,
            "evidence": evidence,
        })

    def human_move(self, column: int) -> "GameService":
        if self.game_over:
            raise GameOverException("Game is already over")
        if not self.is_human_turn:
            raise NotCurrentPlayerMoveException("Not the human's turn")

        self.board.make_move(column)
        self.last_ai_column = None
        self._record_ply(actor="human", color=self.human_color, column=column, evidence=None)

        if not self.game_over and not self.is_human_turn:
            self._run_ai()

        return self

    def _run_ai(self) -> None:
        col, tree, stats = best_move(self.board, self.k, self.ai_idx)
        self.last_tree = tree
        self.last_stats = stats
        self.last_ai_column = col
        if col is None:
            return
        self.board.make_move(col)
        evidence = {
            "role": tree.kind,
            "value": serialize_bound(tree.value),
            "alpha": serialize_bound(tree.alpha),
            "beta": serialize_bound(tree.beta),
            "best_move": tree.best_move,
            "pruned": stats.cutoffs > 0,
            "cutoffs": stats.cutoffs,
        }
        self._record_ply(actor="ai", color=self.ai_color, column=col, evidence=evidence)

    def winner(self) -> str | None:
        if not self.game_over:
            return None
        my_fours, ai_fours = self.scores()
        if my_fours > ai_fours:
            return self.human_color
        if ai_fours > my_fours:
            return self.ai_color
        return "draw"

    def scores(self) -> tuple[int, int]:
        return (
            self.board.count_fours(self.human_idx),
            self.board.count_fours(self.ai_idx),
        )

    def state(self) -> dict:
        human_score, ai_score = self.scores()
        stats_dict = None
        if self.last_stats:
            stats_dict = {
                "nodes": self.last_stats.nodes,
                "leaves": self.last_stats.leaves,
                "cutoffs": self.last_stats.cutoffs,
                "time": self.last_stats.time,
            }
        return {
            "k": self.k,
            "grid": self.board.to_grid(),
            "human_score": human_score,
            "ai_score": ai_score,
            "human_color": self.human_color,
            "ai_color": self.ai_color,
            "winner": self.winner(),
            "is_game_over": self.game_over,
            "is_human_turn": self.is_human_turn,
            "ai_column": self.last_ai_column,
            "stats": stats_dict,
            "history": self.history,
        }

    def tree(self, max_depth: int | None = None) -> dict | None:
        if self.last_tree is None:
            return None
        return tree_to_dict(self.last_tree, max_depth)


_game: GameService | None = None


def get_game() -> GameService:
    if _game is None:
        raise NoActiveGameException("No active game — start a new one first")
    return _game


def new_game(k: int = DEFAULT_K, human_color: Color = "R") -> GameService:
    global _game
    _game = GameService(k=k, human_color=human_color)
    return _game
