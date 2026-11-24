import time
from configs.settings import COLUMN_ORDER
from models.board import Board
from models.tree_node import TreeNode
from models.stats import Stats
from ai.heurisitcs.evaluate import evaluate

INF = float("inf")


def _alpha_beta(
    board: Board,
    node: TreeNode,
    depth: int,
    alpha: float,
    beta: float,
    maximizer: int,
    stats: Stats,
) -> float:
    stats.nodes += 1
    node.alpha, node.beta = alpha, beta

    moves = board.valid_moves(COLUMN_ORDER)

    if depth == 0 or not moves:
        stats.leaves += 1
        node.value, node.heuristic = evaluate(board, maximizer)
        node.is_leaf = True
        node.board = str(board.to_grid())
        return node.value

    maximizing = board.player_to_move == maximizer
    child_kind = "MIN" if maximizing else "MAX"
    best = -INF if maximizing else INF

    for i, col in enumerate(moves):
        child = TreeNode(depth=node.depth + 1, move=col, kind=child_kind)
        node.children.append(child)

        board.make_move(col)
        v = _alpha_beta(board, child, depth - 1, alpha, beta, maximizer, stats)
        board.undo(col)

        if maximizing:
            if v > best:
                best, node.best_move = v, col
            alpha = max(alpha, best)
        else:
            if v < best:
                best, node.best_move = v, col
            beta = min(beta, best)

        if alpha >= beta:
            stats.cutoffs += 1
            for skipped in moves[i + 1:]:
                node.children.append(
                    TreeNode(depth=node.depth + 1, move=skipped, kind=child_kind, pruned=True)
                )
            break

    node.value = best
    return best


def best_move(board: Board, k: int, maximizer: int) -> tuple[int, TreeNode, Stats]:
    root_kind = "MAX" if board.player_to_move == maximizer else "MIN"
    root = TreeNode(depth=0, move=None, kind=root_kind)
    stats = Stats()

    t0 = time.perf_counter()
    _alpha_beta(board, root, k, -INF, INF, maximizer, stats)
    stats.time = time.perf_counter() - t0

    return root.best_move, root, stats
