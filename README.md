# Connect Four Arena — Tactical Edition

A competitive Connect Four web arena featuring a Minimax AI agent with Alpha-Beta pruning, a 64-bit bitboard state engine, tuned tactical heuristics, an interactive decision-tree visualizer, and a chronological Case File deduction replay mode.

---

## Architecture & Project Structure

```text
connect-four-arena2/
├── backend/                  # Python FastAPI application
│   ├── ai/
│   │   ├── algorithms/       # Minimax search & Alpha-Beta pruning
│   │   └── heurisitcs/       # Alexandria 6x7 window evaluation & bonuses
│   ├── apis/                 # REST endpoints (/game/new, /game/move, /game/tree)
│   ├── benchmarks/           # Tournament tuning, stress tests & benchmarks
│   ├── configs/              # Game constants & heuristic weights (settings.py)
│   ├── dtos/                 # Pydantic request / response schemas (GameState, MoveHistoryEntry)
│   ├── exceptions/           # Domain exception classes
│   ├── models/               # Alexandria bitboard engine, Board, Stats, TreeNode
│   ├── services/             # GameService match lifecycle & per-ply history manager
│   ├── tests/                # Pytest suite (45 unit & integration tests)
│   ├── main.py               # FastAPI application entry point
│   └── requirements.txt
├── frontend/                 # React 18 + TypeScript + Vite application
│   ├── src/
│   │   ├── App.tsx           # Main game UI, CaseFileView & TreeDiagram
│   │   ├── caseFile.ts       # Pure Case File history & replay state helpers
│   │   ├── caseFile.test.ts  # Node test suite for Case File replay logic
│   │   ├── main.tsx          # Vite React entry point
│   │   └── styles.css        # Responsive noir theme & evidence-ledger styles
│   ├── public/               # Static images & SVG assets
│   ├── index.html
│   ├── package.json          # Vite, React, test & build scripts
│   └── vite.config.ts        # Vite configuration with /game backend proxy
└── docs/                     # Architecture & design documentation
```

---

## Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18 or higher (tested with Node 22)
- **Package manager**: `npm` or `pnpm`

---

## Installation & Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd connect-four-arena2
```

### 2. Install & Start the FastAPI Backend

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Launch the FastAPI server on port 8000
uvicorn main:app --reload --port 8000
```

Interactive API documentation is available at `http://localhost:8000/docs`.

### 3. Install & Start the Frontend

In a separate terminal:

```bash
cd frontend

# Install Node dependencies (npm or pnpm)
npm install

# Start the Vite development server on port 3000
npm run dev
```

Open `http://localhost:3000` in your browser. Vite proxies `/game` requests to `http://localhost:8000`, or you can override the API origin via `VITE_API_ORIGIN` in `frontend/.env` (see [frontend/.env.example](frontend/.env.example)).

---

## Game Rules (Alexandria Connect Four)

This implementation follows **Alexandria Connect Four** tournament rules:

- **Board**: Standard 7 columns x 6 rows (42 total slots).
- **Match Duration**: Play continues until all **42 slots are filled** (full board).
- **Scoring**: Every completed horizontal, vertical, or diagonal 4-in-a-row connection earns 1 point for the respective player. Discs can participate in multiple intersecting lines.
- **Victory**: The winner is the player with the highest total count of connected fours when the board is full. If scores are tied, the match ends in a mutual draw.

---

## Gameplay Views

### 01 Board
- Interactive 7x6 Connect Four grid with hover column preview and drop indicators.
- Live player and AI panels displaying disc color, connected-fours score, and turn status.
- Real-time search telemetry strip showing expanded nodes, leaves evaluated, alpha-beta cutoffs, and search time.

### 02 Case File (Deduction & Replay Mode)
- **Chronological Timeline**: Records an initial empty board snapshot (`ply 0`) at match start, followed by every human move and AI reply with move number, actor, color, and column (`A`–`G`).
- **Read-Only Replay**: Select any ply or use `Previous`, `Play` / `Pause`, `Next`, and `Return to live` controls (and keyboard Left/Right arrows) to inspect past board positions without mutating the live match.
- **AI Deduction Evidence**: For AI plies, displays `ROLE` (`MAX`/`MIN`), `VALUE`, `ALPHA`, `BETA`, `BEST MOVE`, and whether alpha-beta pruning occurred (`Cutoffs`). Human plies display a factual move summary without fabricated evaluation metrics.
- **End-of-Match Review**: Highlights winning four-in-a-row cells or displays a draw notice when inspecting the final board.

