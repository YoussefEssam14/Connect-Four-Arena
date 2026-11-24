# Connect Four Arena — Theoretical, Algorithmic & Benchmark Q&A

This document covers the game theory, bitboard representation, Alpha-Beta Minimax search, heuristic design, parameter tuning, and benchmark results behind the Connect Four AI engine (excluding UI/frontend concerns).

---

## 1. Game Rules & Bitboard Representation

### Q1: How does Alexandria Connect Four differ from standard Connect Four?
In standard Connect Four, the game ends immediately as soon as either player forms a single 4-in-a-row.
In **Alexandria Connect Four** (implemented in `backend/models/board.py` and `backend/services/game_service.py`):
- **Board size**: 7 columns x 6 rows (`ROWS = 6`, `COLS = 7`, `CELLS = 42`).
- **Termination**: Play continues until **all 42 slots are filled** (`board.full` when `moves == 42`).
- **Scoring**: Every completed horizontal, vertical, or diagonal 4-in-a-row earns 1 point for that player. A single disc can contribute to multiple intersecting 4-in-a-row lines.
- **Winner**: At move 42, the player with more connected fours wins (`my_fours > ai_fours`). Equal counts result in a `"draw"`.

Because the game does not stop on the first 4-in-a-row, the AI cannot simply look for a forced win and stop; it must maximize the **net difference** in 4-in-a-row connections across the full 42-ply horizon while defending against the opponent creating multiple intersecting threats.

---

### Q2: Why represent the board as two 64-bit integers (bitboards) instead of a 2D list?
In `backend/models/board.py`, `Board` stores:
- `self.bb = [0, 0]` — two Python integers (`bb[0]` for `'R'`, `bb[1]` for `'Y'`).
- `self.heights = [0] * COLS` — the next free row index in each column.
- `self.moves = 0` — total plies played (`player_to_move` is `self.moves & 1`).

**Why this matters:**
1. **O(1) move & undo**: `make_move(col)` sets a single bit (`self.bb[player] |= 1 << (col * H + row)`), and `undo(col)` clears that bit (`&= ~(...)`). During Alpha-Beta search, thousands of nodes are explored per move without copying or allocating 2D arrays.
2. **O(1) 4-in-a-row detection**: Checking all 4-in-a-row lines for a player takes four bitwise shift-and-mask operations across `DS = [1, 7, 8, 6]` rather than nested loops over cells.
3. **O(1) window evaluation**: Checking how many discs each player has in a 4-cell window is a single `(mine & window).bit_count()`.

---

### Q3: Why is `H = 7` when the board only has `ROWS = 6` rows?
Each column uses **7 bits** (`H = 7`), where rows `0..5` hold actual discs and bit `6` of each column is an **unused sentinel bit** (always `0`).

Without this sentinel row, bit `5` of column `c` (top row) and bit `0` of column `c + 1` (bottom row) would be adjacent in memory (`c * 6 + 5` and `(c + 1) * 6 + 0`), causing horizontal or diagonal bit-shifts to falsely wrap around from the top of one column to the bottom of the next. With `H = 7`, the sentinel bit is always `0`, so shifts across column boundaries are automatically zeroed out.

Total bits used: `7 columns * 7 bits = 49 bits`, fitting comfortably in a 64-bit word. The direction strides in `DS = [1, H, H + 1, H - 1]` are:
- `1`: vertical (up 1 row)
- `7` (`H`): horizontal (right 1 column)
- `8` (`H + 1`): main diagonal (up 1 row, right 1 column)
- `6` (`H - 1`): anti-diagonal (down 1 row, right 1 column)

---

### Q4: How does `_count_fours(bb)` count all 4-in-a-row lines without loops over coordinates?
In `backend/services/game_service.py`:
```python
for d in DS:
    pairs = bb & (bb >> d)
    fours = pairs & (pairs >> (d << 1))
    count += popcount(fours)
```
For a given direction stride `d`:
1. `pairs = bb & (bb >> d)` marks every cell that has a friendly disc at `pos` and `pos + d` (a 2-in-a-row).
2. `fours = pairs & (pairs >> (d << 1))` marks every cell that has a friendly 2-in-a-row at `pos` and another at `pos + 2d` — which is an exact 4-in-a-row.
3. `popcount(fours)` counts the set bits, giving the exact number of 4-in-a-row windows in direction `d` (including overlapping 5-in-a-row or 6-in-a-row segments, which count as 2 or 3 distinct 4-in-a-row windows as required by Alexandria rules).

