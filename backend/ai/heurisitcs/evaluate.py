from ai.heurisitcs.build_windows import WINDOWS
from configs.settings import (
    ROWS, COLS, H,
    WIN, A, TWO, THREE, THREE_BURIED,
    PARITY_BONUS, TEMPO_BONUS, LAMBDA, COL_WEIGHT,
)
from models.board import Board

_COL_MASKS = [
    sum(1 << (c * H + r) for r in range(ROWS))
    for c in range(COLS)
]


def evaluate(board: Board, maximizer: int, include_info: bool = True) -> tuple[float, dict]:
    me, opp = maximizer, 1 - maximizer
    mine, theirs = board.bb[me], board.bb[opp]
    occupied = mine | theirs
    to_move = board.player_to_move

    fours = [0, 0]
    threes = [0, 0]
    twos = [0, 0]
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
            score += sign * A

        elif k == 3:
            threes[owner] += 1
            empty_bit = window & ~occupied
            idx = empty_bit.bit_length() - 1
            c, r = divmod(idx, H)
            dist = r - board.heights[c]

            val = THREE
            if dist == 0:
                if to_move == owner:
                    val += TEMPO_BONUS
            else:
                val *= THREE_BURIED
                if r % 2 == owner:
                    val += PARITY_BONUS

            score += sign * val

        elif k == 2:
            twos[owner] += 1
            score += sign * TWO

    positional = sum(
        COL_WEIGHT[c] * (
            (mine & _COL_MASKS[c]).bit_count() -
            (theirs & _COL_MASKS[c]).bit_count()
        )
        for c in range(COLS)
    )
    score += LAMBDA * positional

    if board.full:
        diff = fours[me] - fours[opp]
        score = WIN if diff > 0 else -WIN if diff < 0 else 0.0

    info = (
        {
            "fours_me": fours[me],
            "fours_opp": fours[opp],
            "threes_me": threes[me],
            "threes_opp": threes[opp],
            "twos_me": twos[me],
            "twos_opp": twos[opp],
            "positional": positional,
            "score": score,
            **({"terminal": True} if board.full else {}),
        }
        if include_info
        else {}
    )

    return score, info
