# Connect Four Arena

A Connect Four game where a human plays against a Minimax AI with Alpha-Beta pruning.
Built with a Python/FastAPI backend and an Angular frontend using a Death Note-inspired dark theme.

---

## Project structure

```
connect-four-arena2/
├── backend/
│   ├── ai/
│   │   ├── algorithms/alpha_beta.py   # Minimax + alpha-beta
│   │   └── heurisitcs/
│   │       ├── evaluate.py            # Heuristic scoring
│   │       └── build_windows.py       # Pre-computed 4-cell windows
│   ├── apis/api.py                    # FastAPI router
│   ├── benchmarks/
│   │   ├── benchmark_alpha_beta.py    # Minimax vs AB scaling table
│   │   ├── stress_test.py             # Full-game and near-full endurance
│   │   ├── tune_heuristics.py         # Random-search weight tuner
│   │   └── states.py                  # Hard-state and near-full fixtures
│   ├── configs/settings.py            # All tunable constants
│   ├── dtos/schemas.py                # Pydantic request/response models
│   ├── exceptions/exception.py
│   ├── models/
│   │   ├── board.py                   # Bitboard engine
│   │   ├── stats.py                   # nodes / leaves / cutoffs / time
│   │   ├── tree_node.py               # Tree node + tree_to_dict
│   │   └── color.py
│   ├── services/game_service.py       # Session logic, score tracking
│   ├── utils/popcount.py
│   └── main.py                        # FastAPI app entry point
└── frontend/
    └── src/
        ├── app/
        │   ├── board/                 # Game board component
        │   ├── setup/                 # K depth + colour picker
        │   ├── tree-view/             # Scrollable minimax tree
        │   ├── app.ts                 # Root component + Web Audio
        │   ├── game-api.ts            # HTTP client wrapper
        │   └── models.ts              # TypeScript interfaces
        └── styles.css                 # Death Note CSS variables + animations
```

---

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m main          # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm start                # http://localhost:4200  (proxies /game → :8000)
```

---

## How to play

1. Pick **K** (search depth 1–9) and your colour (Red moves first).
2. Click a column to drop a piece. The AI responds immediately.
3. The board fills until every cell is occupied. The player with the most connected-fours wins.

---

## AI — Minimax with Alpha-Beta pruning

### Algorithm

Each turn the AI runs `best_move(board, k, maximizer)`:

1. Build a game tree to depth **K**.
2. Evaluate leaf nodes with the heuristic (see below).
3. Alpha-beta pruning skips subtrees that cannot change the root value.
4. Central columns are searched first (`COLUMN_ORDER = [3,2,4,1,5,0,6]`) to maximise early cutoffs.

### Heuristic

Every 4-cell window on the board is pre-computed at startup (`build_windows.py`).
During evaluation each window is classified:

| Pieces | Score contribution |
|--------|-------------------|
| 4 mine, 0 opp | `+A` (completed four — permanent point) |
| 3 mine, 0 opp | `+THREE`, adjusted by `THREE_BURIED` if the empty cell isn't playable yet, and by `TEMPO_BONUS` if it is playable and it is my turn |
| 2 mine, 0 opp | `+TWO` |
| 3 opp, 0 mine | `−THREE` (mirror) |
| Mixed | 0 (dead window) |

A positional bonus (`LAMBDA × COL_WEIGHT[c]`) rewards column centrality.
On a full board the terminal score is `±WIN` based on four-count difference.

### Tuned weights (current `settings.py`)

Weights were found by running `tune_heuristics.py` (random-search over ~5 000 candidates,
each evaluated by an AI-vs-AI match count).

| Constant | Value | Notes |
|----------|-------|-------|
| `WIN` | 1 000 000 | Terminal win/loss |
| `A` | 1 000 | Completed four |
| `THREE` | 100.63 | Three-in-a-row |
| `THREE_BURIED` | 0.73 | Multiplier when empty cell isn't yet reachable |
| `PARITY_BONUS` | 84.14 | Buried threat on a row the player naturally reaches |
| `TEMPO_BONUS` | 238.13 | Immediate threat on the player's own turn |
| `TWO` | 5.20 | Two-in-a-row |
| `LAMBDA` | 2.86 | Positional weight scale |
| `COL_WEIGHT` | `[4.4, 2.1, 2.9, 12.2, 2.9, 2.1, 4.4]` | Per-column positional bias |

### Expected performance by depth

| K | Typical nodes | Cutoff rate | Avg time |
|---|--------------|-------------|----------|
| 1 | ~7 | — | < 1 ms |
| 2 | ~50 | ~40 % | < 5 ms |
| 3 | ~400 | ~60 % | ~50 ms |
| 4 | ~3 000 | ~70 % | ~300 ms |
| 5 | ~20 000 | ~75 % | ~1–2 s |
| 7 | ~200 000 | ~80 % | ~10 s |
| 9 | ~2 000 000 | ~83 % | > 60 s |

---

## API

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/game/new` | `{k, human_color}` | Start a new game; AI moves first if human picked Yellow |
| `POST` | `/game/move` | `{column}` | Drop human piece, AI responds in the same call |
| `GET` | `/game` | — | Current board snapshot |
| `GET` | `/game/tree?max_depth=N` | — | Minimax tree from last AI move, capped at N levels |

