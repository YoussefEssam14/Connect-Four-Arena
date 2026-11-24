export type Color = 'R' | 'Y';

export type MoveEvidence = {
  role: string;
  value: number | string | null;
  alpha: number | string;
  beta: number | string;
  best_move: number | null;
  pruned: boolean;
  cutoffs?: number;
};

export type MoveHistoryEntry = {
  ply: number;
  actor: 'initial' | 'human' | 'ai';
  color: Color | null;
  column: number | null;
  grid: string[][];
  human_score: number;
  ai_score: number;
  evidence: MoveEvidence | null;
};

export type ReplayState = {
  history: MoveHistoryEntry[];
  selectedIndex: number | null;
  isPlaying: boolean;
};

export const INITIAL_REPLAY_STATE: ReplayState = {
  history: [],
  selectedIndex: null,
  isPlaying: false,
};

export function columnLetter(column: number): string {
  return String.fromCharCode(65 + column);
}

export function normalizeHistory(rawHistory: MoveHistoryEntry[] | undefined | null): MoveHistoryEntry[] {
  if (!Array.isArray(rawHistory) || rawHistory.length === 0) {
    return [];
  }
  return [...rawHistory].sort((a, b) => a.ply - b.ply);
}

export function createReplayFromGameHistory(
  rawHistory: MoveHistoryEntry[] | undefined | null,
  previousSelectedIndex: number | null = null,
): ReplayState {
  const history = normalizeHistory(rawHistory);
  if (history.length === 0) {
    return INITIAL_REPLAY_STATE;
  }
  const selectedIndex =
    previousSelectedIndex !== null && previousSelectedIndex >= 0 && previousSelectedIndex < history.length
      ? previousSelectedIndex
      : history.length - 1;
  return {
    history,
    selectedIndex,
    isPlaying: false,
  };
}

export function selectReplayIndex(state: ReplayState, index: number): ReplayState {
  if (state.history.length === 0) {
    return { ...state, selectedIndex: null, isPlaying: false };
  }
  const clamped = Math.max(0, Math.min(index, state.history.length - 1));
  return {
    ...state,
    selectedIndex: clamped,
    isPlaying: false,
  };
}

export function stepReplay(state: ReplayState, delta: -1 | 1): ReplayState {
  if (state.history.length === 0) {
    return { ...state, selectedIndex: null, isPlaying: false };
  }
  const current = state.selectedIndex ?? state.history.length - 1;
  const next = Math.max(0, Math.min(current + delta, state.history.length - 1));
  return {
    ...state,
    selectedIndex: next,
  };
}

export function toggleReplayPlayback(state: ReplayState): ReplayState {
  if (state.history.length <= 1) {
    return { ...state, isPlaying: false };
  }
  if (!state.isPlaying) {
    const atEnd = state.selectedIndex === state.history.length - 1;
    return {
      ...state,
      selectedIndex: atEnd ? 0 : (state.selectedIndex ?? 0),
      isPlaying: true,
    };
  }
  return { ...state, isPlaying: false };
}

export function resetReplay(): ReplayState {
  return INITIAL_REPLAY_STATE;
}
