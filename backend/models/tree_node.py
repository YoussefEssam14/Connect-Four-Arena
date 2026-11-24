from dataclasses import dataclass, field

INF = float("inf")


@dataclass(slots=True)
class TreeNode:
    depth: int
    move: int | None
    kind: str
    alpha: float = -INF
    beta: float = INF
    value: float | None = None
    pruned: bool = False
    is_leaf: bool = False
    heuristic: dict | None = None
    board: str | None = None
    best_move: int | None = None
    children: list["TreeNode"] = field(default_factory=list)


def tree_to_dict(node: TreeNode, max_depth: int | None = None) -> dict:
    def serialize(x: float) -> float | str:
        return str(x) if x in (INF, -INF) else x

    return {
        "move": node.move,
        "kind": node.kind,
        "depth": node.depth,
        "alpha": serialize(node.alpha),
        "beta": serialize(node.beta),
        "value": serialize(node.value),
        "pruned": node.pruned,
        "is_leaf": node.is_leaf,
        "heuristic": node.heuristic,
        "board": node.board,
        "best_move": node.best_move,
        "children": (
            [tree_to_dict(c, max_depth) for c in node.children]
            if max_depth is None or node.depth < max_depth
            else []
        ),
    }