---

## 2. Minimax & Alpha-Beta Pruning

### Q5: How does the Alpha-Beta Minimax algorithm work in `backend/ai/algorithms/alpha_beta.py`?
Minimax assumes both players play optimally:
- **MAX** (`board.player_to_move == maximizer`) tries to **maximize** the evaluation score.
- **MIN** (`board.player_to_move != maximizer`) tries to **minimize** the evaluation score.

Alpha-Beta pruning maintains two bounds along the current search path:
- **`alpha`**: The highest score MAX is already guaranteed to achieve from an ancestor choice (initialized to `-inf`).
- **`beta`**: The lowest score MIN is already guaranteed to achieve from an ancestor choice (initialized to `+inf`).

At each node:
1. **Base case**: If `depth == 0` or no valid moves remain (`board.full`), evaluate the board via `evaluate(board, maximizer, include_info=False)` and return the score.
2. **Recursive step**: Iterate through `moves = board.valid_moves(COLUMN_ORDER)`:
   - Apply `board.make_move(col)`, recurse with `depth - 1`, then call `board.undo(col)`.
   - If maximizing: update `best = max(best, v)` and `alpha = max(alpha, best)`.
   - If minimizing: update `best = min(best, v)` and `beta = min(beta, best)`.
   - **Cutoff check**: If `alpha >= beta`, increment `stats.cutoffs` and `break` immediately — remaining sibling columns cannot change the parent's decision because the opponent already has a strictly better or equal alternative earlier in the tree.

---

### Q6: Why do some nodes in the search tree show `alpha = -inf` or `beta = +inf`?
`alpha` and `beta` are **search window bounds**, not node scores:
- The **root node** starts with `(-inf, +inf)` because no branches have been explored yet.
- The **first child** of the root inherits `(-inf, +inf)` because the root has not finished evaluating any sibling yet.
- Subsequent siblings inherit tightened bounds (for example, `alpha = 21, beta = inf` at MAX, or `alpha = -inf, beta = 21` at MIN) once earlier siblings return concrete values.
- A node's actual minimax evaluation is its `value` field, while `alpha` and `beta` record the pruning window.

---

### Q7: Why does move ordering (`COLUMN_ORDER = [3, 2, 4, 1, 5, 0, 6]`) matter so much for Alpha-Beta?
Alpha-Beta pruning returns the **exact same minimax value and best move** as full Minimax regardless of move order, but the **number of pruned nodes** depends heavily on exploring strong moves first:
- In Connect Four, center columns (`3`, then `2` and `4`) participate in far more 4-in-a-row windows than edge columns (`0` and `6`).
- Exploring `[3, 2, 4, 1, 5, 0, 6]` finds high-scoring lines early, tightening `alpha` (or `beta`) immediately so weaker edge-column branches trigger `alpha >= beta` cutoffs right away.
- In our benchmark on an empty board at `k = 6`, center-first ordering reduced searched nodes from **16,059** (sequential `[0..6]`) down to **1,408** — a **91.23% reduction**.

---

### Q8: Why is `MAX_SEARCH_DEPTH` set to `9` in `settings.py`?
Even with ~96.8% pruning, Minimax search grows exponentially with depth $k$.
- At `k = 3..5`, moves take under ~10 ms.
- At `k = 6..7` in midgame, search evaluates ~3,500–11,500 nodes in ~22–76 ms.
- At `k = 8..9`, lookahead remains interactive in Python (typically a fraction of a second to a few seconds depending on branching factor), whereas `k >= 10` can cause multi-second or timeout delays in a synchronous HTTP request.

Capping `MAX_SEARCH_DEPTH = 9` (and `MAX_K = 9`) keeps the API responsive while still offering deep tactical foresight.

