import assert from 'node:assert/strict';
import test from 'node:test';
import {
  INITIAL_REPLAY_STATE,
  columnLetter,
  createReplayFromGameHistory,
  normalizeHistory,
  resetReplay,
  selectReplayIndex,
  stepReplay,
  toggleReplayPlayback,
  type MoveHistoryEntry,
} from './caseFile.ts';

function makeGrid(fill = '.'): string[][] {
  return Array.from({ length: 6 }, () => Array.from({ length: 7 }, () => fill));
}

function sampleHistory(): MoveHistoryEntry[] {
  const g1 = makeGrid();
  g1[0][3] = 'R';

  const g2 = makeGrid();
  g2[0][3] = 'R';
  g2[0][2] = 'Y';

  const g3 = makeGrid();
  g3[0][3] = 'R';
  g3[0][2] = 'Y';
  g3[1][3] = 'R';

  return [
    {
      ply: 3,
      actor: 'human',
      color: 'R',
      column: 3,
      grid: g3,
      human_score: 0,
      ai_score: 0,
      evidence: null,
    },
    {
      ply: 1,
      actor: 'human',
      color: 'R',
      column: 3,
      grid: g1,
      human_score: 0,
      ai_score: 0,
      evidence: null,
    },
    {
      ply: 2,
      actor: 'ai',
      color: 'Y',
      column: 2,
      grid: g2,
      human_score: 0,
      ai_score: 0,
      evidence: {
        role: 'MAX',
        value: 14,
        alpha: 14,
        beta: 'inf',
        best_move: 2,
        pruned: true,
        cutoffs: 3,
      },
    },
  ];
}

test('normalizeHistory sorts plies chronologically and handles missing history', () => {
  assert.deepEqual(normalizeHistory(undefined), []);
  assert.deepEqual(normalizeHistory(null), []);
  assert.deepEqual(normalizeHistory([]), []);

  const ordered = normalizeHistory(sampleHistory());
  assert.deepEqual(
    ordered.map((entry) => entry.ply),
    [1, 2, 3],
  );
  assert.equal(ordered[1].actor, 'ai');
  assert.equal(ordered[1].evidence?.pruned, true);
  assert.equal(ordered[0].evidence, null);
});

test('createReplayFromGameHistory selects latest ply and does not fabricate when empty', () => {
  const emptyReplay = createReplayFromGameHistory(undefined);
  assert.deepEqual(emptyReplay, INITIAL_REPLAY_STATE);

  const replay = createReplayFromGameHistory(sampleHistory());
  assert.equal(replay.history.length, 3);
  assert.equal(replay.selectedIndex, 2);
  assert.equal(replay.isPlaying, false);
});

test('selectReplayIndex and stepReplay clamp bounds without mutating history', () => {
  const original = sampleHistory();
  const initial = createReplayFromGameHistory(original);

  const selectedFirst = selectReplayIndex(initial, 0);
  assert.equal(selectedFirst.selectedIndex, 0);
  assert.equal(selectedFirst.history[0].grid[0][3], 'R');
  assert.equal(selectedFirst.history[0].grid[0][2], '.');

  const clampedLow = stepReplay(selectedFirst, -1);
  assert.equal(clampedLow.selectedIndex, 0);

  const steppedNext = stepReplay(clampedLow, 1);
  assert.equal(steppedNext.selectedIndex, 1);
  assert.equal(steppedNext.history[1].actor, 'ai');
  assert.equal(columnLetter(steppedNext.history[1].column), 'C');

  const clampedHigh = selectReplayIndex(steppedNext, 99);
  assert.equal(clampedHigh.selectedIndex, 2);
});

test('toggleReplayPlayback restarts from ply 0 when at end and resetReplay clears state', () => {
  const replayAtEnd = createReplayFromGameHistory(sampleHistory());
  const playing = toggleReplayPlayback(replayAtEnd);
  assert.equal(playing.isPlaying, true);
  assert.equal(playing.selectedIndex, 0);

  const paused = toggleReplayPlayback(playing);
  assert.equal(paused.isPlaying, false);
  assert.equal(paused.selectedIndex, 0);

  const cleared = resetReplay();
  assert.deepEqual(cleared, INITIAL_REPLAY_STATE);
});