`max_depth` on the tree endpoint is bounded by `MAX_SEARCH_DEPTH` (currently **9**) in `settings.py`,
not hard-coded to 6.

### Response shape (`GameState`)

```jsonc
{
  "k": 3,
  "grid": [[".", ".", ...], ...],   // 6 rows × 7 cols, "R" / "Y" / "."
  "human_score": 1,
  "ai_score": 2,
  "human_color": "R",
  "ai_color": "Y",
  "winner": null,                   // "R" | "Y" | "draw" | null
  "is_game_over": false,
  "is_human_turn": true,
  "ai_column": 3,                   // last column the AI played
  "stats": {
    "nodes": 412,
    "leaves": 118,
    "cutoffs": 247,
    "time": 0.048                   // seconds
  }
}
```

---

## Benchmarks

All scripts live in `backend/benchmarks/` and must be run from that directory
(they insert `..` into `sys.path` automatically).

### `benchmark_alpha_beta.py`

Compares pure Minimax against Alpha-Beta on an empty board (depths 1–5), then
on the 20 hard mid-game positions from `states.py` at depth 12.
Prints nodes, cutoffs, and wall-clock time for every row.

```bash
cd backend/benchmarks
python3 benchmark_alpha_beta.py
```

### `stress_test.py`

Two test suites:

- **Full-game endurance** — runs AI-vs-AI at a chosen depth until the board fills,
  then reports total nodes, cutoffs, total time, average ms/move, and both scores.
- **Near-full board** — replays the 20 `almost_full_boards` from `states.py` and
  runs alpha-beta on each near-terminal position.

```bash
python3 stress_test.py
```

### `tune_heuristics.py`

Random-search tuner: samples heuristic parameter sets, runs short AI-vs-AI matches
for each, and keeps the configuration with the most four-count wins.
The best set found is printed at the end and was used to update `settings.py`.

```bash
python3 tune_heuristics.py
```

### `states.py`

Fixture data only — no executable entry point.
Contains `hard_states` (20 mid-game move sequences) and `almost_full_boards`
(20 near-complete board layouts) imported by the other benchmarks.

---

## Frontend features

- **Death Note dark theme** — black/deep-navy backgrounds, blood-red accents (`#ff4444`), gold highlights (`#d4af37`).
- **Dynamic AI thinking delay** — the spinner stays visible for exactly as long as the backend calculation takes (minimum 400 ms so the animation is visible); K = 1 disappears almost instantly, K = 5 stays for the full search duration.
- **Depth-aware messages** — "Analyzing board…" at K = 1, "Traversing game tree…" at K = 5.
- **Web Audio sound effects** — eerie 110 Hz thinking hum, 880 Hz click on piece placement, different tones for victory and defeat. Generated with the Web Audio API (no audio files).
- **Scrollable minimax tree** — the tree panel scrolls both horizontally and vertically; `max_depth` for the tree request is capped by `MAX_SEARCH_DEPTH` from `settings.py` (not a hard-coded 6).
- **AI stats panel** — nodes explored, leaves evaluated, alpha-beta cutoffs, and wall-clock time shown after every AI move.

---

## Configuration

All constants are in `backend/configs/settings.py`.

| Constant | Default | Purpose |
|----------|---------|---------|
| `ROWS` | 6 | Board height |
| `COLS` | 7 | Board width |
| `DEFAULT_K` | 3 | Depth used if none is supplied |
| `MAX_SEARCH_DEPTH` / `MAX_K` | 9 | Upper bound enforced by the API |
| `COLUMN_ORDER` | `[3,2,4,1,5,0,6]` | Search order (centre-first) |
| `WIN` | 1 000 000 | Terminal score magnitude |
| `A` | 1 000 | Completed-four score |
| `THREE` … `COL_WEIGHT` | see table above | Heuristic weights |

---

## Assignment requirements

✅ Full game — human vs. computer, AI uses minimax with alpha-beta pruning  
✅ GUI (bonus) — board 7 wide × 6 tall  
✅ Minimax tree printed each turn in readable form (interactive scrollable panel in the UI)  
✅ Heuristic function truncates tree after K levels; K is chosen before the game  
✅ Board heuristic values shown after every AI move (stats panel)

---

## Credits

Alexandria University — Faculty of Engineering  
Computer and Systems Engineering Department  
Artificial Intelligence Course — Assignment 2
