# Connect Four Frontend — Death Note Edition

A React 18 + TypeScript 5.7 + Vite 6 frontend for Alexandria Connect Four, featuring an interactive Minimax search tree visualizer and a Death Note anime-inspired interface.

---

## Running Locally

```bash
# Install dependencies
npm install

# Start the Vite development server on port 3000
npm run dev
# Or: npm start
```

The frontend runs on **`http://localhost:3000`** and proxies `/game` requests to `http://localhost:8000`.

---

## Features

- **Setup Screen**: Select player character (Red / Light Yagami or Yellow / L Lawliet) and search depth from $k=1$ to $k=9$.
- **Match View**: Drop discs with column guides, live ghost previews, turn indicators, scores, and search telemetry (nodes, leaves, cutoffs, time).
- **Interactive Minimax Decision Tree**:
  - Scrollable (both X and Y) and pannable (click and drag to move canvas).
  - Zoom controls (In, Out, Center, Reset).
  - Expand/collapse branch toggles and "Expand All" / "Collapse All" controls.
  - Depth selector dynamically bounded up to `MAX_SEARCH_DEPTH = 9`.
  - Max / Min color distinctions, gold glowing best-move connectors, and dashed pruned-branch cutoffs.
- **Winning Lines & Animations**: Completed four-in-a-row connections pulsate dynamically on the board.
- **Responsive Layout**: Designed for desktop, tablet, and mobile screens.

---

## Production Build

```bash
npm run build
```
Runs TypeScript verification (`tsc -b`) and Vite production bundling into `dist/`.