---

## 3. Heuristic Evaluation Design

### Q9: Why precompute all 69 4-in-a-row windows in `build_windows.py`?
On a 7x6 board there are exactly **69** possible 4-in-a-row segments:
- Horizontal: `4 * 6 = 24`
- Vertical: `7 * 3 = 21`
- Main diagonal: `4 * 3 = 12`
- Anti-diagonal: `4 * 3 = 12`
- Total: `24 + 21 + 12 + 12 = 69` bitmasks, cached in `windows.json`.

Evaluating a board only requires iterating over these 69 integer masks. Any window containing discs from **both** players (`m and o`) is dead (blocked) and skipped immediately (`continue`).

---

### Q10: How does `evaluate()` score a board position?
In `backend/ai/heurisitcs/evaluate.py`, `score` combines **window threats** and **positional column weights**:

1. **Terminal full-board check (`board.full`)**:
   - `diff = fours[me] - fours[opp]`
   - Returns `WIN = 1,000,000` if `diff > 0`, `-1,000,000` if `diff < 0`, or `0.0` if tied.
2. **Completed 4-in-a-row (`k == 4`)**:
   - Adds `sign * A` (`A = 1000`), directly rewarding every completed four since Alexandria Connect Four is won by total 4-in-a-row count.
3. **Uncontested 3-in-a-row (`k == 3`, 1 empty cell)**:
   - Finds the empty cell's column `c` and row `r` via `empty_bit = window & ~occupied` and `divmod(empty_bit.bit_length() - 1, H)`.
   - Computes gravity distance `dist = r - board.heights[c]`:
     - **Immediate threat (`dist == 0`)**: Base value `THREE = 120`. If it is that player's turn (`to_move == owner`), adds `TEMPO_BONUS = 420` (total `540`) because they can complete the four on this move.
     - **Buried threat (`dist > 0`)**: Scaled down by `THREE_BURIED = 0.48` (`57.6`) because discs must be stacked underneath before it can be completed. Adds `PARITY_BONUS = 80` if `r % 2 == owner`.
4. **Uncontested 2-in-a-row (`k == 2`)**:
   - Adds `sign * TWO` (`TWO = 12`) to favor flexible developing patterns.
5. **Positional column control**:
   - `sum(COL_WEIGHT[c] * (mine_in_col - theirs_in_col))` with `COL_WEIGHT = [3, 4, 6, 9, 6, 4, 3]` and `LAMBDA = 1`.

---

### Q11: Why does `PARITY_BONUS` check `r % 2 == owner`?
In Connect Four, Player 0 (Red, first player) moves on **even plies** (`0, 2, 4, ...`) and naturally tends to claim **even-indexed rows** (`r = 0, 2, 4`, i.e., rows 1, 3, 5 in 1-based counting) when players alternate in the same column, while Player 1 (Yellow, second player) tends to control **odd-indexed rows** (`r = 1, 3, 5`).

A buried 3-in-a-row threat whose completing cell lies on a player's favorable parity row (`r % 2 == owner`) is structurally much easier to realize in an endgame zugzwang than one on the opponent's parity row, so `PARITY_BONUS = 80` rewards threats aligned with the player's parity.

---

### Q12: Why is `TEMPO_BONUS` gated on `dist == 0` AND `to_move == owner`?
If `dist == 0`, the empty cell is directly playable right now.
- If `to_move == owner`, that player can immediately claim the 4-in-a-row (`+A`) on this turn — worth `THREE + TEMPO_BONUS = 540`.
- If `to_move != owner`, the opponent is on move and can block that cell (or take an even better move), so the threat does not receive the tempo bonus.

---

## 4. Parameter Tuning

### Q13: How were the heuristic parameters tuned?
`backend/benchmarks/tune_heuristics.py` defines a head-to-head self-play tournament at search depth 4, alternating who plays Player 0 (Red) and Player 1 (Yellow) against a `Baseline` profile (`THREE=100, TEMPO_BONUS=300, PARITY_BONUS=60, THREE_BURIED=0.5, TWO=10, COL_WEIGHT=(3,4,5,7,5,4,3)`).

