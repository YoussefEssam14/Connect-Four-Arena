# TODO

## Player setup screen and game initialization
- [x] “Home screen for choosing Red or Yellow and minimax search depth from 1 to 9.” Let the player select Red or Yellow and depth 1–9, then start a new game through `POST /game/new` with `{k, human_color}`.
- [x] Make the API origin configurable because no backend URL was supplied; call the supplied game endpoints at `/game/new`, `/game/move`, `/game`, and `/game/tree?max_depth=`.

## Connect Four human-versus-AI play
- [x] “Connect Four game view with the human player on the left and AI on the right; support moves and display the current game state.” Render the API's board, scores, player colors, whose turn it is, winner/game-over state, AI's latest column, and search stats when available. Allow human column drops through `POST /game/move` with `{column}` and retrieve the current state with `GET /game`.

## Minimax search-tree tab
- [x] Display the AI search as a simple tree with visible node and branch connections. Each node should show Max or Min, value, alpha, beta, and best move as a column. Use the supplied reference figure: https://www.researchgate.net/figure/Alpha-beta-pruning-can-speed-up-the-search-depending-on-the-evaluation-order-In-this_fig1_220812836. Increase the text size for clarity and avoid extra node copy that becomes cluttered when there are many nodes.

## Clear interface wording
- [x] Remove unnecessary dramatic phrases throughout the app, including “The evidence is on the board” and “Every branch. Every possibility.” Replace them with concise functional labels and instructions.

## Game result and connect-four animations
- [x] Show an animated end-of-game result with the winner. The game ends when the board is full.
- [x] Animate each completed four-in-a-row on the board.

## Death Note-inspired visual design and responsive behavior
- [x] Give the home and game screens a distinctive Death Note-inspired visual theme, with setup controls and gameplay readable on desktop and mobile.
