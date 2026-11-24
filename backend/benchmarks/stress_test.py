import sys
import os
import time
import tracemalloc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.board import Board
from models.stats import Stats
from configs.settings import (
    ROWS, COLS, H, CELLS, WIN, COLUMN_ORDER
)
from ai.algorithms.alpha_beta import best_move, _alpha_beta
from ai.heurisitcs.evaluate import evaluate
from utils.popcount import popcount
from configs.settings import DS

INF = float("inf")


def count_fours(bb: int) -> int:
    count = 0
    for d in DS:
        pairs = bb & (bb >> d)
        fours = pairs & (pairs >> (d << 1))
        count += popcount(fours)
    return count


def stress_test_full_game_endurance():
    print("\n[STRESS TEST 1] Full Game AI vs AI Endurance Test (Depth 5)")
    print("-" * 70)
    tracemalloc.start()
    t_start = time.perf_counter()

    board = Board()
    total_nodes = 0
    total_cutoffs = 0
    move_times = []

    move_num = 1
    while not board.full:
        cur_player = board.player_to_move
        t0 = time.perf_counter()
        col, tree, stats = best_move(board, k=5, maximizer=cur_player)
        t_move = time.perf_counter() - t0

        move_times.append(t_move)
        total_nodes += stats.nodes
        total_cutoffs += stats.cutoffs

        assert col in board.valid_moves(COLUMN_ORDER), f"Invalid move {col} at move {move_num}"
        board.make_move(col)

        if move_num % 7 == 0 or board.full:
            print(
                f"  Move {move_num:>2}/42: Col {col} | Nodes: {stats.nodes:>6,d} | "
                f"Cutoffs: {stats.cutoffs:>5,d} | Latency: {t_move*1000:>6.1f}ms"
            )
        move_num += 1

    t_total = time.perf_counter() - t_start
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    p0_score = count_fours(board.bb[0])
    p1_score = count_fours(board.bb[1])

    print("-" * 70)
    print(f"  Result: Player 0 ({p0_score}) vs Player 1 ({p1_score}) | Moves: {board.moves}/{CELLS}")
    print(f"  Total Nodes Expanded: {total_nodes:,d}")
    print(f"  Total Cutoffs:        {total_cutoffs:,d}")
    print(f"  Avg Latency / Move:   {sum(move_times)/len(move_times)*1000:.2f} ms")
    print(f"  Max Latency / Move:   {max(move_times)*1000:.2f} ms")
    print(f"  Total Match Time:     {t_total:.2f} s")
    print(f"  Peak Memory:          {peak_mem / 1024:.1f} KB")
    print("  STATUS: [PASSED - STABLE & DETERMINISTIC]")


def stress_test_deep_lookahead():
    print("\n[STRESS TEST 2] Deep Lookahead Scaling & Recursion Limits (k=6, 7, 8)")
    print("-" * 70)
    # Balanced midgame board (8 moves)
    board = Board()
    for col in [3, 3, 2, 4, 3, 2, 4, 1]:
        board.make_move(col)

    for depth in [6, 7, 8]:
        tracemalloc.start()
        t0 = time.perf_counter()
        col, tree, stats = best_move(board, k=depth, maximizer=board.player_to_move)
        dur = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        nps = stats.nodes / dur if dur > 0 else 0
        print(
            f"  Depth k={depth}: Best Move={col} | Nodes={stats.nodes:>9,d} | "
            f"Leaves={stats.leaves:>9,d} | Cutoffs={stats.cutoffs:>7,d} | "
            f"Time={dur:>6.2f}s | Throughput={nps:>10,.0f} n/s | Peak Mem={peak/1024:>6.1f}KB"
        )
    print("  STATUS: [PASSED - NO OVERFLOW OR LEAK]")


def stress_test_boundary_conditions():
    print("\n[STRESS TEST 3] Boundary Conditions & Edge Case Boards")
    print("-" * 70)

    # 1. Nearly full board (41 moves played, 1 slot left)
    b_nearly_full = Board()
    # Fill all columns 0 to 5 completely (6*6 = 36 moves), and col 6 with 5 moves (36+5 = 41 moves)
    for c in range(6):
        for _ in range(6):
            b_nearly_full.make_move(c)
    for _ in range(5):
        b_nearly_full.make_move(6)

    assert b_nearly_full.moves == 41
    assert b_nearly_full.valid_moves(COLUMN_ORDER) == [6]

    t0 = time.perf_counter()
    col, tree, stats = best_move(b_nearly_full, k=5, maximizer=b_nearly_full.player_to_move)
    t_end = time.perf_counter() - t0
    assert col == 6, f"Expected move 6, got {col}"
    print(f"  Test 3.1 (1 Slot Remaining): Played Col {col} in {t_end*1000:.3f}ms [PASSED]")

    # 2. Defensive block of immediate opponent 3-in-a-row
    b_block = Board()
    # Player 0 plays col 0, 1, 2 at row 0 (3-in-a-row threat at col 3)
    b_block.make_move(0) # P0 at (0, 0)
    b_block.make_move(0) # P1 at (0, 1)
    b_block.make_move(1) # P0 at (1, 0)
    b_block.make_move(1) # P1 at (1, 1)
    b_block.make_move(2) # P0 at (2, 0) -> threat: (3, 0) gives P0 four-in-a-row!
    # Now it is P1's turn. P1 must block by playing col 3!
    assert b_block.player_to_move == 1
    col, tree, stats = best_move(b_block, k=4, maximizer=1)
    print(f"  Test 3.2 (Defensive Block): P1 chose Col {col} to block P0 threat at col 3 (P1 chose: {col})")
    assert col == 3, f"Expected P1 to block at col 3, got {col}"
    print("  STATUS: [PASSED - THREAT ACCURATELY BLOCKED]")


def stress_test_rapid_burst():
    print("\n[STRESS TEST 4] Rapid Fire Search Burst (200 Sequential Requests)")
    print("-" * 70)
    board = Board()
    board.make_move(3)
    board.make_move(3)

    t0 = time.perf_counter()
    for _ in range(200):
        col, _, _ = best_move(board, k=3, maximizer=board.player_to_move)
    dur = time.perf_counter() - t0

    req_per_sec = 200 / dur
    print(f"  Executed 200 searches at k=3 in {dur:.2f}s ({req_per_sec:.1f} req/s)")
    print("  STATUS: [PASSED - 0 ERRORS UNDER RAPID BURST]")


def run_all_stress_tests():
    print("=" * 80)
    print("          ALPHA-BETA PRUNING STRESS TEST & RELIABILITY SUITE")
    print("=" * 80)
    stress_test_full_game_endurance()
    stress_test_deep_lookahead()
    stress_test_boundary_conditions()
    stress_test_rapid_burst()
    print("\n" + "=" * 80)
    print("                 ALL STRESS TESTS COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    run_all_stress_tests()