Three candidate profiles were tested:
- **Tactical-Aggressive**: `THREE=130, TEMPO_BONUS=450, PARITY_BONUS=75, THREE_BURIED=0.45, TWO=12, COL_WEIGHT=(2,4,7,10,7,4,2)`
- **Center-Dominance**: `THREE=110, TEMPO_BONUS=380, PARITY_BONUS=70, THREE_BURIED=0.50, TWO=15, COL_WEIGHT=(1,3,6,9,6,3,1)`
- **Balanced-Master**: `THREE=120, TEMPO_BONUS=420, PARITY_BONUS=80, THREE_BURIED=0.48, TWO=14, COL_WEIGHT=(2,4,6,9,6,4,2)`

In deterministic depth-4 self-play (`tune_heuristics.py`), both games of `Tactical-Aggressive` and `Balanced-Master` ended `0 - 0` against `Baseline` (strong defensive blocking), while `Center-Dominance` drew `0 - 0` as P0 and `2 - 2` as P1.

The final values adopted in `backend/configs/settings.py` combine the `Balanced-Master` tactical ratios (`A=1000, THREE=120, TEMPO_BONUS=420, PARITY_BONUS=80, THREE_BURIED=0.48`) with `TWO=12` and slightly firmer wing/center weights `COL_WEIGHT = [3, 4, 6, 9, 6, 4, 3]` to avoid neglecting columns 0 and 6 in Alexandria full-board scoring.

---

## 5. Benchmarks & Stress Tests

### Q14: What did `benchmark_alpha_beta.py` measure on this codebase?
Observed output running `backend/.venv/bin/python benchmarks/benchmark_alpha_beta.py` (Python 3.14.4):

#### 1. Minimax vs. Alpha-Beta Scaling (Empty Board, `COLUMN_ORDER = [3, 2, 4, 1, 5, 0, 6]`)
| Depth | Minimax Nodes | Alpha-Beta Nodes | Cutoffs | Pruned % | Minimax Time | AB Time | Speedup |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `k = 1` | 8 | 8 | 0 | 0.00% | 0.10 ms | 0.06 ms | 1.73x |
| `k = 2` | 57 | 24 | 6 | 57.89% | 0.43 ms | 0.13 ms | 3.31x |
| `k = 3` | 400 | 76 | 12 | 81.00% | 2.59 ms | 0.41 ms | 6.30x |
| `k = 4` | 2,801 | 173 | 60 | 93.82% | 20.51 ms | 0.87 ms | 23.55x |
| `k = 5` | 19,608 | 628 | 113 | 96.80% | 137.71 ms | 3.69 ms | 37.27x |

#### 2. Move Ordering Impact (Center-First vs. Sequential `[0..6]`)
| Depth | Center-First Nodes (Time) | Sequential Nodes (Time) | Nodes Saved | Efficiency Gain |
| :--- | ---: | ---: | ---: | ---: |
| `k = 1` | 8 (0.1 ms) | 8 (0.0 ms) | 0 | 0.00% |
| `k = 2` | 24 (0.1 ms) | 46 (0.3 ms) | 22 | 47.83% |
| `k = 3` | 76 (0.4 ms) | 177 (1.0 ms) | 101 | 57.06% |
| `k = 4` | 173 (0.8 ms) | 947 (5.6 ms) | 774 | 81.73% |
| `k = 5` | 628 (3.7 ms) | 4,800 (29.5 ms) | 4,172 | 86.92% |
| `k = 6` | 1,408 (7.5 ms) | 16,059 (98.4 ms) | 14,651 | 91.23% |

#### 3. Midgame Tactical Search (14 Moves Played)
| Depth | Nodes | Leaves | Cutoffs | Time (ms) | Throughput |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `k = 1` | 8 | 7 | 0 | 0.08 ms | 104,053 n/s |
| `k = 2` | 35 | 27 | 4 | 0.27 ms | 131,941 n/s |
| `k = 3` | 99 | 70 | 18 | 0.68 ms | 146,128 n/s |
| `k = 4` | 316 | 212 | 75 | 2.01 ms | 157,195 n/s |
| `k = 5` | 1,242 | 880 | 240 | 8.34 ms | 148,858 n/s |
| `k = 6` | 3,566 | 2,333 | 883 | 22.33 ms | 159,704 n/s |
| `k = 7` | 11,487 | 8,029 | 2,278 | 76.19 ms | 150,767 n/s |

