from dataclasses import dataclass


@dataclass
class Stats:
    nodes: int = 0
    leaves: int = 0
    cutoffs: int = 0
    time: float = 0.0
