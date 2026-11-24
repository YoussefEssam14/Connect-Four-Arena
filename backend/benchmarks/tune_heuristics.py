import sys
import os
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.board import Board
from models.tree_node import TreeNode
from models.stats import Stats
from configs.settings import (
    ROWS, COLS, H, WIN, COLUMN_ORDER, DS
)
from ai.heurisitcs.build_windows import WINDOWS
from utils.popcount import popcount


def count_fours(bb: int) -> int:
    count = 0
    for d in DS:
        pairs = bb & (bb >> d)
        fours = pairs & (pairs >> (d << 1))
        count += popcount(fours)
    return count


_COL_MASKS = [
    sum(1 << (c * H + r) for r in range(ROWS))
    for c in range(COLS)
]


@dataclass
class HeuristicParams:
    name: str
    A: float = 1000.0
    THREE: float = 100.0
    THREE_BURIED: float = 0.5
    PARITY_BONUS: float = 60.0
    TEMPO_BONUS: float = 300.0
    TWO: float = 10.0
    LAMBDA: float = 1.0
    COL_WEIGHT: tuple[int, ...] = (3, 4, 5, 7, 5, 4, 3)


def evaluate_custom(board: Board, maximizer: int, p: HeuristicParams) -> float:
    me, opp = maximizer, 1 - maximizer
    mine, theirs = board.bb[me], board.bb[opp]
    occupied = mine | theirs
    to_move = board.player_to_move

    fours = [0, 0]
    score = 0.0

    for window in WINDOWS:
        m = (mine & window).bit_count()
        o = (theirs & window).bit_count()

        if m and o:
            continue

        if m:
            owner, k = me, m
        elif o:
            owner, k = opp, o
        else:
            continue

        sign = 1 if owner == me else -1

        if k == 4:
            fours[owner] += 1
            score += sign * p.A

        elif k == 3:
            empty_bit = window & ~occupied
            idx = empty_bit.bit_length() - 1
            c, r = divmod(idx, H)
            dist = r - board.heights[c]

            val = p.THREE
            if dist == 0:
                if to_move == owner:
                    val += p.TEMPO_BONUS
            else:
                val *= p.THREE_BURIED
                if r % 2 == owner:
                    val += p.PARITY_BONUS

            score += sign * val

        else:
            score += sign * p.TWO

    positional = sum(
        p.COL_WEIGHT[c] * (
            (mine & _COL_MASKS[c]).bit_count() -
            (theirs & _COL_MASKS[c]).bit_count()
        )
        for c in range(COLS)
    )
    score += p.LAMBDA * positional

    if board.full:
        diff = fours[me] - fours[opp]
        return WIN if diff > 0 else -WIN if diff < 0 else 0.0

    return score


def search_custom(
    board: Board,
    depth: int,
    alpha: float,
    beta: float,
    maximizer: int,
    p: HeuristicParams,
) -> tuple[float, int | None]:
    moves = board.valid_moves(COLUMN_ORDER)
    if depth == 0 or not moves:
        return evaluate_custom(board, maximizer, p), None

    maximizing = board.player_to_move == maximizer
    best_move = moves[0]

    if maximizing:
        best_v = -float("inf")
        for col in moves:
            board.make_move(col)
            v, _ = search_custom(board, depth - 1, alpha, beta, maximizer, p)
            board.undo(col)
            if v > best_v:
                best_v = v
                best_move = col
            alpha = max(alpha, best_v)
            if alpha >= beta:
                break
        return best_v, best_move
    else:
        best_v = float("inf")
        for col in moves:
            board.make_move(col)
            v, _ = search_custom(board, depth - 1, alpha, beta, maximizer, p)
            board.undo(col)
            if v < best_v:
                best_v = v
                best_move = col
            beta = min(beta, best_v)
            if alpha >= beta:
                break
        return best_v, best_move


def play_game(p0: HeuristicParams, p1: HeuristicParams, depth: int) -> tuple[int, int, int]:
    board = Board()
    params = [p0, p1]

    while not board.full:
        cur = board.player_to_move
        _, col = search_custom(board, depth, -float("inf"), float("inf"), cur, params[cur])
        if col is None:
            break
        board.make_move(col)

    s0 = count_fours(board.bb[0])
    s1 = count_fours(board.bb[1])
    return s0, s1, board.moves


def run_tuning():
    baseline = HeuristicParams(name="Baseline")
    
    candidates = [
        HeuristicParams(
            name="Tactical-Aggressive",
            A=1000.0,
            THREE=130.0,
            TEMPO_BONUS=450.0,
            PARITY_BONUS=75.0,
            THREE_BURIED=0.45,
            TWO=12.0,
            COL_WEIGHT=(2, 4, 7, 10, 7, 4, 2),
        ),
        HeuristicParams(
            name="Center-Dominance",
            A=1000.0,
            THREE=110.0,
            TEMPO_BONUS=380.0,
            PARITY_BONUS=70.0,
            THREE_BURIED=0.5,
            TWO=15.0,
            COL_WEIGHT=(1, 3, 6, 9, 6, 3, 1),
        ),
        HeuristicParams(
            name="Balanced-Master",
            A=1000.0,
            THREE=120.0,
            TEMPO_BONUS=420.0,
            PARITY_BONUS=80.0,
            THREE_BURIED=0.48,
            TWO=14.0,
            COL_WEIGHT=(2, 4, 6, 9, 6, 4, 2),
        ),
    ]

    print("=================================================================")
    print("        HEURISTIC PARAMETER FINE-TUNING TOURNAMENT")
    print("=================================================================")
    print(f"Matchups played at search depth 4 (alternating Red / Yellow)...")

    results = []
    for cand in candidates:
        print(f"\nEvaluating: {cand.name} vs Baseline...")
        
        # Game 1: Cand plays Player 0 (Red), Baseline plays Player 1 (Yellow)
        t0 = time.perf_counter()
        c_score1, b_score1, moves1 = play_game(cand, baseline, depth=4)
        t1 = time.perf_counter()
        print(f"  Game 1 ({cand.name} as P0): {cand.name} {c_score1} - {b_score1} Baseline (in {t1-t0:.2f}s, {moves1} moves)")

        # Game 2: Baseline plays Player 0 (Red), Cand plays Player 1 (Yellow)
        t2 = time.perf_counter()
        b_score2, c_score2, moves2 = play_game(baseline, cand, depth=4)
        t3 = time.perf_counter()
        print(f"  Game 2 ({cand.name} as P1): {cand.name} {c_score2} - {b_score2} Baseline (in {t3-t2:.2f}s, {moves2} moves)")

        total_cand = c_score1 + c_score2
        total_base = b_score1 + b_score2
        diff = total_cand - total_base
        results.append((cand, total_cand, total_base, diff))
        print(f"  --> Total Points: {cand.name} {total_cand} vs Baseline {total_base} (Diff: {diff:+d})")

    print("\n" + "=" * 65)
    print("                 TUNING SUMMARY & RANKINGS")
    print("=" * 65)
    print(f"{'Profile':<22} | {'Cand Score':<12} | {'Base Score':<12} | {'Net Diff':<10}")
    print("-" * 65)
    for cand, c_pts, b_pts, diff in sorted(results, key=lambda x: x[3], reverse=True):
        print(f"{cand.name:<22} | {c_pts:<12} | {b_pts:<12} | {diff:+10d}")
    print("=" * 65)


if __name__ == "__main__":
    run_tuning()
