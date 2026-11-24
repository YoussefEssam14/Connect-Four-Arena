import time
from configs.settings import COLUMN_ORDER
from models.board import Board
from models.tree_node import INF, TreeNode
from models.stats import Stats
from ai.heurisitcs.evaluate import evaluate


def _alpha_beta(
    board: Board,
    node: TreeNode | None,
    depth: int,
    alpha: float,
    beta: float,
    maximizer: int,
    stats: Stats,
    max_record_depth: int = 4,
) -> float:
    stats.nodes += 1
    if node is not None:
        node.alpha, node.beta = alpha, beta

    moves = board.valid_moves(COLUMN_ORDER)

    if depth == 0 or not moves:
        stats.leaves += 1
        score, _ = evaluate(board, maximizer, include_info=False)
        if node is not None:
            node.value = score
            node.is_leaf = True
        return score

    maximizing = board.player_to_move == maximizer
    child_kind = "MIN" if maximizing else "MAX"
    best = -INF if maximizing else INF
    best_move_col = moves[0]

    record_children = node is not None and node.depth < max_record_depth

    for i, col in enumerate(moves):
        child = None
        if record_children:
            child = TreeNode(depth=node.depth + 1, move=col, kind=child_kind)
            node.children.append(child)

        board.make_move(col)
        v = _alpha_beta(board, child, depth - 1, alpha, beta, maximizer, stats, max_record_depth)
        board.undo(col)

        if maximizing:
            if v > best:
                best, best_move_col = v, col
            alpha = max(alpha, best)
        else:
            if v < best:
                best, best_move_col = v, col
            beta = min(beta, best)

        if alpha >= beta:
            stats.cutoffs += 1
            if record_children:
                for skipped in moves[i + 1:]:
                    node.children.append(
                        TreeNode(depth=node.depth + 1, move=skipped, kind=child_kind, pruned=True)
                    )
            break

    if node is not None:
        node.value = best
        node.best_move = best_move_col
        node.alpha = alpha
        node.beta = beta
    return best


def best_move(
    board: Board,
    k: int,
    maximizer: int,
    max_record_depth: int | None = None,
) -> tuple[int | None, TreeNode, Stats]:
    root_kind = "MAX" if board.player_to_move == maximizer else "MIN"
    root = TreeNode(depth=0, move=None, kind=root_kind)
    stats = Stats()

    if max_record_depth is None:
        max_record_depth = k

    t0 = time.perf_counter()
    _alpha_beta(board, root, k, -INF, INF, maximizer, stats, max_record_depth=max_record_depth)
    stats.time = time.perf_counter() - t0

    return root.best_move, root, stats
