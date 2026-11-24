import sys
import os
import time
import math
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.board import Board
from models.tree_node import TreeNode
from models.stats import Stats
from configs.settings import (
    ROWS, COLS, H, WIN, COLUMN_ORDER, DS
)
from ai.heurisitcs.evaluate import evaluate
from ai.algorithms.alpha_beta import _alpha_beta, best_move

INF = float("inf")


def _minimax_no_pruning(
    board: Board,
    depth: int,
    maximizer: int,
    stats: Stats,
    col_order: list[int],
) -> float:
    stats.nodes += 1
    moves = board.valid_moves(col_order)

    if depth == 0 or not moves:
        stats.leaves += 1
        score, _ = evaluate(board, maximizer)
        return score

    maximizing = board.player_to_move == maximizer
    best = -INF if maximizing else INF

    for col in moves:
        board.make_move(col)
        v = _minimax_no_pruning(board, depth - 1, maximizer, stats, col_order)
        board.undo(col)
        if maximizing:
            best = max(best, v)
        else:
            best = min(best, v)

    return best


def _alpha_beta_bench(
    board: Board,
    depth: int,
    alpha: float,
    beta: float,
    maximizer: int,
    stats: Stats,
    col_order: list[int],
) -> float:
    stats.nodes += 1
    moves = board.valid_moves(col_order)

    if depth == 0 or not moves:
        stats.leaves += 1
        score, _ = evaluate(board, maximizer)
        return score

    maximizing = board.player_to_move == maximizer
    best = -INF if maximizing else INF

    for col in moves:
        board.make_move(col)
        v = _alpha_beta_bench(board, depth - 1, alpha, beta, maximizer, stats, col_order)
        board.undo(col)

        if maximizing:
            best = max(best, v)
            alpha = max(alpha, best)
        else:
            best = min(best, v)
            beta = min(beta, best)

        if alpha >= beta:
            stats.cutoffs += 1
            break

    return best


def run_benchmark():
    print("=" * 80)
    print("          ALPHA-BETA PRUNING BENCHMARK & SEARCH EFFICIENCY")
    print("=" * 80)
    print(f"Platform: Python {sys.version.split()[0]} | Board: {ROWS}x{COLS} (Alexandria Connect-4)")
    print(f"Center-First Order: {COLUMN_ORDER}")
    print(f"Sequential Order:   {[0, 1, 2, 3, 4, 5, 6]}")
    print("=" * 80)

    # 1. Depth scaling benchmark on initial board
    board = Board()
    sequential_order = list(range(COLS))

    print("\n--- 1. MINIMAX vs ALPHA-BETA PRUNING SCALING (Empty Board, Depths 1 to 5) ---")
    header = (
        f"{'Depth':<6} | {'Minimax Nodes':<14} | {'AB Nodes':<12} | "
        f"{'Cutoffs':<8} | {'Pruned %':<10} | {'MM Time':<10} | {'AB Time':<10} | {'Speedup':<8}"
    )
    print(header)
    print("-" * len(header))

    for d in range(1, 6):
        # Pure Minimax
        stats_mm = Stats()
        t0 = time.perf_counter()
        _minimax_no_pruning(board, d, 0, stats_mm, COLUMN_ORDER)
        t_mm = time.perf_counter() - t0

        # Alpha-Beta with Center-First ordering
        stats_ab = Stats()
        t0 = time.perf_counter()
        _alpha_beta_bench(board, d, -INF, INF, 0, stats_ab, COLUMN_ORDER)
        t_ab = time.perf_counter() - t0

        prune_pct = ((stats_mm.nodes - stats_ab.nodes) / stats_mm.nodes) * 100.0
        speedup = (t_mm / t_ab) if t_ab > 0 else 1.0

        print(
            f"k = {d:<2} | {stats_mm.nodes:<14,d} | {stats_ab.nodes:<12,d} | "
            f"{stats_ab.cutoffs:<8,d} | {prune_pct:>8.2f}% | "
            f"{t_mm*1000:>7.2f} ms | {t_ab*1000:>7.2f} ms | {speedup:>6.2f}x"
        )

    # 2. Move Ordering Impact: Center-First vs Sequential Order
    print("\n--- 2. MOVE ORDERING IMPACT ON ALPHA-BETA PRUNING ---")
    order_header = (
        f"{'Depth':<6} | {'Center-First (AB)':<18} | {'Sequential (AB)':<16} | "
        f"{'Nodes Saved':<12} | {'Efficiency Gain':<15}"
    )
    print(order_header)
    print("-" * len(order_header))

    for d in range(1, 7):
        stats_cf = Stats()
        t0 = time.perf_counter()
        _alpha_beta_bench(board, d, -INF, INF, 0, stats_cf, COLUMN_ORDER)
        t_cf = time.perf_counter() - t0

        stats_seq = Stats()
        t0 = time.perf_counter()
        _alpha_beta_bench(board, d, -INF, INF, 0, stats_seq, sequential_order)
        t_seq = time.perf_counter() - t0

        saved = stats_seq.nodes - stats_cf.nodes
        pct_gain = (saved / stats_seq.nodes) * 100.0 if stats_seq.nodes > 0 else 0.0

        print(
            f"k = {d:<2} | {stats_cf.nodes:>7,d} ({t_cf*1000:>6.1f}ms) | "
            f"{stats_seq.nodes:>7,d} ({t_seq*1000:>6.1f}ms) | "
            f"{saved:>10,d} | {pct_gain:>13.2f}%"
        )

    # 3. Midgame tactical position benchmark
    print("\n--- 3. MIDGAME TACTICAL SEARCH PERFORMANCE (14 Moves Played) ---")
    midgame = Board()
    # Play 14 strategic moves to set up a complex board
    moves = [3, 3, 2, 4, 3, 2, 4, 1, 3, 4, 2, 5, 1, 0]
    for m in moves:
        midgame.make_move(m)

    mid_header = f"{'Depth':<6} | {'Nodes':<10} | {'Leaves':<10} | {'Cutoffs':<9} | {'Time (ms)':<10} | {'Throughput (n/s)':<18}"
    print(mid_header)
    print("-" * len(mid_header))

    for d in range(1, 8):
        stats = Stats()
        t0 = time.perf_counter()
        _alpha_beta_bench(midgame, d, -INF, INF, midgame.player_to_move, stats, COLUMN_ORDER)
        dur = time.perf_counter() - t0
        nps = (stats.nodes / dur) if dur > 0 else 0

        print(
            f"k = {d:<2} | {stats.nodes:<10,d} | {stats.leaves:<10,d} | "
            f"{stats.cutoffs:<9,d} | {dur*1000:>8.2f}ms | {nps:>16,.0f} n/s"
        )

    print("\n" + "=" * 80)
    print("                      BENCHMARK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmark()
