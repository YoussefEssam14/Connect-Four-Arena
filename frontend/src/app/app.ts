import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { GameApiService, GameState, TreeNode } from './game-api.service';
import { TreeCanvasComponent } from './tree-canvas.component';
import { SoundService } from './sound.service';

export type DiscColor = 'red' | 'yellow';
export type Screen = 'home' | 'game';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, TreeCanvasComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private api = inject(GameApiService);
  public sound = inject(SoundService);

  readonly ROWS = 6;
  readonly COLS = 7;
  readonly columns = Array.from({ length: 7 }, (_, i) => i);
  readonly cells = Array.from({ length: 42 }, (_, i) => i);
  readonly depths = Array.from({ length: 9 }, (_, i) => i + 1);

  screen: Screen = 'home';
  color: DiscColor = 'red';
  depth = 5;

  gameState: GameState | null = null;
  treeNode: TreeNode | null = null;
  treeDepth = 3;

  loading = false;
  error: string | null = null;
  winningCells: number[] = [];
  celebration: { color: DiscColor; count: number; name: string; quote: string } | null = null;
  private celebrationTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {}

  get computerColor(): DiscColor {
    return this.color === 'red' ? 'yellow' : 'red';
  }

  get humanCharacterName(): string {
    return this.color === 'red' ? 'LIGHT YAGAMI' : 'L LAWLIET';
  }

  get humanCharacterRole(): string {
    return this.color === 'red' ? 'KIRA · GOD OF THE NEW WORLD' : 'L · GREATEST DETECTIVE';
  }

  get aiCharacterName(): string {
    return this.computerColor === 'red' ? 'LIGHT YAGAMI' : 'L LAWLIET';
  }

  get aiCharacterRole(): string {
    return this.computerColor === 'red' ? 'KIRA · GOD OF THE NEW WORLD' : 'L · GREATEST DETECTIVE';
  }

  get humanScore(): number {
    return this.gameState?.human_score ?? 0;
  }

  get aiScore(): number {
    return this.gameState?.ai_score ?? 0;
  }

  get isHumanTurn(): boolean {
    return this.gameState?.is_human_turn ?? true;
  }

  get isGameOver(): boolean {
    return this.gameState?.is_game_over ?? false;
  }

  get winner(): string | null {
    return this.gameState?.winner ?? null;
  }

  toggleSound() {
    this.sound.toggleSound();
  }

  selectColor(c: DiscColor) {
    this.color = c;
    this.sound.playHover();
  }

  startMatch() {
    this.screen = 'game';
    this.sound.playTurnChange();
    this.newMatch();
  }

  exitMatch() {
    this.screen = 'home';
    this.sound.playHover();
    this.clearCelebration();
  }

  reset() {
    this.sound.playHover();
    this.newMatch();
  }

  newMatch() {
    this.loading = true;
    this.error = null;
    this.treeNode = null;
    this.clearCelebration();
    const humanChar = this.color === 'red' ? 'R' : 'Y';

    this.api.newGame(this.depth, humanChar).subscribe({
      next: (state) => {
        const prev = this.gameState;
        this.gameState = state;
        this.loading = false;
        if (state.ai_column !== null) {
          this.sound.playDiscDrop(this.computerColor === 'red');
          this.fetchTree();
        }
        this.checkWinLines(prev, state);
      },
      error: (err) => {
        this.error = err?.error?.detail ?? 'Unable to connect to game engine.';
        this.loading = false;
      },
    });
  }

  playColumn(col: number) {
    if (!this.isHumanTurn || this.isGameOver || this.loading) return;

    this.sound.playDiscDrop(this.color === 'red');
    this.loading = true;
    this.error = null;
    const prev = this.gameState;

    this.api.move(col).subscribe({
      next: (state) => {
        this.gameState = state;
        this.loading = false;
        if (state.ai_column !== null) {
          setTimeout(() => {
            this.sound.playDiscDrop(this.computerColor === 'red');
          }, 80);
        }
        this.checkWinLines(prev, state);
        if (state.ai_column !== null || !state.is_human_turn) {
          this.fetchTree();
        }
        if (state.is_game_over) {
          this.sound.playGameOver();
        }
      },
      error: (err) => {
        this.error = err?.error?.detail ?? 'Invalid move.';
        this.loading = false;
      },
    });
  }

  fetchTree() {
    this.api.getTree(this.treeDepth).subscribe({
      next: (t) => {
        this.treeNode = t;
      },
      error: () => {},
    });
  }

  setTreeDepth(d: number) {
    this.treeDepth = d;
    this.sound.playHover();
    this.fetchTree();
  }

  discAt(cellIndex: number): DiscColor | null {
    if (!this.gameState?.grid) return null;
    const visualRow = Math.floor(cellIndex / this.COLS);
    const col = cellIndex % this.COLS;
    const gridRow = this.ROWS - 1 - visualRow;
    const char = this.gameState.grid[gridRow]?.[col];
    if (char === 'R') return 'red';
    if (char === 'Y') return 'yellow';
    return null;
  }

  cellClasses(cellIndex: number): Record<string, boolean> {
    const d = this.discAt(cellIndex);
    const isAiRecent = this.isAiRecentCell(cellIndex);
    return {
      'has-disc': d !== null,
      'disc--red': d === 'red',
      'disc--yellow': d === 'yellow',
      'is-winning': this.winningCells.includes(cellIndex),
      'is-ai-recent': isAiRecent,
    };
  }

  isAiRecentCell(cellIndex: number): boolean {
    if (this.gameState?.ai_column === null) return false;
    const visualRow = Math.floor(cellIndex / this.COLS);
    const col = cellIndex % this.COLS;
    if (col !== this.gameState?.ai_column) return false;
    for (let r = 0; r < this.ROWS; r++) {
      if (this.gameState?.grid[r]?.[col] !== '.') {
        const topVisualRow = this.ROWS - 1 - r;
        return visualRow === topVisualRow;
      }
    }
    return false;
  }

  turnColor(): DiscColor {
    return this.isHumanTurn ? this.color : this.computerColor;
  }

  private checkWinLines(prev: GameState | null, next: GameState) {
    if (!prev) return;
    const humanDiff = next.human_score - prev.human_score;
    const aiDiff = next.ai_score - prev.ai_score;

    if (humanDiff > 0) {
      this.triggerCelebration(this.color, humanDiff, this.humanCharacterName, this.color === 'red' ? 'JUST AS PLANNED!' : 'MY HYPOTHESIS WAS CORRECT.');
    } else if (aiDiff > 0) {
      this.triggerCelebration(this.computerColor, aiDiff, this.aiCharacterName, this.computerColor === 'red' ? 'I SHALL CLEANSE THIS BOARD!' : 'EXACTLY AS CALCULATED.');
    }
  }

  private triggerCelebration(playerColor: DiscColor, count: number, name: string, quote: string) {
    this.sound.playPointScored();
    this.celebration = { color: playerColor, count, name, quote };
    if (this.celebrationTimer) clearTimeout(this.celebrationTimer);
    this.celebrationTimer = setTimeout(() => {
      this.celebration = null;
    }, 3200);
  }

  private clearCelebration() {
    this.celebration = null;
    if (this.celebrationTimer) {
      clearTimeout(this.celebrationTimer);
      this.celebrationTimer = null;
    }
  }
}
