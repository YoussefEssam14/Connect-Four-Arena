import sys
import os
import time

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
))


from models.board import Board
from configs.settings import COLUMN_ORDER, CELLS
from ai.algorithms.alpha_beta import best_move

from states import almost_full_boards
def test_full_game(max_search_depth: int = 5):
    print("\n[1] Full game stress test")
    print("-" * 90)

    board = Board()
    first_player = board.player_to_move

    total_nodes = 0
    total_time = 0
    total_pruned = 0

    while not board.full:
        player = board.player_to_move

        start = time.perf_counter()
        col, tree, stats = best_move(
            board,
            k=max_search_depth,
            maximizer=player
        )
        time_elapsed = time.perf_counter() - start

        valid_moves = board.valid_moves(COLUMN_ORDER)

        if col not in valid_moves:
            raise ValueError(
                f"Invalid move: {col}, "
                f"valid moves: {valid_moves}, "
                f"depth: {max_search_depth}"
            )

        board.make_move(col)

        total_nodes += stats.nodes
        total_time += time_elapsed
        total_pruned += stats.cutoffs

    print(f"Moves played         : {board.moves}/{CELLS}")
    print(f"Total expanded nodes : {total_nodes:,}")
    print(f"Total cutoffs        : {total_pruned:,}")
    print(f"Total time           : {total_time:.2f}s")
    print(f"Average move         : {total_time / board.moves * 1000:.2f}ms")

    print(f"First player score   : {board.count_fours(first_player)}")
    print(f"Second player score  : {board.count_fours(1-first_player)}")

    for row in board.to_grid():
        print(row)

    print("[PASSED]")
# for d in range(1,10):
#     print(f"Current depth : {d}")
#     test_full_game(d)

def test_nearly_full_board(max_search_depth: int = 5):

    print(f"\n[2] Nearly full board stress test | Depth {max_search_depth}")
    print("-" * 110)

    move_counts = [20 ,36, 38, 40, 41]

    total_nodes = 0
    total_cutoffs = 0
    total_time = 0

    passed = 0
    invalid = 0

    for i, sequence in enumerate(almost_full_boards):

        for move_count in move_counts:

            board = Board()

            # Reconstruct the position.
            valid_position = True

            for col in sequence[:move_count]:

                valid_moves = board.valid_moves(COLUMN_ORDER)

                if col not in valid_moves:
                    print(
                        f"Board {i + 1:02} | "
                        f"Moves {move_count} | INVALID POSITION"
                    )
                    invalid += 1
                    valid_position = False
                    break

                board.make_move(col)

            if not valid_position:
                continue

            valid_moves = board.valid_moves(COLUMN_ORDER)

            if not valid_moves:
                print(f"Board {i + 1:02} | No legal moves")
                invalid += 1
                continue

            moves_before = board.moves

            # Search.
            start = time.perf_counter()

            col, tree, stats = best_move(
                board,
                k=max_search_depth,
                maximizer=board.player_to_move
            )

            elapsed = time.perf_counter() - start

            # Validate the result.
            if board.moves != moves_before:
                raise RuntimeError("Search modified the original board!")

            if col not in valid_moves:
                raise ValueError(
                    f"Invalid AI move {col} "
                    f"on board {i + 1}"
                )

            total_nodes += stats.nodes
            total_cutoffs += stats.cutoffs
            total_time += elapsed

            passed += 1

            print(
                f"Board {i + 1:02} | "
                f"Moves {move_count:02} | "
                f"Nodes {stats.nodes:>9,} | "
                f"Cutoffs {stats.cutoffs:>8,} | "
                f"Time {elapsed * 1000:>9.3f} ms"
            )

    print("\nSUMMARY")
    print("-" * 90)

    print(f"Passed positions : {passed}")
    print(f"Invalid positions: {invalid}")

    if passed == 0:
        return

    print(f"Total nodes      : {total_nodes:,}")
    print(f"Total cutoffs    : {total_cutoffs:,}")
    print(f"Total time       : {total_time:.3f}s")

    print(f"Average nodes    : {total_nodes / passed:,.2f}")
    print(f"Average cutoffs  : {total_cutoffs / passed:,.2f}")
    print(f"Average time     : {total_time / passed * 1000:.3f}ms")

    if total_nodes:
        print(
            f"Cutoff rate      : "
            f"{total_cutoffs / total_nodes * 100:.2f}%"
        )

def ai_vs_ai_smart_vs_stupid(smart_depth:int,stupid_depth:int):
    print("\n[3] Full game stress test with smart agent vs stupid agent")
    print("-" * 90)

    board = Board()
    first_player = board.player_to_move

    total_nodes = 0
    total_time = 0
    total_pruned = 0

    while not board.full:
        player = board.player_to_move

        start = time.perf_counter()
        depth =  smart_depth if player == 0 else stupid_depth
        col, tree, stats = best_move(
            board,
            k=depth,
            maximizer=player
        )
        time_elapsed = time.perf_counter() - start

        valid_moves = board.valid_moves(COLUMN_ORDER)

        if col not in valid_moves:
            raise ValueError(
                f"Invalid move: {col}, "
                f"valid moves: {valid_moves}, "
                f"depth: {depth}"
            )

        board.make_move(col)

        total_nodes += stats.nodes
        total_time += time_elapsed
        total_pruned += stats.cutoffs

    print(f"Moves played         : {board.moves}/{CELLS}")
    print(f"Total expanded nodes : {total_nodes:,}")
    print(f"Total cutoffs        : {total_pruned:,}")
    print(f"Total time           : {total_time:.2f}s")
    print(f"Average move         : {total_time / board.moves * 1000:.2f}ms")

    print(f"First player score   : {board.count_fours(first_player)}")
    print(f"Second player score  : {board.count_fours(1-first_player)}")

    for row in board.to_grid():
        print(row)

    print("[PASSED]")
for d in range(1,9):
    test_nearly_full_board(d)

for d1 , d2 in [(7,1),(6,3),(5,2),(4,3),(9,4),(10,9),(9,7)]:
    ai_vs_ai_smart_vs_stupid(d1,d2)