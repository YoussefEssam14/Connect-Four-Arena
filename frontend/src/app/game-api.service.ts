import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Stats {
  nodes: number;
  leaves: number;
  cutoffs: number;
  time: number;
}

export interface GameState {
  k: number;
  grid: string[][];
  human_score: number;
  ai_score: number;
  human_color: 'R' | 'Y';
  ai_color: 'R' | 'Y';
  winner: string | null;
  is_game_over: boolean;
  is_human_turn: boolean;
  ai_column: number | null;
  stats: Stats | null;
}

export interface TreeNode {
  move: number | null;
  kind: 'MAX' | 'MIN';
  depth: number;
  alpha: number | string;
  beta: number | string;
  value: number | string | null;
  pruned: boolean;
  is_leaf: boolean;
  heuristic: Record<string, number> | null;
  board: string | null;
  best_move: number | null;
  children: TreeNode[];
}

@Injectable({ providedIn: 'root' })
export class GameApiService {
  private http = inject(HttpClient);
  private base = 'http://localhost:8000';

  newGame(k: number, humanColor: 'R' | 'Y'): Observable<GameState> {
    return this.http.post<GameState>(`${this.base}/game/new`, {
      k,
      human_color: humanColor,
    });
  }

  move(column: number): Observable<GameState> {
    return this.http.post<GameState>(`${this.base}/game/move`, { column });
  }

  getState(): Observable<GameState> {
    return this.http.get<GameState>(`${this.base}/game`);
  }

  getTree(maxDepth: number = 3): Observable<TreeNode> {
    return this.http.get<TreeNode>(`${this.base}/game/tree?max_depth=${maxDepth}`);
  }
}
