# Connect Four Arena

A sophisticated Connect Four game featuring a Minimax AI opponent with Alpha-Beta Pruning. Built with Python FastAPI backend and Angular frontend, featuring a Death Note anime-inspired dark theme.

##  Project Structure

```
connect-four-arena2/
├── backend/           # Python FastAPI server
│   ├── ai/           # AI algorithms & heuristics
│   ├── apis/         # FastAPI endpoints
│   ├── configs/      # Game configuration
│   ├── dtos/         # Data schemas
│   ├── models/       # Game models (Board, Stats, etc.)
│   ├── services/     # Game service layer
│   ├── main.py       # FastAPI app entry point
│   └── requirements.txt
├── frontend/         # Angular 22 application
│   ├── src/app/
│   │   ├── board/           # Game board component
│   │   ├── setup/           # Game setup component
│   │   ├── tree-view/       # Minimax tree visualizer
│   │   ├── app.ts           # Main app component
│   │   ├── game-api.ts      # API service
│   │   └── models.ts        # TypeScript interfaces
│   └── src/styles.css       # Death Note theme styles
└── docs/            # Documentation
```

##  Quick Start

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python3 -m main
# Server runs on http://localhost:8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm start
# Frontend runs on http://localhost:4200
```

The frontend is configured to proxy API requests to `http://localhost:8000/game`.

## How to Play

1. **Start a Game:**
   - Choose AI difficulty (K = 1-5, higher = stronger)
   - Select your color (Red = play first, Yellow = AI plays first)
   - Click START GAME

2. **Game Rules:**
   - Click any column to drop your piece
   - Pieces fall to the lowest available row
   - Connect 4 of your pieces vertically, horizontally, or diagonally
   - Game ends when board is full
   - Winner = player with most connected fours

3. **View AI Analysis:**
   - After AI moves, see performance stats:
     - **Nodes Explored:** Total game tree nodes evaluated
     - **Leaves Evaluated:** Leaf nodes reached (heuristic evaluated)
     - **Cutoffs:** Alpha-beta pruning cutoffs (optimization)
     - **Time (ms):** Computation time
   - Click "Show Tree" to visualize the minimax decision tree

##  AI Algorithm

### Minimax with Alpha-Beta Pruning

The AI uses the classic minimax algorithm optimized with alpha-beta pruning:

- **K-depth search:** Explores game tree up to K moves ahead
- **Heuristic evaluation:** Evaluates positions using game features:
  - Connected pieces (groups of 2, 3, 4)
  - Open positions vs blocked pieces
  - Column positioning strategies
  - Parity (even/odd row preference)
- **Alpha-Beta Pruning:** Eliminates branches that cannot affect the final decision
- **Column ordering:** Explores central columns first (more likely to be winning)

### Difficulty Levels

| K | Depth | Strength | Typical Nodes |
|---|-------|----------|---------------|
| 1 | 1 move | Very Easy | ~7 |
| 2 | 2 moves | Easy | ~50 |
| 3 | 3 moves | Medium | ~400 |
| 4 | 4 moves | Hard | ~3,000+ |
| 5 | 5 moves | Brutal | ~20,000+ |

##  UI/UX - Death Note Theme

The interface features a dark, sophisticated design inspired by the Death Note anime:

- **Color Scheme:**
  - Black background (#0a0e27, #1a1f3a)
  - Blood red accents (#ff4444)
  - Gold highlights (#d4af37)
  - Soft white text (#e8e8e8)

- **Effects:**
  - Glowing text animations
  - Smooth transitions and hover effects
  - Piece drop animations
  - Pulsing highlights for important elements

- **Components:**
  - Game board with realistic piece physics
  - Setup form with difficulty selection
  - Live AI statistics display
  - Interactive minimax tree visualization
  - Responsive design (mobile-friendly)

##  API Endpoints

### POST /game/new
Start a new game
```json
{
  "k": 3,
  "human_color": "R"
}
```

### POST /game/move
Make a human move
```json
{
  "column": 3
}
```

### GET /game
Get current game state

### GET /game/tree?max_depth=2
Get minimax tree from last AI move

##  Configuration

Edit `backend/configs/settings.py` to adjust:

- Board dimensions (ROWS=6, COLS=7)
- Heuristic weights:
  - `WIN`: Terminal win value (1,000,000)
  - `A`: Completed four value (1,000)
  - `THREE`: Three-in-a-row value (100)
  - `TWO`: Two-in-a-row value (10)
- Column search order (central first)

##  Development Notes

### Adding New AI Features

1. **Heuristic improvements:** Modify `backend/ai/heurisitcs/evaluate.py`
2. **Algorithm optimization:** Update `backend/ai/algorithms/alpha_beta.py`
3. **Game logic:** Extend `backend/models/board.py`

### Frontend Customization

- **Theme:** Modify CSS variables in `frontend/src/styles.css`
- **Components:** Update Angular components in `frontend/src/app/*/`
- **API calls:** Extend `frontend/src/app/game-api.ts`

##  Testing

Backend syntax check:
```bash
cd backend
python3 -m py_compile main.py
```

##  Key Technologies

**Backend:**
- Python 3.10+
- FastAPI 0.165+
- Pydantic 2.14+ (data validation)
- Uvicorn (ASGI server)

**Frontend:**
- Angular 22
- TypeScript 6.0+
- Tailwind CSS 4.1+ (utility-first CSS)
- RxJS (reactive programming)

##  Assignment Requirements Met

✅ Full game: human vs computer  
✅ Minimax with alpha-beta pruning  
✅ Configurable search depth (K parameter)  
✅ Heuristic evaluation function  
✅ Tree visualization (console + interactive GUI)  
✅ Performance statistics (nodes, leaves, cutoffs, time)  
✅ Responsive UI with modern styling  
✅ API-based architecture (bonus)  

## License & Credits

Alexandria University - Artificial Intelligence Course  
Assignment 2: Minimax Connect Four Agent  

---