---

### Q15: What does `stress_test.py` validate?
`backend/benchmarks/stress_test.py` tests four reliability properties:
1. **Full-game AI vs. AI endurance (`k = 5`, 42 moves)**: Verifies all 42 plies are legal, deterministic, and bounded in memory using `tracemalloc`.
2. **Deep lookahead scaling (`k = 6, 7, 8`)**: Verifies recursion stability and memory footprint without stack overflow or leaks.
3. **Boundary conditions**:
   - 41-move board with 1 slot remaining (`valid_moves == [6]`).
   - Immediate defensive block: P0 threatens `(3, 0)` after playing columns `0, 1, 2`; P1 at `k = 4` must choose column `3`.
4. **Rapid-burst throughput**: Runs 200 sequential `best_move` searches at `k = 3` to confirm zero state corruption across repeated calls.

---

## 6. Backend Architecture & History Integrity

### Q16: Why does `GameService` record `ply: 0` and separate human/AI snapshots on the backend?
A single `POST /game/move` request executes the human's move and then (if the game is not over) runs the AI's Minimax search and executes the AI's reply. If the API only returned the final board after both moves, the intermediate board after the human's ply would be lost — and trying to guess it on the client would fail or misattribute scores/winning lines.

Therefore, `GameService` (`backend/services/game_service.py`) records:
- `ply: 0` (`actor: "initial"`) in `__init__` with the empty 6x7 grid.
- `ply: 1..N` via `_record_ply()` immediately after each `board.make_move(...)`:
  - Human plies store the exact intermediate `grid`, `human_score`, `ai_score`, and `evidence: None`.
  - AI plies store the exact post-AI `grid`, scores, and `evidence` (`role`, `value`, `alpha`, `beta`, `best_move`, `pruned`, `cutoffs`).

### Q17: Why is Red (`'R'`) always Player 0 in the bitboard even if the human picks Yellow (`'Y'`)?
In `GameService.__init__`:
- `Board(symbols=["R", "Y"])` assigns index `0` to `'R'` and index `1` to `'Y'`.
- `player_to_move` is `self.moves & 1`, so `'R'` always moves on even plies (starting at ply 0) and `'Y'` always moves on odd plies.
- If the human chooses `'Y'` (`human_idx = 1`, `ai_idx = 0`), `is_human_turn` is initially `False`, so `GameService.__init__` immediately calls `self._run_ai()` for `'R'`'s opening move (recorded as `ply: 1` right after `ply: 0`).

---

## 7. Additional Theoretical, Edge-Case & Assignment Questions

### Q18: Why is the full Connect Four game tree $O(10^{35})$ and why is depth-limited heuristic pruning (`k`) required?
With 7 columns and 42 total plies, a naive upper bound on the game tree size is $b^d \approx 7^{42} \approx 3.1 \times 10^{35}$ states (with roughly $4.5 \times 10^{12}$ unique reachable board positions). Even with fast bitboard operations at ~150,000 nodes/second, traversing to terminal states from the opening move would take longer than the age of the universe.

Truncating the search at depth `k` and applying `evaluate(board, maximizer)` at the frontier reduces the worst-case time complexity from $O(b^{42})$ to $O(b^k)$ — and with Alpha-Beta pruning and good move ordering, closer to $O(b^{k/2})$ in the best case.

---

### Q19: How does `evaluate()` guarantee that larger values favor the AI and smaller values favor the human?
In `backend/ai/heurisitcs/evaluate.py`, `maximizer` is always passed as `self.ai_idx` (`0` if AI is Red, `1` if AI is Yellow):
- `me, opp = maximizer, 1 - maximizer`
- Every window owned by `me` (AI) gets `sign = +1`.
- Every window owned by `opp` (Human) gets `sign = -1`.
- Positional column control is computed as `(mine & _COL_MASKS[c]).bit_count() - (theirs & _COL_MASKS[c]).bit_count()`.
- At a full board (`board.full`), `diff = fours[me] - fours[opp]` returns `+WIN` (`+1,000,000`) when AI has more fours, `-WIN` (`-1,000,000`) when Human has more fours, and `0.0` on a draw.

