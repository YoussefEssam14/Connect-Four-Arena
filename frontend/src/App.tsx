import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Cpu,
  Eye,
  FileText,
  Pause,
  Play,
  Radio,
  RotateCcw,
  SkipBack,
  SkipForward,
  Skull,
  Trophy,
  X,
  Zap,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from 'lucide-react';
import {
  type Color,
  type MoveHistoryEntry,
  type ReplayState,
  INITIAL_REPLAY_STATE,
  columnLetter,
  createReplayFromGameHistory,
  resetReplay,
  selectReplayIndex,
  stepReplay,
  toggleReplayPlayback,
} from './caseFile';

type GameState = {
  k: number;
  grid: string[][];
  human_score: number;
  ai_score: number;
  human_color: Color;
  ai_color: Color;
  winner: string | null;
  is_game_over: boolean;
  is_human_turn: boolean;
  ai_column: number | null;
  stats: { nodes: number; leaves: number; cutoffs: number; time: number } | null;
  history?: MoveHistoryEntry[];
};
type TreeNode = {
  move: number | null;
  kind: string;
  depth: number;
  alpha: number | string;
  beta: number | string;
  value: number | string | null;
  pruned: boolean;
  is_leaf: boolean;
  heuristic: Record<string, unknown> | null;
  board: string | null;
  best_move: number | null;
  children: TreeNode[];
};
type Screen = 'home' | 'game';
type GameTab = 'board' | 'case' | 'tree';

const DEFAULT_ORIGIN = import.meta.env.VITE_API_ORIGIN ?? 'http://localhost:8000';
const MAX_SEARCH_DEPTH = 9;
const TREE_DEPTH_DEFAULT = 3;

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const base = DEFAULT_ORIGIN.trim().replace(/\/+$/, '');
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      ...init,
      headers: { ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    });
  } catch {
    throw new Error('Could not reach the game server at ' + base + '. Make sure the FastAPI backend is running.');
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? String(data.detail) : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return data as T;
}

const colorName = (color: Color) => (color === 'R' ? 'Red' : 'Yellow');
const isPiece = (value: string | undefined) => value === 'R' || value === 'Y';

function analyzeBoard(grid: string[][]) {
  const winningCells = new Set<string>();
  let winner: Color | null = null;
  const directions = [[0, 1], [1, 0], [1, 1], [-1, 1]] as const;
  for (let row = 0; row < grid.length; row += 1) {
    for (let column = 0; column < (grid[row]?.length ?? 0); column += 1) {
      const color = grid[row]?.[column];
      if (!isPiece(color)) continue;
      for (const [rowStep, columnStep] of directions) {
        const line = Array.from({ length: 4 }, (_, step) => [row + rowStep * step, column + columnStep * step] as const);
        if (line.every(([r, c]) => grid[r]?.[c] === color)) {
          line.forEach(([r, c]) => winningCells.add(`${r}-${c}`));
          winner ??= color;
        }
      }
    }
  }
  return { winningCells, winner };
}

function isBoardFull(grid: string[][]) {
  return grid.length > 0 && grid.every((row) => row.length > 0 && row.every((cell) => isPiece(cell)));
}

function isFinishedState(state: GameState) {
  return state.is_game_over || isBoardFull(state.grid);
}

const displayValue = (value: unknown) => {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  if (typeof value === 'number' && isFinite(value)) return value.toFixed(3);
  return String(value);
};

function BrandMark({ small = false }: { small?: boolean }) {
  return (
    <div className={`brand-mark${small ? ' brand-mark--small' : ''}`} aria-label="Death Note Connect Four">
      <div className="brand-mark__glyph"><span>D</span><i>N</i></div>
      {!small && <span className="brand-mark__caption">Connect Four</span>}
    </div>
  );
}

