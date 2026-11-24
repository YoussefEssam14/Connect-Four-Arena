import {
  Component,
  Input,
  OnChanges,
  AfterViewInit,
  ViewChild,
  ElementRef,
  ChangeDetectorRef,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TreeNode } from './game-api.service';

const NW = 148;
const NH = 80;
const HG = 24;
const VG = 62;

interface LayoutNode {
  n: TreeNode;
  x: number;
  y: number;
}

interface LayoutEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  pruned: boolean;
  best: boolean;
}

@Component({
  selector: 'app-tree-canvas',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="tc-wrap"
      #wrap
      (wheel)="onWheel($event)"
      (mousedown)="onDown($event)"
      (mousemove)="onMove($event)"
      (mouseup)="onUp()"
      (mouseleave)="onUp()"
    >
      <svg class="tc-svg" width="100%" height="100%">
        <defs>
          <radialGradient id="nodeMaxGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(239, 51, 64, 0.28)" />
            <stop offset="100%" stop-color="rgba(17, 19, 34, 0.96)" />
          </radialGradient>
          <radialGradient id="nodeMinGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(255, 212, 59, 0.28)" />
            <stop offset="100%" stop-color="rgba(17, 19, 34, 0.96)" />
          </radialGradient>
          <filter id="bestEdgeGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#ffd43b" flood-opacity="0.7"/>
          </filter>
        </defs>

        <g [attr.transform]="xf">
          @for (e of edges; track $index) {
            <path
              [attr.d]="edgePath(e)"
              fill="none"
              [attr.stroke]="e.best ? '#ffd43b' : e.pruned ? 'rgba(239, 51, 64, 0.32)' : 'rgba(184, 194, 235, 0.5)'"
              [attr.stroke-width]="e.best ? 4 : e.pruned ? 1.5 : 2.5"
              [attr.stroke-dasharray]="e.pruned ? '6 6' : ''"
              [attr.filter]="e.best ? 'url(#bestEdgeGlow)' : ''"
            />
          }

          @for (ln of layoutNodes; track $index) {
            <g
              [attr.transform]="'translate(' + (ln.x - NW / 2) + ',' + ln.y + ')'"
              [attr.opacity]="ln.n.pruned ? 0.38 : 1"
            >
              <rect
                [attr.width]="NW"
                [attr.height]="NH"
                rx="12"
                [attr.fill]="nodeFill(ln.n)"
                [attr.stroke]="nodeStroke(ln.n)"
                [attr.stroke-width]="ln.n.best_move !== null ? 2.5 : 2"
              />

              @if (ln.n.is_leaf) {
                <rect [attr.width]="NW" height="4" rx="2" fill="#7dffbb" opacity="0.95" />
              }

              @if (ln.n.pruned) {
                <line
                  x1="6" y1="6" [attr.x2]="NW - 6" [attr.y2]="NH - 6"
                  stroke="#ef3340" stroke-width="2" opacity="0.75"
                />
                <line
                  [attr.x1]="NW - 6" y1="6" x2="6" [attr.y2]="NH - 6"
                  stroke="#ef3340" stroke-width="2" opacity="0.75"
                />
              }

              <!-- Kind (MAX / MIN) -->
              <text x="10" y="18" class="t-kind" [attr.fill]="kindColor(ln.n.kind)">{{ ln.n.kind }}</text>

              <!-- Column / Move -->
              @if (ln.n.move !== null && !ln.n.pruned) {
                <text [attr.x]="NW - 10" y="18" class="t-col" text-anchor="end">
                  COL {{ ln.n.move + 1 }}
                </text>
              }

              @if (ln.n.pruned) {
                <text [attr.x]="NW / 2" y="18" class="t-pruned" text-anchor="middle">PRUNED</text>
              }

              <!-- Minimax Evaluated Score -->
              <text
                [attr.x]="NW / 2"
                [attr.y]="NH / 2 + 7"
                class="t-val"
                text-anchor="middle"
                [attr.fill]="valueColor(ln.n.value)"
              >{{ fmt(ln.n.value) }}</text>

              <!-- Alpha & Beta bounds -->
              <text x="10" [attr.y]="NH - 10" class="t-ab">α:{{ fmt(ln.n.alpha) }}</text>
              <text [attr.x]="NW - 10" [attr.y]="NH - 10" class="t-ab" text-anchor="end">β:{{ fmt(ln.n.beta) }}</text>

              @if (ln.n.best_move !== null && !ln.n.is_leaf) {
                <text [attr.x]="NW / 2" [attr.y]="NH - 10" class="t-best" text-anchor="middle">
                  ★ BEST C{{ ln.n.best_move + 1 }}
                </text>
              }
            </g>
          }
        </g>
      </svg>

      <div class="tc-toolbar">
        <button class="tc-btn" (click)="fit()" title="Fit Tree To View">⤢ FIT TREE</button>
        <button class="tc-btn" (click)="zoom(1.25)" title="Zoom In">+</button>
        <button class="tc-btn" (click)="zoom(0.8)" title="Zoom Out">−</button>
      </div>

      @if (!layoutNodes.length) {
        <div class="tc-empty">
          <span>Make a move to inspect the Minimax Search Tree</span>
        </div>
      }
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      flex: 1;
      min-height: 0;
      height: 100%;
      position: relative;
    }
    .tc-wrap {
      position: relative;
      flex: 1;
      width: 100%;
      height: 100%;
      min-height: 420px;
      overflow: hidden;
      cursor: grab;
      background: radial-gradient(circle at 50% 30%, rgba(17, 19, 34, 0.75), #0a0b18);
      border-radius: 16px;
      border: 1px solid rgba(255, 244, 210, 0.16);
      box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.6);
    }
    .tc-wrap:active { cursor: grabbing; }
    .tc-svg { display: block; user-select: none; }

    .t-kind { font: 900 13px 'Barlow Condensed', sans-serif; letter-spacing: 0.1em; }
    .t-col  { font: 900 13px 'Barlow Condensed', sans-serif; fill: #ffd15c; letter-spacing: 0.08em; }
    .t-pruned { font: 900 13px 'Barlow Condensed', sans-serif; fill: #ff2a44; letter-spacing: 0.12em; }
    .t-val  { font: 900 22px 'Barlow Condensed', sans-serif; letter-spacing: 0.04em; }
    .t-ab   { font: 800 12px 'Barlow Condensed', sans-serif; fill: #cbd5e1; letter-spacing: 0.06em; }
    .t-best { font: 900 12px 'Barlow Condensed', sans-serif; fill: #ffd15c; }

    .tc-toolbar {
      position: absolute;
      bottom: 14px;
      right: 14px;
      display: flex;
      gap: 8px;
      z-index: 5;
    }
    .tc-btn {
      padding: 7px 14px;
      background: rgba(17, 19, 34, 0.92);
      border: 1.5px solid rgba(255, 244, 210, 0.28);
      border-radius: 8px;
      color: #fffaf0;
      font-family: 'Barlow Condensed', sans-serif;
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.1em;
      cursor: pointer;
      backdrop-filter: blur(10px);
      transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
    }
    .tc-btn:hover {
      background: rgba(255, 212, 59, 0.25);
      border-color: #ffd43b;
      color: #ffd43b;
      transform: translateY(-2px);
      box-shadow: 0 0 16px rgba(255, 212, 59, 0.4);
    }

    .tc-empty {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      color: #94a3b8;
      font-family: 'Barlow Condensed', sans-serif;
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      pointer-events: none;
      text-transform: uppercase;
    }
  `]
})
export class TreeCanvasComponent implements OnChanges, AfterViewInit {
  @Input({ required: true }) node!: TreeNode | null;
  @ViewChild('wrap') wrapRef!: ElementRef<HTMLDivElement>;

  private cd = inject(ChangeDetectorRef);

  NW = NW;
  NH = NH;

  layoutNodes: LayoutNode[] = [];
  edges: LayoutEdge[] = [];

  scale = 1;
  tx = 40;
  ty = 25;
  dragging = false;
  lastMx = 0;
  lastMy = 0;

  get xf() {
    return `translate(${this.tx},${this.ty}) scale(${this.scale})`;
  }

  ngAfterViewInit() {
    this.build();
    this.fit();
  }

  ngOnChanges() {
    this.build();
    this.fit();
  }

  build() {
    this.layoutNodes = [];
    this.edges = [];
    if (!this.node) return;

    const ws = new Map<TreeNode, number>();
    this.calcW(this.node, ws);
    this.place(this.node, ws, ws.get(this.node)! / 2, 0, -1, -1, false);
  }

  calcW(n: TreeNode, ws: Map<TreeNode, number>): number {
    const ch = n.children ?? [];
    if (!ch.length) {
      ws.set(n, NW + HG);
      return NW + HG;
    }
    const total = ch.reduce((s: number, c: TreeNode) => s + this.calcW(c, ws), 0);
    ws.set(n, Math.max(total, NW + HG));
    return ws.get(n)!;
  }

  place(
    n: TreeNode,
    ws: Map<TreeNode, number>,
    cx: number,
    y: number,
    px: number,
    py: number,
    isBestBranch: boolean
  ) {
    this.layoutNodes.push({ n, x: cx, y });
    if (px >= 0) {
      this.edges.push({
        x1: px,
        y1: py + NH,
        x2: cx,
        y2: y,
        pruned: n.pruned,
        best: isBestBranch
      });
    }

    const ch = n.children ?? [];
    if (!ch.length) return;

    const total = ch.reduce((s: number, c: TreeNode) => s + (ws.get(c) ?? 0), 0);
    let startX = cx - total / 2;
    for (const c of ch) {
      const cw = ws.get(c)!;
      const childIsBest = n.best_move !== null && c.move === n.best_move;
      this.place(c, ws, startX + cw / 2, y + NH + VG, cx, y, childIsBest);
      startX += cw;
    }
  }

  edgePath(e: LayoutEdge): string {
    const my = e.y1 + (e.y2 - e.y1) * 0.48;
    return `M${e.x1},${e.y1} C${e.x1},${my + 10} ${e.x2},${my - 10} ${e.x2},${e.y2}`;
  }

  fit() {
    if (!this.wrapRef || !this.layoutNodes.length) return;
    const el = this.wrapRef.nativeElement;
    const ww = el.clientWidth || 600;
    const wh = el.clientHeight || 400;

    const minX = Math.min(...this.layoutNodes.map((l) => l.x - NW / 2));
    const maxX = Math.max(...this.layoutNodes.map((l) => l.x + NW / 2));
    const maxY = Math.max(...this.layoutNodes.map((l) => l.y + NH));
    const treeW = maxX - minX + HG * 2;
    const treeH = maxY + VG;

    this.scale = Math.min(ww / treeW, (wh * 0.88) / treeH, 1.2);
    this.tx = (ww - treeW * this.scale) / 2 - minX * this.scale + HG * this.scale;
    this.ty = 20;
    this.cd.markForCheck();
  }

  zoom(f: number) {
    this.scale = Math.max(0.1, Math.min(3.5, this.scale * f));
  }

  onWheel(e: WheelEvent) {
    e.preventDefault();
    const f = e.deltaY < 0 ? 1.12 : 0.9;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    this.tx = mx - (mx - this.tx) * f;
    this.ty = my - (my - this.ty) * f;
    this.scale = Math.max(0.1, Math.min(3.5, this.scale * f));
  }

  onDown(e: MouseEvent) {
    this.dragging = true;
    this.lastMx = e.clientX;
    this.lastMy = e.clientY;
  }

  onMove(e: MouseEvent) {
    if (!this.dragging) return;
    this.tx += e.clientX - this.lastMx;
    this.ty += e.clientY - this.lastMy;
    this.lastMx = e.clientX;
    this.lastMy = e.clientY;
  }

  onUp() {
    this.dragging = false;
  }

  nodeFill(n: TreeNode): string {
    return n.kind === 'MAX' ? 'url(#nodeMaxGlow)' : 'url(#nodeMinGlow)';
  }

  nodeStroke(n: TreeNode): string {
    if (n.is_leaf) return 'rgba(125, 255, 187, 0.9)';
    if (n.kind === 'MAX') return 'rgba(239, 51, 64, 0.8)';
    return 'rgba(255, 212, 59, 0.8)';
  }

  kindColor(k: string): string {
    return k === 'MAX' ? '#ef3340' : '#ffd43b';
  }

  valueColor(v: number | string | null): string {
    if (v === null || v === undefined) return '#94a3b8';
    if (v === 'inf') return '#7dffbb';
    if (v === '-inf') return '#ef3340';
    const num = Number(v);
    if (num > 0) return '#7dffbb';
    if (num < 0) return '#ef3340';
    return '#fffaf0';
  }

  fmt(v: number | string | null | undefined): string {
    if (v === null || v === undefined) return '—';
    if (v === 'inf') return '+∞';
    if (v === '-inf') return '−∞';
    if (typeof v === 'number') {
      if (Math.abs(v) >= 1_000_000) return (v > 0 ? '+' : '') + (v / 1_000_000).toFixed(1) + 'M';
      if (Math.abs(v) >= 1_000) return (v > 0 ? '+' : '') + v.toFixed(0);
      return (v > 0 ? '+' : '') + v.toFixed(1);
    }
    return String(v);
  }
}
