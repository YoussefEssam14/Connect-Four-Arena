import sys
import os
import time
import random
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
))

from models.board import Board
from configs.settings import ROWS, COLS, H, WIN, COLUMN_ORDER, DS
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


# Custom heuristic evaluator
def evaluate_custom(
    board: Board,
    maximizer: int,
    p: HeuristicParams
) -> float:

    me = maximizer
    opp = 1 - maximizer

    mine = board.bb[me]
    theirs = board.bb[opp]

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

        elif k == 2:

            score += sign * p.TWO

    # Positional evaluation.
    positional = sum(
        p.COL_WEIGHT[c] * (
            (mine & _COL_MASKS[c]).bit_count()
            - (theirs & _COL_MASKS[c]).bit_count()
        )
        for c in range(COLS)
    )

    score += p.LAMBDA * positional

    # Final score when the board is full.
    if board.full:

        diff = fours[me] - fours[opp]

        if diff > 0:
            return WIN

        elif diff < 0:
            return -WIN

        return 0.0

    return score



def search_custom(
    board: Board,
    depth: int,
    alpha: float,
    beta: float,
    maximizer: int,
    p: HeuristicParams
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

            v, _ = search_custom(
                board,
                depth - 1,
                alpha,
                beta,
                maximizer,
                p
            )

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

            v, _ = search_custom(
                board,
                depth - 1,
                alpha,
                beta,
                maximizer,
                p
            )

            board.undo(col)

            if v < best_v:
                best_v = v
                best_move = col

            beta = min(beta, best_v)

            if alpha >= beta:
                break

        return best_v, best_move



def play_game(
    p0: HeuristicParams,
    p1: HeuristicParams,
    depth: int
) -> tuple[int, int, int]:

    board = Board()

    params = [p0, p1]

    while not board.full:

        cur = board.player_to_move

        _, col = search_custom(
            board,
            depth,
            -float("inf"),
            float("inf"),
            cur,
            params[cur]
        )

        if col is None:
            break

        board.make_move(col)

    s0 = count_fours(board.bb[0])
    s1 = count_fours(board.bb[1])

    return s0, s1, board.moves



def random_candidate(index: int) -> HeuristicParams:

    w0 = random.uniform(1, 5)
    w1 = random.uniform(1, 7)
    w2 = random.uniform(1, 10)
    w3 = random.uniform(1, 15)

    return HeuristicParams(
        name=f"Candidate-{index}",

        A=1000.0,

        THREE=random.uniform(70, 160),
        THREE_BURIED=random.uniform(0.2, 0.8),
        PARITY_BONUS=random.uniform(0, 120),
        TEMPO_BONUS=random.uniform(100, 600),
        TWO=random.uniform(5, 25),
        LAMBDA=random.uniform(0.2, 3.0),

        COL_WEIGHT=(w0, w1, w2, w3, w2, w1, w0)
    )



def evaluate_candidate(
    candidate: HeuristicParams,
    baseline: HeuristicParams,
    depth: int
) -> dict:

    start = time.perf_counter()

    # Game 1: Candidate plays as P0.
    c0, b0, moves1 = play_game(
        candidate,
        baseline,
        depth
    )

    # Game 2: Candidate plays as P1.
    b1, c1, moves2 = play_game(
        baseline,
        candidate,
        depth
    )

    elapsed = time.perf_counter() - start

    candidate_score = c0 + c1
    baseline_score = b0 + b1

    diff = candidate_score - baseline_score

    wins = int(c0 > b0) + int(c1 > b1)
    draws = int(c0 == b0) + int(c1 == b1)
    losses = int(c0 < b0) + int(c1 < b1)

    return {
        "params": candidate,
        "candidate_score": candidate_score,
        "baseline_score": baseline_score,
        "diff": diff,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "moves": moves1 + moves2,
        "time": elapsed
    }


def run_tuning():

    random.seed(42)

    baseline = HeuristicParams(name="Baseline")

    NUMBER_OF_CANDIDATES = 2000
    DEPTH = 4

    results = []

    print("=" * 90)
    print("                 HEURISTIC RANDOM SEARCH TUNER")
    print("=" * 90)

    print(f"Candidates : {NUMBER_OF_CANDIDATES}")
    print(f"Search depth: {DEPTH}")
    print("Games per candidate: 2")
    print("=" * 90)

    for i in range(1, NUMBER_OF_CANDIDATES + 1):

        candidate = random_candidate(i)

        print(f"\nTesting {candidate.name}...")

        result = evaluate_candidate(
            candidate,
            baseline,
            DEPTH
        )

        results.append(result)

        print(
            f"  Score: {result['candidate_score']} - "
            f"{result['baseline_score']} | "
            f"Diff: {result['diff']:+d} | "
            f"W/D/L: "
            f"{result['wins']}/"
            f"{result['draws']}/"
            f"{result['losses']} | "
            f"Time: {result['time']:.2f}s"
        )

    # Sort candidates by score difference.
    results.sort(
        key=lambda x: x["diff"],
        reverse=True
    )

    # Print ranking.
    print("\n" + "=" * 90)
    print("                         FINAL RANKING")
    print("=" * 90)

    print(
        f"{'Rank':<7}"
        f"{'Candidate':<18}"
        f"{'Score':<15}"
        f"{'Diff':<10}"
        f"{'W/D/L':<12}"
        f"{'Time':<10}"
    )

    print("-" * 90)

    for rank, result in enumerate(results, 1):

        score = (
            f"{result['candidate_score']} - "
            f"{result['baseline_score']}"
        )

        wdl = (
            f"{result['wins']}/"
            f"{result['draws']}/"
            f"{result['losses']}"
        )

        print(
            f"{rank:<7}"
            f"{result['params'].name:<18}"
            f"{score:<15}"
            f"{result['diff']:+<10}"
            f"{wdl:<12}"
            f"{result['time']:.2f}s"
        )

    # Best candidate.
    best = results[0]["params"]

    print("\n" + "=" * 90)
    print("                         BEST PARAMETERS")
    print("=" * 90)

    print(f"Name          : {best.name}")
    print(f"A             : {best.A:.2f}")
    print(f"THREE         : {best.THREE:.2f}")
    print(f"THREE_BURIED  : {best.THREE_BURIED:.3f}")
    print(f"PARITY_BONUS  : {best.PARITY_BONUS:.2f}")
    print(f"TEMPO_BONUS   : {best.TEMPO_BONUS:.2f}")
    print(f"TWO           : {best.TWO:.2f}")
    print(f"LAMBDA        : {best.LAMBDA:.3f}")
    print(f"COL_WEIGHT    : {best.COL_WEIGHT}")

    print("=" * 90)


run_tuning()