### 03 Search Tree (Minimax Visualizer)
- **Scrollable & Pannable**: Drag anywhere or use horizontal and vertical scrollbars to inspect large search trees.
- **Zoom & View Controls**: Zoom in/out (`40%`–`150%`), reset zoom, center view, and expand or collapse all branches.
- **Depth Filter**: Filter visible tree depth from Level 0 (root only) up to the configured search depth (up to `MAX_SEARCH_DEPTH = 9`).
- **Visual Diagnostics**:
  - `MAX` nodes highlighted in crimson (AI).
  - `MIN` nodes highlighted in gold (Human).
  - Gold connectors on the best-move branch.
  - Dashed red paths on pruned/cutoff branches.
  - Live `alpha` / `beta` bounds and minimax values on every node.

---

## AI Engine & Search Strategy

### 1. Fast Bitboard Representation
The board state is stored as two 64-bit integers (`bb[0]` for Red, `bb[1]` for Yellow) in a 7x7 bitboard layout.
- Horizontal, vertical, and diagonal lines are verified using single-instruction bitwise shifts (`bb & (bb >> d) & (bb >> 2d) & (bb >> 3d)`).
- Move generation, undoing, and terminal four counting run in O(1) operations with zero heap allocation.

### 2. Alpha-Beta Minimax Search
- **Lookahead Depth (`k`)**: Configurable from `k = 1` (fast) up to `k = 9` (deep lookahead).
- **Center-First Move Ordering**: Columns are evaluated in order `[3, 2, 4, 1, 5, 0, 6]`, triggering early alpha-beta cutoffs.
- **Depth Configuration**: `MAX_SEARCH_DEPTH = 9` in [backend/configs/settings.py](backend/configs/settings.py).

### 3. Tuned Heuristic Parameters
Heuristic weights were tuned via head-to-head tournament benchmarking:
- `A = 1000`: Completed 4-in-a-row value.
- `THREE = 120`: Uncontested open 3-in-a-row.
- `TEMPO_BONUS = 420`: Immediate unblockable win threat on the current turn.
- `PARITY_BONUS = 80`: Advantage for controlling odd/even parity rows.
- `THREE_BURIED = 0.48`: Weighting for potential threats currently blocked below.
- `TWO = 12`: Open 2-in-a-row potential.
- `COL_WEIGHT = [3, 4, 6, 9, 6, 4, 3]`: Positional gravity favoring central columns.

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/game/new` | Start a new match (`{ "k": 1..9, "human_color": "R" \| "Y" }`) and initialize `history` |
| `POST` | `/game/move` | Human drops a disc (`{ "column": 0..6 }`), AI replies if game continues, appends plies to `history` |
| `GET` | `/game` | Snapshot of current board, scores, turns, stats, and `history` |
| `GET` | `/game/tree?max_depth=0..9` | Minimax decision tree from the latest AI move |
| `GET` | `/health` | Health check probe |

---

## Running Tests & Benchmarks

### Backend Test Suite
```bash
cd backend
.venv/bin/python -m pytest tests/
```
Runs all **45 unit and integration tests** covering bitboard moves, gravity, window evaluations, minimax correctness, alpha-beta cutoffs, per-ply history snapshots, and REST API endpoints.

### Frontend Unit Tests
```bash
cd frontend
npm test
```
Runs the Case File replay and history-ordering test suite (`src/caseFile.test.ts`).

### Frontend Production Build
```bash
cd frontend
npm run build
```
Type-checks with `tsc -b` and bundles with Vite.

### Backend Benchmarks & Tuning
```bash
cd backend
.venv/bin/python benchmarks/benchmark_alpha_beta.py
.venv/bin/python benchmarks/stress_test.py
.venv/bin/python benchmarks/tune_heuristics.py
```