Thus, the heuristic is strictly zero-sum from the AI's perspective: larger positive scores mean the AI is ahead, and smaller (more negative) scores mean the human is ahead.

---

### Q20: Why does `_alpha_beta` use `alpha >= beta` instead of `alpha > beta`?
When `alpha == beta`, the maximizer already has a guaranteed alternative of score `alpha`, and the minimizer can already hold the current branch to at most `beta = alpha`. Even if the remaining sibling moves in this branch could somehow improve the minimizer's score further (making it `< alpha`), the maximizer will never choose this branch over the `alpha` branch it already found. Conversely, if a sibling doesn't improve it, it is at best `alpha`, which only ties the existing option. Pruning on `alpha >= beta` ("fail-hard / fail-soft" standard cutoff) eliminates redundant tie-exploration without changing the minimax value.

---

### Q21: How are ties between equally scored columns broken?
In `_alpha_beta` (`backend/ai/algorithms/alpha_beta.py`):
- `moves = board.valid_moves(COLUMN_ORDER)` orders candidate moves as `[3, 2, 4, 1, 5, 0, 6]`.
- `best_move_col = moves[0]` initializes the choice to the first valid move in center-first order.
- Updates use strict inequality: `if v > best:` (MAX) and `if v < best:` (MIN).

Because strict `>` / `<` only replaces `best_move_col` on a strictly better score, ties automatically resolve in favor of the **most central** column in `COLUMN_ORDER`, which is strategically stronger in Connect Four.

---

### Q22: What is the "horizon effect" at depth `k`, and how do odd vs. even `k` values differ?
Depth-limited search cannot see threats or forced sequences beyond `k` plies (the "horizon"):
- **Odd `k` (e.g. `k = 1, 3, 5`)**: The leaf nodes are evaluated right after a **MAX (AI)** move, meaning `to_move` at the leaf is the **opponent (MIN)**. If the AI leaves an immediate threat, the opponent's reply is just beyond the horizon (partially mitigated by `TEMPO_BONUS` checking `to_move == owner`).
- **Even `k` (e.g. `k = 2, 4, 6`)**: The leaf nodes are evaluated right after a **MIN (Human)** move, so `to_move` at the leaf is **MAX (AI)**.

Higher `k` pushes the horizon further away so tactical traps and multi-move combinations are resolved inside the search tree rather than approximated by the heuristic.

---

### Q23: Why does `evaluate()` have an `include_info: bool = True` flag?
Building the diagnostic `info` dictionary (`fours_me`, `fours_opp`, `threes_me`, `threes_opp`, `twos_me`, `twos_opp`, `positional`, `score`) allocates a Python `dict` on every call. During Alpha-Beta search (`_alpha_beta`), `evaluate()` is called at every leaf node (potentially tens of thousands of times per move), so passing `include_info=False` avoids unnecessary dictionary allocations in the hot path while keeping detailed breakdowns available for debugging, tests, and inspection.

---

### Q24: Why does `best_move()` default `max_record_depth = k`?
Originally `max_record_depth` defaulted to `4`, which meant searches at `k = 5..9` still computed the full tree but truncated the recorded `TreeNode` children below depth 4. Setting `max_record_depth = k` when `None` ensures the recorded tree matches the full search depth `k`, while the API endpoint `/game/tree?max_depth=...` lets callers request a smaller slice (from `0` up to `MAX_SEARCH_DEPTH = 9`) without re-running the search.

---

### Q25: What is the space complexity of Alpha-Beta Minimax in this implementation?
The search recursion stack itself uses **$O(k)$** space:
- Because `Board.make_move(col)` and `Board.undo(col)` mutate a single `Board` instance in place, **zero** board copies are allocated during search.
- When `TreeNode` recording is enabled up to `max_record_depth = k`, memory is proportional to the number of visited nodes $O(N_{\text{visited}})$ (typically a few hundred KB to a few MB depending on `k`).