function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [tab, setTab] = useState<GameTab>('board');
  const [humanColor, setHumanColor] = useState<Color>('R');
  const [searchDepth, setSearchDepth] = useState(5);
  const [game, setGame] = useState<GameState | null>(null);
  const [replay, setReplay] = useState<ReplayState>(INITIAL_REPLAY_STATE);
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [treeDepth, setTreeDepth] = useState(TREE_DEPTH_DEFAULT);
  const [loading, setLoading] = useState(false);
  const [treeLoading, setTreeLoading] = useState(false);
  const [error, setError] = useState('');
  const [hoverColumn, setHoverColumn] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (!showResult) return;
    const dismissOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setShowResult(false);
    };
    window.addEventListener('keydown', dismissOnEscape);
    return () => window.removeEventListener('keydown', dismissOnEscape);
  }, [showResult]);

  useEffect(() => {
    if (tab !== 'case' || !replay.isPlaying) return;
    const timer = window.setInterval(() => {
      setReplay((current) => {
        if (current.history.length === 0) return { ...current, isPlaying: false };
        const currentIndex = current.selectedIndex ?? current.history.length - 1;
        if (currentIndex >= current.history.length - 1) {
          return { ...current, isPlaying: false };
        }
        return stepReplay(current, 1);
      });
    }, 900);
    return () => window.clearInterval(timer);
  }, [tab, replay.isPlaying]);

  const startGame = useCallback(async (depth = searchDepth, color = humanColor) => {
    setLoading(true);
    setError('');
    setReplay(resetReplay());
    try {
      const next = await apiRequest<GameState>('/game/new', {
        method: 'POST',
        body: JSON.stringify({ k: depth, human_color: color }),
      });
      setGame(next);
      setReplay(createReplayFromGameHistory(next.history));
      setShowResult(isFinishedState(next));
      setSearchDepth(depth);
      setHumanColor(color);
      setTree(null);
      setTab('board');
      setScreen('game');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start a new game.');
    } finally {
      setLoading(false);
    }
  }, [humanColor, searchDepth]);

  const refreshState = useCallback(async () => {
    setError('');
    try {
      const next = await apiRequest<GameState>('/game');
      setGame(next);
      setReplay((current) =>
        createReplayFromGameHistory(next.history, tab === 'case' ? current.selectedIndex : null),
      );
      setShowResult(isFinishedState(next));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to refresh game state.');
    }
  }, [tab]);

  const loadTree = useCallback(async (depth = treeDepth) => {
    setTreeLoading(true);
    setError('');
    try {
      const next = await apiRequest<TreeNode>(`/game/tree?max_depth=${depth}`);
      setTree(next);
      setTreeDepth(depth);
    } catch (err) {
      setTree(null);
      setError(err instanceof Error ? err.message : 'Unable to load the search tree.');
    } finally {
      setTreeLoading(false);
    }
  }, [treeDepth]);

  const makeMove = useCallback(async (column: number) => {
    if (!game || loading || !game.is_human_turn || isFinishedState(game)) return;
    setLoading(true);
    setError('');
    try {
      const next = await apiRequest<GameState>('/game/move', {
        method: 'POST',
        body: JSON.stringify({ column }),
      });
      setGame(next);
      setReplay(createReplayFromGameHistory(next.history));
      setShowResult(isFinishedState(next));
      if (next.ai_column !== null) {
        try {
          const latestTree = await apiRequest<TreeNode>(`/game/tree?max_depth=${treeDepth}`);
          setTree(latestTree);
        } catch {
          setTree(null);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Your move could not be made.');
    } finally {
      setLoading(false);
    }
  }, [game, loading, treeDepth]);

  const openTree = () => {
    setReplay((current) => ({ ...current, isPlaying: false }));
    setTab('tree');
    if (!tree) void loadTree();
  };

  const openCaseFile = () => {
    setReplay((current) => ({
      ...current,
      isPlaying: false,
      selectedIndex:
        current.history.length > 0
          ? (current.selectedIndex ?? current.history.length - 1)
          : null,
    }));
    setTab('case');
  };

  const returnToLiveBoard = () => {
    setReplay((current) => ({ ...current, isPlaying: false }));
    setTab('board');
  };

  const returnHome = () => {
    setError('');
    setShowResult(false);
    setReplay(resetReplay());
    setScreen('home');
  };

  const effectiveHumanColor = game?.human_color ?? humanColor;
  const effectiveAiColor = game?.ai_color ?? (effectiveHumanColor === 'R' ? 'Y' : 'R');
  const boardAnalysis = game ? analyzeBoard(game.grid) : { winningCells: new Set<string>(), winner: null };
  const gameFinished = game ? isFinishedState(game) : false;
  const finalWinner = game?.winner === 'R' || game?.winner === 'Y'
    ? game.winner
    : game?.winner === 'draw'
      ? null
      : boardAnalysis.winner;
  const resultText = finalWinner ? `${colorName(finalWinner)} wins` : 'Draw';
  const statusText = gameFinished
    ? resultText
    : game?.is_human_turn
      ? 'Your turn'
      : 'AI thinking';

  return (
    <main className={`app-shell${screen === 'game' ? ' app-shell--game' : ''}`}>
      <div className="ambient ambient--one" />
      <div className="ambient ambient--two" />
      {screen === 'home' ? (
        <section className="home-screen">
          <header className="topbar">
            <BrandMark />
          </header>

          <div className="home-grid">
            <section className="hero-copy">
              <h1>Connect<br /><em>Four</em></h1>
              <p className="hero-copy__intro">
                Play Connect Four against Minimax AI with Alpha-Beta pruning. Configure your match and inspect search trees in real time.
              </p>
              <div className="hero-note">
                <div className="hero-note__seal"><Skull size={24} strokeWidth={1.5} /></div>
                <div>
                  <span className="micro-label">RULES</span>
                  <p>Connect four discs vertically, horizontally, or diagonally. The game continues until the 42-slot board is full.</p>
                </div>
              </div>
            </section>

            <section className="setup-card" aria-labelledby="setup-title">
              <h2 id="setup-title">Match Setup</h2>
              <p className="setup-card__subtitle">Select your character and AI search depth.</p>

              <div className="field-group">
                <div className="field-heading">
                  <label>Choose your color</label>
                </div>
                <div className="color-options" role="group" aria-label="Choose your color">
                  {(['R', 'Y'] as Color[]).map((color) => (
                    <button
                      key={color}
                      className={`color-option${humanColor === color ? ' is-selected' : ''}`}
                      onClick={() => setHumanColor(color)}
                      aria-pressed={humanColor === color}
                    >
                      <span className={`disc disc--${color}`}><span /></span>
                      <span className="color-option__copy">
                        <strong>{color === 'R' ? 'Light Yagami' : 'L Lawliet'}</strong>
                        <small>{color === 'R' ? 'Red · Moves first' : 'Yellow · AI moves first'}</small>
                      </span>
                      {humanColor === color && <Check className="color-option__check" size={20} />}
                    </button>
                  ))}
                </div>
              </div>

              <div className="field-group field-group--depth">
                <div className="field-heading">
                  <label htmlFor="depth-input">AI Search Depth (K)</label>
                </div>
                <div className="depth-input-row">
                  <BrainCircuit size={22} strokeWidth={1.5} className="depth-input-icon" />
                  <input
                    id="depth-input"
                    type="number"
                    min="1"
                    value={searchDepth}
                    onChange={(event) => {
                      const raw = event.target.value;
                      if (raw === '') { setSearchDepth(0); return; }
                      const n = parseInt(raw, 10);
                      if (!isNaN(n)) setSearchDepth(n);
                    }}
                    onBlur={() => {
                      if (searchDepth < 1) setSearchDepth(1);
                    }}
                    aria-label="AI search depth"
                    aria-describedby="depth-hint"
                    placeholder="e.g. 5"
                  />
                </div>
                <p id="depth-hint" className="depth-hint">
                  {searchDepth < 1
                    ? 'Must be at least 1.'
                    : searchDepth <= 3
                      ? `K=${searchDepth} — Fast · Reactive`
                      : searchDepth <= 6
                        ? `K=${searchDepth} — Balanced · Deep pruning`
                        : `K=${searchDepth} — Exhaustive · Deep lookahead`}
                </p>
              </div>

              {error && (
                <div className="error-banner" role="alert">
                  <CircleHelp size={18} />
                  <span>{error}</span>
                  <button onClick={() => setError('')} aria-label="Dismiss error"><X size={18} /></button>
                </div>
              )}

              <button className="start-button" onClick={() => void startGame()} disabled={loading}>
                <span>{loading ? 'Starting…' : 'Enter Arena'}</span>
                <ArrowRight size={20} />
              </button>
            </section>
          </div>

          <footer className="home-footer">
            <span>DEATH NOTE ARENA</span>
            <span>MINIMAX WITH ALPHA-BETA PRUNING</span>
          </footer>
        </section>
      ) : (
        <section className="game-screen">
          <header className="game-header">
            <button className="back-button" onClick={returnHome}>
              <ArrowLeft size={18} />
              <span>Back to Setup</span>
            </button>
            <BrandMark small />
            <div className="game-header__right">
              <span className="turn-indicator">
                <i className={game?.is_human_turn && !gameFinished ? 'turn-indicator__dot is-human' : 'turn-indicator__dot'} />
                {statusText}
              </span>
            </div>
          </header>

          <div className="game-title-row">
            <div>
              <h1>Connect Four</h1>
            </div>
            <div className="game-title-row__actions">
              <button className="icon-button" onClick={() => void refreshState()} title="Refresh game state" aria-label="Refresh game state">
                <RotateCcw size={18} />
              </button>
              <button className="text-button" onClick={() => void startGame(game?.k ?? searchDepth, game?.human_color ?? humanColor)}>
                <Zap size={16} /> New Match
              </button>
            </div>
          </div>

          <nav className="game-tabs" aria-label="Game view">
            <button className={tab === 'board' ? 'game-tab is-active' : 'game-tab'} onClick={returnToLiveBoard}>
              <span className="tab-index">01</span>
              <span>BOARD</span>
              <span className="tab-underline" />
            </button>
            <button className={tab === 'case' ? 'game-tab is-active' : 'game-tab'} onClick={openCaseFile}>
              <span className="tab-index">02</span>
              <span>CASE FILE</span>
              {replay.history.length > 0 && <span className="tab-count">{replay.history.length} PLIES</span>}
              <span className="tab-underline" />
            </button>
            <button className={tab === 'tree' ? 'game-tab is-active' : 'game-tab'} onClick={openTree}>
              <span className="tab-index">03</span>
              <span>SEARCH TREE</span>
              <span className="tab-count">{game?.stats ? `${game.stats.nodes} NODES` : ''}</span>
              <span className="tab-underline" />
            </button>
          </nav>

          {error && (
            <div className="error-banner game-error" role="alert">
              <CircleHelp size={18} />
              <span>{error}</span>
              <button onClick={() => setError('')} aria-label="Dismiss error"><X size={18} /></button>
            </div>
          )}

          {tab === 'board' ? (
            <div className="match-layout">
              <PlayerPanel
                side="human"
                color={effectiveHumanColor}
                active={Boolean(game?.is_human_turn && !gameFinished)}
                finished={gameFinished}
                score={game?.human_score ?? 0}
              />

              <section className="board-column-wrap">
                <div className="board-meta">
                  <span><span className="live-dot" /> LIVE MATCH</span>
                  <span>{game?.ai_column !== null && game?.ai_column !== undefined ? `AI Played: Col ${String.fromCharCode(65 + game.ai_column)} (${game.ai_column + 1})` : ''}　 Depth: {game?.k ?? searchDepth}</span>
                </div>

                <div className="board-shell">
                  <div className="board-labels">
                    <span>{gameFinished ? 'MATCH OVER' : game?.is_human_turn ? 'CLICK A COLUMN TO DROP' : 'AI IS THINKING...'}</span>
                  </div>

                  <div className="board-grid" role="group" aria-label="Connect Four game board">
                    {Array.from({ length: 7 }, (_, column) => {
                      let pieceCount = 0;
                      for (let r = 0; r < 6; r++) {
                        if (isPiece(game?.grid?.[r]?.[column])) pieceCount += 1;
                      }
                      const landingRow = pieceCount < 6 ? 5 - pieceCount : -1;
                      const canPlay = Boolean(game?.is_human_turn && !gameFinished && landingRow >= 0 && !loading);
                      return (
                        <button
                          key={column}
                          className={`board-column${hoverColumn === column && canPlay ? ' is-hovered' : ''}`}
                          onClick={() => void makeMove(column)}
                          onMouseEnter={() => setHoverColumn(column)}
                          onMouseLeave={() => setHoverColumn(null)}
                          disabled={!canPlay}
                          aria-label={`Drop in column ${column + 1}`}
                        >
                          <span className="column-cue">
                            {canPlay ? <ArrowDown size={18} /> : <span>{column + 1}</span>}
                          </span>
                          {Array.from({ length: 6 }, (_, visualRow) => {
                            const gridRow = 5 - visualRow;
                            const value = game?.grid?.[gridRow]?.[column] ?? '';
                            const ghost = hoverColumn === column && visualRow === landingRow && canPlay;
                            const winning = boardAnalysis.winningCells.has(`${gridRow}-${column}`);
                            return (
                              <span
                                key={visualRow}
                                className={`board-cell${value === 'R' || value === 'Y' ? ` board-cell--${value}` : ''}${ghost ? ` board-cell--ghost board-cell--${effectiveHumanColor}` : ''}${winning ? ' is-winning' : ''}`}
                              >
                                <i />
                              </span>
                            );
                          })}
                        </button>
                      );
                    })}
                  </div>

                  <div className="board-coordinates">
                    <span>A (1)</span><span>B (2)</span><span>C (3)</span><span>D (4)</span><span>E (5)</span><span>F (6)</span><span>G (7)</span>
                  </div>
                </div>

                <div className={`match-status${gameFinished ? ' match-status--over' : ''}`}>
                  {gameFinished ? <Trophy size={20} /> : loading ? <Activity size={20} className="spin" /> : <Eye size={20} />}
                  <span>{loading ? 'AI is calculating best move…' : statusText}</span>
                  {gameFinished && (
                    <button onClick={() => void startGame(game?.k ?? searchDepth, game?.human_color ?? humanColor)}>
                      Rematch <ArrowRight size={16} />
                    </button>
                  )}
                </div>
              </section>

              <PlayerPanel
                side="ai"
                color={effectiveAiColor}
                active={Boolean(game && !game.is_human_turn && !gameFinished)}
                finished={gameFinished}
                score={game?.ai_score ?? 0}
              />

              <section className="stats-strip">
                <div className="stats-strip__label">
                  <Activity size={18} />
                  <span>SEARCH STATS</span>
                </div>
                <StatItem label="EXPANDED NODES" value={game?.stats?.nodes?.toLocaleString() ?? '—'} />
                <StatItem label="LEAVES" value={game?.stats?.leaves?.toLocaleString() ?? '—'} />
                <StatItem label="CUTOFFS" value={game?.stats?.cutoffs?.toLocaleString() ?? '—'} />
                <StatItem label="TIME" value={game?.stats ? `${(game.stats.time * 1000).toFixed(1)} ms` : '—'} />
              </section>
            </div>
          ) : tab === 'case' ? (
            <CaseFileView
              replay={replay}
              gameFinished={gameFinished}
              finalWinner={finalWinner}
              onSelectIndex={(index) => setReplay((current) => selectReplayIndex(current, index))}
              onStep={(delta) => setReplay((current) => ({ ...stepReplay(current, delta), isPlaying: false }))}
              onTogglePlay={() => setReplay((current) => toggleReplayPlayback(current))}
              onReturnToLive={returnToLiveBoard}
            />
          ) : (
            <section className="tree-view">
              <div className="tree-intro">
                <div>
                  <h2>Minimax Search Tree</h2>
                  <p>Explore the Alpha-Beta evaluation tree and cutoffs.</p>
                </div>
                <label className="tree-depth-select">
                  <span>TREE DEPTH</span>
                  <input
                    type="number"
                    min="0"
                    max={game?.k ?? MAX_SEARCH_DEPTH}
                    value={treeDepth}
                    onChange={(event) => {
                      const max = game?.k ?? MAX_SEARCH_DEPTH;
                      const val = Math.max(0, Math.min(Number(event.target.value), max));
                      void loadTree(val);
                    }}
                    aria-label="Tree display depth"
                  />
                </label>
              </div>

              {treeLoading ? (
                <div className="tree-empty">
                  <Activity className="spin" size={26} />
                  <span>Loading search tree…</span>
                </div>
              ) : tree ? (
                <TreeDiagram rootNode={tree} />
              ) : (
                <div className="tree-empty">
                  <BrainCircuit size={32} />
                  <strong>No search tree yet</strong>
                  <span>Play a move on the board to generate the minimax decision tree.</span>
                  <button className="text-button" onClick={() => void loadTree()}>
                    <RotateCcw size={16} /> Fetch latest tree
                  </button>
                </div>
              )}

              <div className="tree-legend">
                <span><i className="legend-dot legend-dot--max" /> MAX (AI)</span>
                <span><i className="legend-dot legend-dot--min" /> MIN (YOU)</span>
                <span><i className="legend-dot legend-dot--pruned" /> PRUNED / CUTOFF</span>
              </div>
            </section>
          )}

          <footer className="game-footer">
            <span>DEATH NOTE ARENA</span>
            <button onClick={returnHome}>
              EXIT TO SETUP <ArrowRight size={14} />
            </button>
          </footer>
        </section>
      )}

      {game && gameFinished && showResult && (
        <div className="result-overlay" role="dialog" aria-modal="true" aria-labelledby="result-title">
          <section className="result-card">
            <button className="result-close" onClick={() => setShowResult(false)} aria-label="Close dialog">
              <X size={18} />
            </button>
            {finalWinner ? (
              <img
                className="result-winner-gif"
                src="/images/connect-four-winner.gif"
                alt=""
              />
            ) : (
              <img
                className="result-emblem"
                src="/images/four-in-a-row-emblem.webp"
                alt=""
              />
            )}
            <span className="result-label">MATCH COMPLETED</span>
            <h2 id="result-title">{resultText}</h2>
            <p>
              {finalWinner
                ? `${colorName(finalWinner)} connected the most fours (${game.human_score} vs ${game.ai_score}).`
                : `The board is full. Mutual draw (${game.human_score} vs ${game.ai_score}).`}
            </p>
            <div className="result-actions">
              <button className="result-play" onClick={() => void startGame(game.k, game.human_color)}>
                Rematch <ArrowRight size={18} />
              </button>
              <button
                className="result-secondary"
                onClick={() => {
                  setShowResult(false);
                  openCaseFile();
                }}
              >
                <FileText size={16} /> Inspect Case File
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function PlayerPanel({
  side,
  color,
  active,
  finished,
  score,
}: {
  side: 'human' | 'ai';
  color: Color;
  active: boolean;
  finished: boolean;
  score: number;
}) {
  const isAi = side === 'ai';
  const character = isAi
    ? color === 'R' ? 'Light Yagami' : 'L Lawliet'
    : color === 'R' ? 'Light Yagami' : 'L Lawliet';

  return (
    <aside className={`player-panel player-panel--${side}${active ? ' is-active' : ''}`}>
      <div className="player-panel__top">
        <span className="micro-label">{isAi ? 'AI' : 'YOU'}</span>
        <span className="player-panel__mark">{isAi ? <Cpu size={20} /> : <Eye size={20} />}</span>
      </div>
      <img
        className="player-portrait"
        src={isAi ? '/images/minimax-opponent.webp' : '/images/player-strategist.webp'}
        alt={isAi ? 'Minimax AI opponent' : 'Human strategist'}
      />
      <div className="player-panel__identity">
        <h3>{character}</h3>
        <span>{isAi ? 'MINIMAX' : 'HUMAN'}</span>
      </div>
      <div className="player-panel__color">
        <span className={`mini-disc mini-disc--${color}`} />
        {colorName(color)} Disc
      </div>
      <div className="player-panel__score">
        <span>FOURS CONNECTED</span>
        <strong>{score}</strong>
      </div>
      <div className="player-panel__turn">
        {finished ? (
          <><span className="idle-dot" />FINISHED</>
        ) : active ? (
          <><span className="live-dot" />{isAi ? 'THINKING' : 'YOUR TURN'}</>
        ) : (
          <><span className="idle-dot" />AWAITING MOVE</>
        )}
      </div>
    </aside>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CaseFileView({
  replay,
  gameFinished,
  finalWinner,
  onSelectIndex,
  onStep,
  onTogglePlay,
  onReturnToLive,
}: {
  replay: ReplayState;
  gameFinished: boolean;
  finalWinner: Color | null;
  onSelectIndex: (index: number) => void;
  onStep: (delta: -1 | 1) => void;
  onTogglePlay: () => void;
  onReturnToLive: () => void;
}) {
  const { history, selectedIndex, isPlaying } = replay;
  const activeIndex =
    history.length === 0
      ? -1
      : selectedIndex !== null && selectedIndex >= 0 && selectedIndex < history.length
        ? selectedIndex
        : history.length - 1;
  const selectedEntry = activeIndex >= 0 ? history[activeIndex] : null;
  const isAtStart = activeIndex <= 0;
  const isAtEnd = history.length === 0 || activeIndex >= history.length - 1;
  const isFinalSnapshot = gameFinished && activeIndex === history.length - 1;
  const snapshotAnalysis = selectedEntry ? analyzeBoard(selectedEntry.grid) : { winningCells: new Set<string>(), winner: null };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (history.length === 0) return;
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      onStep(-1);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      onStep(1);
    }
  };

  if (history.length === 0 || !selectedEntry) {
    return (
      <section className="case-file-view">
        <div className="case-header">
          <div className="case-header__title">
            <FileText size={20} />
            <div>
              <h2>Case File</h2>
              <p>Chronological match ledger and AI deduction snapshots.</p>
            </div>
          </div>
          <button className="case-btn case-btn--live" onClick={onReturnToLive}>
            <Radio size={15} /> Return to live
          </button>
        </div>
        <div className="tree-empty">
          <FileText size={32} />
          <strong>No recorded plies yet</strong>
          <span>Make a move on the live board to record snapshots and AI deductions in the case file.</span>
        </div>
      </section>
    );
  }

  const moveNumberFormatted = String(selectedEntry.ply).padStart(2, '0');
  const totalPliesFormatted = String(history[history.length - 1]?.ply ?? 0).padStart(2, '0');
  const colChar = selectedEntry.column !== null ? columnLetter(selectedEntry.column) : '—';
  const actorLabel =
    selectedEntry.actor === 'initial'
      ? 'MATCH START'
      : selectedEntry.actor === 'ai'
        ? 'AI'
        : 'PLAYER';
  const evidence = selectedEntry.evidence;

  return (
    <section className="case-file-view" onKeyDown={handleKeyDown} aria-label="Case File deduction replay">
      <div className="case-header">
        <div className="case-header__title">
          <FileText size={20} />
          <div>
            <h2>Case File</h2>
            <p>Read-only evidence replay. Selecting past plies does not alter the live match.</p>
          </div>
        </div>
        <div className="case-counter" aria-live="polite">
          <span>MOVE {moveNumberFormatted} / {totalPliesFormatted}</span>
          <small>{isPlaying ? 'PLAYING REPLAY' : isAtEnd ? 'LATEST PLY' : 'HISTORICAL SNAPSHOT'}</small>
        </div>
      </div>

      <div className="case-controls" role="toolbar" aria-label="Replay controls">
        <div className="case-controls__transport">
          <button
            className="case-btn"
            onClick={() => onStep(-1)}
            disabled={isAtStart}
            aria-label="Previous move"
          >
            <SkipBack size={15} /> Previous
          </button>
          <button
            className={`case-btn${isPlaying ? ' is-playing' : ''}`}
            onClick={onTogglePlay}
            disabled={history.length <= 1}
            aria-pressed={isPlaying}
            aria-label={isPlaying ? 'Pause replay' : 'Play replay'}
          >
            {isPlaying ? <Pause size={15} /> : <Play size={15} />}
            <span>{isPlaying ? 'Pause' : 'Play'}</span>
          </button>
          <button
            className="case-btn"
            onClick={() => onStep(1)}
            disabled={isAtEnd}
            aria-label="Next move"
          >
            Next <SkipForward size={15} />
          </button>
        </div>
        <button
          className="case-btn case-btn--live"
          onClick={onReturnToLive}
          aria-label="Return to live board"
        >
          <Radio size={15} /> Return to live
        </button>
      </div>

      <div className="case-ledger">
        <aside className="case-timeline" aria-label="Chronological move timeline">
          <div className="case-panel-heading">
            <span>TIMELINE</span>
            <span>{history.length} PLIES</span>
          </div>
          <div className="case-timeline-list" role="list">
            {history.map((entry, index) => {
              const isSelected = index === activeIndex;
              const entryCol = entry.column !== null ? columnLetter(entry.column) : null;
              const entryActor =
                entry.actor === 'initial' ? 'START' : entry.actor === 'ai' ? 'AI' : 'PLAYER';
              const entryAria =
                entry.actor === 'initial'
                  ? 'Initial board snapshot'
                  : `Move ${entry.ply}: ${entryActor}, ${entry.color ? colorName(entry.color) : ''}, Column ${entryCol}`;
              return (
                <button
                  key={entry.ply}
                  type="button"
                  role="listitem"
                  className={`case-timeline-item${isSelected ? ' is-selected' : ''}${entry.actor === 'ai' ? ' is-ai' : ' is-human'}`}
                  onClick={() => onSelectIndex(index)}
                  aria-current={isSelected ? 'step' : undefined}
                  aria-label={entryAria}
                >
                  <span className="case-ply-num">{String(entry.ply).padStart(2, '0')}</span>
                  {entry.color ? (
                    <span className={`mini-disc mini-disc--${entry.color}`} />
                  ) : (
                    <span className="mini-disc mini-disc--neutral" />
                  )}
                  <span className="case-ply-label">
                    {entry.actor === 'initial' ? 'MATCH START · Empty board' : `${entryActor} · ${entryCol}`}
                  </span>
                  {entry.actor === 'ai' && entry.evidence?.pruned && (
                    <span className="case-pruned-tag">PRUNED</span>
                  )}
                </button>
              );
            })}
          </div>
        </aside>

        <div className="case-evidence">
          <div className="case-panel-heading">
            <span>SELECTED MOVE EVIDENCE</span>
            <span>PLY {moveNumberFormatted}</span>
          </div>

          <div className="case-summary-bar">
            <div className="case-summary-identity">
              {selectedEntry.color ? (
                <span className={`mini-disc mini-disc--${selectedEntry.color}`} />
              ) : (
                <span className="mini-disc mini-disc--neutral" />
              )}
              <strong>
                {selectedEntry.actor === 'initial'
                  ? 'MATCH START · INITIAL BOARD'
                  : `${actorLabel} · ${selectedEntry.color ? colorName(selectedEntry.color).toUpperCase() : '—'} · COLUMN ${colChar}`}
              </strong>
            </div>
            <span className="case-score-pill">
              SCORE {selectedEntry.human_score} – {selectedEntry.ai_score}
            </span>
          </div>

          {selectedEntry.actor === 'initial' ? (
            <div className="case-human-note">
              <span>Initial Board Snapshot</span>
              <small>Empty 6×7 board recorded at match start before any moves.</small>
            </div>
          ) : selectedEntry.actor === 'human' ? (
            <div className="case-human-note">
              <span>{actorLabel} · Column {colChar} ({selectedEntry.column !== null ? selectedEntry.column + 1 : '—'})</span>
              <small>Human move — no AI search evaluation recorded for this ply.</small>
            </div>
          ) : evidence ? (
            <div className="case-evidence-grid" aria-label="AI Minimax evidence">
              <div className="case-metric">
                <span>ROLE</span>
                <strong>{evidence.role}</strong>
              </div>
              <div className="case-metric">
                <span>VALUE</span>
                <strong>{displayValue(evidence.value)}</strong>
              </div>
              <div className="case-metric">
                <span>ALPHA</span>
                <strong>{displayValue(evidence.alpha)}</strong>
              </div>
              <div className="case-metric">
                <span>BETA</span>
                <strong>{displayValue(evidence.beta)}</strong>
              </div>
              <div className="case-metric">
                <span>BEST MOVE</span>
                <strong>
                  {evidence.best_move !== null
                    ? `Col ${columnLetter(evidence.best_move)} (${evidence.best_move + 1})`
                    : '—'}
                </strong>
              </div>
              <div className="case-metric">
                <span>PRUNING</span>
                <strong>
                  {evidence.pruned
                    ? `Cutoff${evidence.cutoffs ? ` (${evidence.cutoffs})` : ''}`
                    : 'None'}
                </strong>
              </div>
            </div>
          ) : (
            <div className="case-human-note">
              <span>AI · Column {colChar} ({selectedEntry.column !== null ? selectedEntry.column + 1 : '—'})</span>
              <small>AI search metadata unavailable for this ply.</small>
            </div>
          )}

          {isFinalSnapshot && (
            <div className={`case-outcome-banner${finalWinner ? ' is-win' : ' is-draw'}`} role="status">
              {finalWinner ? (
                <>
                  <Trophy size={16} />
                  <span>
                    Final Result: {colorName(finalWinner)} wins ({selectedEntry.human_score} vs {selectedEntry.ai_score}) — winning four highlighted below.
                  </span>
                </>
              ) : (
                <>
                  <Eye size={16} />
                  <span>
                    Final Result: Draw — board full ({selectedEntry.human_score} vs {selectedEntry.ai_score}). No winner declared.
                  </span>
                </>
              )}
            </div>
          )}

          <div className="case-board-wrap">
            <div
              className="case-board-grid"
              role="img"
              aria-label={
                selectedEntry.actor === 'initial'
                  ? 'Initial empty board snapshot'
                  : `Board snapshot after move ${selectedEntry.ply}, ${actorLabel} in column ${colChar}`
              }
            >
              {Array.from({ length: 7 }, (_, column) => (
                <div key={column} className={`case-board-col${selectedEntry.column !== null && column === selectedEntry.column ? ' is-last-move' : ''}`}>
                  {Array.from({ length: 6 }, (_, visualRow) => {
                    const gridRow = 5 - visualRow;
                    const value = selectedEntry.grid?.[gridRow]?.[column] ?? '';
                    const winning = snapshotAnalysis.winningCells.has(`${gridRow}-${column}`);
                    return (
                      <span
                        key={visualRow}
                        className={`board-cell${value === 'R' || value === 'Y' ? ` board-cell--${value}` : ''}${winning ? ' is-winning' : ''}`}
                      >
                        <i />
                      </span>
                    );
                  })}
                </div>
              ))}
            </div>
            <div className="case-board-coords">
              <span>A</span><span>B</span><span>C</span><span>D</span><span>E</span><span>F</span><span>G</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const TREE_NODE_WIDTH = 196;
const TREE_NODE_HEIGHT = 124;
const TREE_NODE_GAP = 32;
const TREE_LEVEL_GAP = 168;

type PositionedTreeNode = {
  node: TreeNode;
  path: string;
  depth: number;
  slot: number;
  children: PositionedTreeNode[];
};

function TreeDiagram({ rootNode }: { rootNode: TreeNode }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(['root']));
  const [isPanning, setIsPanning] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startY, setStartY] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);
  const [zoom, setZoom] = useState(1);

  let nextSlot = 0;

  const placeNode = (node: TreeNode, path: string, depth: number): PositionedTreeNode => {
    const children = expanded.has(path)
      ? (node.children ?? []).map((child, index) => placeNode(child, `${path}.${index}`, depth + 1))
      : [];
    const slot = children.length > 0
      ? (children[0].slot + children[children.length - 1].slot) / 2
      : nextSlot++;
    return { node, path, depth, slot, children };
  };

  const root = placeNode(rootNode, 'root', 0);
  const nodes: PositionedTreeNode[] = [];
  const edges: Array<{ parent: PositionedTreeNode; child: PositionedTreeNode }> = [];
  const collect = (parent: PositionedTreeNode) => {
    nodes.push(parent);
    parent.children.forEach((child) => {
      edges.push({ parent, child });
      collect(child);
    });
  };
  collect(root);

  const maxSlot = Math.max(0, ...nodes.map((item) => item.slot));
  const maxDepth = Math.max(0, ...nodes.map((item) => item.depth));
  const stride = TREE_NODE_WIDTH + TREE_NODE_GAP;
  const canvasWidth = maxSlot * stride + TREE_NODE_WIDTH;
  const canvasHeight = maxDepth * TREE_LEVEL_GAP + TREE_NODE_HEIGHT;
  const columnLabel = (move: number | null) => move === null ? '—' : `Col ${move + 1}`;
  const playerName = (node: TreeNode) => node.kind?.toLowerCase().includes('max') ? 'MAX' : 'MIN';

  const onMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    if (!scrollRef.current) return;
    setIsPanning(true);
    setStartX(e.pageX - scrollRef.current.offsetLeft);
    setStartY(e.pageY - scrollRef.current.offsetTop);
    setScrollLeft(scrollRef.current.scrollLeft);
    setScrollTop(scrollRef.current.scrollTop);
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!isPanning || !scrollRef.current) return;
    e.preventDefault();
    const x = e.pageX - scrollRef.current.offsetLeft;
    const y = e.pageY - scrollRef.current.offsetTop;
    const walkX = (x - startX) * 1.3;
    const walkY = (y - startY) * 1.3;
    scrollRef.current.scrollLeft = scrollLeft - walkX;
    scrollRef.current.scrollTop = scrollTop - walkY;
  };

  const onMouseUp = () => setIsPanning(false);

  const expandAll = () => {
    const allPaths = new Set<string>();
    const gather = (n: TreeNode, p: string) => {
      allPaths.add(p);
      (n.children ?? []).forEach((c, i) => gather(c, `${p}.${i}`));
    };
    gather(rootNode, 'root');
    setExpanded(allPaths);
  };

  const collapseAll = () => setExpanded(new Set(['root']));

  const resetView = () => {
    setZoom(1);
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = Math.max(0, (scrollRef.current.scrollWidth - scrollRef.current.clientWidth) / 2);
      scrollRef.current.scrollTop = 0;
    }
  };

  return (
    <div className="tree-diagram-frame">
      <div className="tree-diagram-toolbar">
        <div className="tree-toolbar-info">
          <span>{nodes.length} nodes · Scroll or drag to navigate</span>
        </div>
        <div className="tree-toolbar-actions">
          <button className="tree-toolbar-btn" onClick={() => setZoom((z) => Math.max(0.4, Number((z - 0.15).toFixed(2))))} title="Zoom out">
            <ZoomOut size={15} />
          </button>
          <button className="tree-toolbar-btn" onClick={() => setZoom(1)} title="Reset zoom">
            {Math.round(zoom * 100)}%
          </button>
          <button className="tree-toolbar-btn" onClick={() => setZoom((z) => Math.min(1.5, Number((z + 0.15).toFixed(2))))} title="Zoom in">
            <ZoomIn size={15} />
          </button>
          <button className="tree-toolbar-btn" onClick={resetView} title="Center view">
            <Maximize2 size={15} /> Center
          </button>
          <button className="tree-toolbar-btn" onClick={expandAll} title="Expand all branches">
            Expand All
          </button>
          <button className="tree-toolbar-btn" onClick={collapseAll} title="Collapse all branches">
            Collapse All
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className={`tree-diagram-scroll${isPanning ? ' is-panning' : ''}`}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        <div
          className="tree-diagram"
          style={{
            width: canvasWidth,
            height: canvasHeight,
            transform: `scale(${zoom})`,
            transformOrigin: 'top center',
          }}
        >
          <svg className="tree-diagram-edges" width={canvasWidth} height={canvasHeight} aria-hidden="true">
            {edges.map(({ parent, child }) => {
              const x1 = parent.slot * stride + TREE_NODE_WIDTH / 2;
              const y1 = parent.depth * TREE_LEVEL_GAP + TREE_NODE_HEIGHT;
              const x2 = child.slot * stride + TREE_NODE_WIDTH / 2;
              const y2 = child.depth * TREE_LEVEL_GAP;
              const best = parent.node.best_move !== null && parent.node.best_move === child.node.move;
              const pruned = child.node.pruned;
              return (
                <path
                  key={`${parent.path}-${child.path}`}
                  className={`tree-edge${best ? ' is-best' : ''}${pruned ? ' is-pruned' : ''}`}
                  d={`M ${x1} ${y1} C ${x1} ${y1 + 25}, ${x2} ${y2 - 25}, ${x2} ${y2}`}
                />
              );
            })}
          </svg>
          {nodes.map(({ node, path, depth, slot }) => {
            const role = playerName(node);
            const hasChildren = (node.children?.length ?? 0) > 0;
            const isExpanded = expanded.has(path);
            const bestMove = node.best_move === null ? '—' : columnLabel(node.best_move);
            return (
              <button
                key={path}
                className={`tree-diagram-node tree-diagram-node--${role.toLowerCase()}${node.pruned ? ' is-pruned' : ''}${node.is_leaf ? ' is-leaf' : ''}`}
                style={{ left: slot * stride, top: depth * TREE_LEVEL_GAP, width: TREE_NODE_WIDTH, height: TREE_NODE_HEIGHT }}
                onClick={() => {
                  if (!hasChildren) return;
                  setExpanded((current) => {
                    const next = new Set(current);
                    if (next.has(path)) next.delete(path);
                    else next.add(path);
                    return next;
                  });
                }}
                disabled={!hasChildren}
                aria-expanded={hasChildren ? isExpanded : undefined}
                aria-label={`${role} node`}
              >
                <span className="tree-node-heading">
                  <strong>{role}</strong>
                  {node.move !== null && <small>Played Col {node.move + 1}</small>}
                  {hasChildren && <span className="tree-node-expand">{isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</span>}
                </span>
                <span className="tree-node-value">
                  <small>VALUE</small>
                  <b>{displayValue(node.value)}</b>
                </span>
                <span className="tree-node-metrics">
                  <span><small>BEST</small><b>{bestMove}</b></span>
                  <span><small>ALPHA</small><b>{displayValue(node.alpha)}</b></span>
                  <span><small>BETA</small><b>{displayValue(node.beta)}</b></span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="tree-diagram-footer">
        <span>{nodes.length} nodes visible</span>
        <span>α: ALPHA BOUND · β: BETA BOUND</span>
      </div>
    </div>
  );
}

export default App;