---

### Q26: Why were transposition tables or iterative deepening not used for `k <= 9`?
- With a 64-bit bitboard + `COLUMN_ORDER` pruning ~96.8% of nodes at `k = 5`, searches up to `k = 7` finish in under ~80 ms in pure Python without needing a Zobrist hash table or time-budgeted iterative deepening.
- For `k >= 10` or strict wall-clock time limits, adding **iterative deepening** (using the previous depth's best move first) and a **Zobrist transposition table** (caching `(bb[0], bb[1], depth)` evaluations) would be the natural next optimization.

---

### Q27: What happens in the endgame when fewer than `k` empty cells remain?
In `_alpha_beta`:
`if depth == 0 or not moves:`
When `board.full` becomes `True` (`moves == []`) before `depth` reaches `0`, the search hits the exact terminal state and `evaluate()` enters `if board.full:`, returning `WIN` (`+1,000,000`), `-WIN` (`-1,000,000`), or `0.0`. Thus, in the final `k` plies of the match, Alpha-Beta solves the endgame **exactly** with zero heuristic approximation.

---

### Q28: Why does the backend define explicit domain exceptions (`FullColumnException`, `OutOfBoundsException`, `GameOverException`, `NotCurrentPlayerMoveException`, `NoActiveGameException`)?
Separating domain errors (`backend/exceptions/exception.py`) from HTTP handling (`backend/apis/api.py`) keeps `Board` and `GameService` framework-agnostic:
- `Board` and `GameService` can be unit-tested or driven from a CLI without FastAPI.
- The API layer maps `_CLIENT_ERRORS` uniformly in `_guard()` to HTTP `400 Bad Request` with clear error messages, while keeping Pydantic schema validation errors (e.g. `column: 99`) as HTTP `422 Unprocessable Entity`.

---

## 8. Deep-Dive Algorithm & Heuristic Questions

### Q29: Why does `_alpha_beta` determine `maximizing` via `board.player_to_move == maximizer` instead of passing a boolean flag?
`Board.player_to_move` is already maintained in $O(1)$ as `self.moves & 1` (`0` on even plies, `1` on odd plies) and automatically flips on every `make_move(col)` and `undo(col)`. Deriving `maximizing = board.player_to_move == maximizer` from the board itself guarantees the search role can never drift out of sync with the board state.

---

### Q30: What is the difference between a beta cutoff and an alpha cutoff?
Both are triggered by the same condition `if alpha >= beta: break`, but they happen at opposite node types:
- **Beta cutoff (at a MAX node)**: MAX finds a move whose value `v >= beta`. Since the parent MIN node already has an alternative with score `beta`, MIN will never allow MAX to reach this node — so MAX stops checking remaining siblings.
- **Alpha cutoff (at a MIN node)**: MIN finds a move whose value `v <= alpha`. Since the parent MAX node already has an alternative with score `alpha`, MAX will never enter this branch — so MIN stops checking remaining siblings.

---

### Q31: Why does MAX only update `alpha` and MIN only update `beta`?
- `alpha` represents the **best guaranteed lower bound for MAX** along the current path. Only MAX chooses moves that raise its minimum guarantee (`alpha = max(alpha, best)`).
- `beta` represents the **best guaranteed upper bound for MIN** along the current path. Only MIN chooses moves that lower its maximum concession (`beta = min(beta, best)`).

Updating `beta` inside a MAX node or `alpha` inside a MIN node would corrupt the opponent's guarantee and cause unsound pruning.

---

### Q32: Can Alpha-Beta pruning ever change the optimal move or minimax value compared to full Minimax?
No. Assuming a deterministic evaluation function and identical tie-breaking order (`COLUMN_ORDER`), Alpha-Beta pruning is **mathematically equivalent** to full Minimax: every pruned subtree is provably unable to influence the root's minimax value. Only the number of visited nodes and runtime change.

---

### Q33: Why does `k = 1` have `0` cutoffs (`0.00%` pruned) in the benchmark?
A cutoff requires at least **two plies** of interaction: a parent bound established by an earlier sibling, and a child node comparing its own children against that parent bound. At `k = 1`, the root simply evaluates all 7 immediate leaf boards directly — there are no deeper grandchildren to prune, so Minimax and Alpha-Beta both visit the exact same `8` nodes (1 root + 7 leaves).

---

### Q34: Why does `evaluate()` ignore windows with `k == 1` (1 friendly disc and 3 empty cells)?
A window with 1 disc and 3 empty cells is too weak and noisy to indicate a real threat — almost any disc on the board participates in several 1-of-4 windows. Instead of scoring `k == 1` per window, `evaluate()` captures early-game disc placement cleanly and faster via the `COL_WEIGHT = [3, 4, 6, 9, 6, 4, 3]` positional term.

---

### Q35: Why is `A = 1000` (completed 4-in-a-row) much larger than `THREE + TEMPO_BONUS = 540` and `TWO = 12`?
This strict weight hierarchy enforces tactical priority:
- **Completed 4 (`1000`) > Immediate 3-with-tempo (`540`) > Uncontested 3 (`120`) > Buried 3 (`57.6`, or `137.6` with parity) > Open 2 (`12`) > Column weight (`3..9`)**.
- Without `A >> THREE + TEMPO_BONUS`, the AI could mistakenly trade away an already-completed 4-in-a-row (or miss taking one) in favor of setting up two speculative 3-in-a-row threats.

---

### Q36: How does `evaluate()` find the exact missing cell of a 3-in-a-row in $O(1)$?
When `k == 3` in a 4-cell `window`:
1. `empty_bit = window & ~occupied` isolates the single bit that is `1` in `window` and `0` in `occupied` (since 3 of the 4 bits are occupied).
2. `idx = empty_bit.bit_length() - 1` converts that power-of-two bitmask directly to its integer bit index.
3. `c, r = divmod(idx, H)` recovers the exact column `c` and row `r` (because bit index = `c * H + r`), allowing `dist = r - board.heights[c]` to check whether the threat is immediately playable (`dist == 0`) or buried (`dist > 0`).

---

### Q37: Why is `if board.full:` checked at the end of `evaluate()` rather than at the top?
`fours[me]` and `fours[opp]` are already accumulated during the single pass over the 69 `WINDOWS` (`if k == 4: fours[owner] += 1`). Checking `if board.full:` right after the loop reuses those exact `fours` counts to compute `diff = fours[me] - fours[opp]` and return `WIN`, `-WIN`, or `0.0` without running `_count_fours()` a second time.

---

### Q38: What is the purpose of `LAMBDA = 1` in `score += LAMBDA * positional`?
`LAMBDA` is the global scaling factor between **tactical window threats** (`A`, `THREE`, `TWO`) and **positional column control** (`COL_WEIGHT`). Keeping `LAMBDA` as an explicit parameter in `settings.py` lets you dial positional gravity up or down relative to tactical threats during tuning without rewriting `COL_WEIGHT`.

---

### Q39: Why can a single disc be counted in multiple `WINDOWS` in `evaluate()`?
That is intentional: in Connect Four (and especially in Alexandria Connect Four where all 4-in-a-rows are scored), a central disc that simultaneously participates in a horizontal, vertical, and two diagonal 3-in-a-row threats creates **forks** (double threats) that cannot all be blocked in a single turn. Scoring each of the 69 windows independently naturally rewards multi-directional forks.

---

### Q40: What happens when `board.full` is tied (`fours[me] == fours[opp]`) vs. when an intermediate leaf has `score == 0.0`?
- At `board.full` with `fours[me] == fours[opp]`, `evaluate()` returns `0.0` (exact game-theoretic draw — neither `WIN` nor `-WIN`), ignoring positional `COL_WEIGHT` because positional advantage no longer matters once no moves remain.
- At a non-terminal leaf (`depth == 0` with empty cells remaining), `score == 0.0` simply means the AI's and human's heuristic threats and positional weights currently balance out.
