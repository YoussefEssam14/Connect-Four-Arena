import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.board import Board
from models.stats import Stats
from configs.settings import ROWS, COLS, COLUMN_ORDER
from ai.heurisitcs.evaluate import evaluate

from states import hard_states

INF = float("inf")
# -------------- MINIMAX 
def minimax(board : Board , depth : int , maximizer : int , stats : Stats , order : list[int]):
    stats.nodes += 1
    moves = board.valid_moves(order)


    if depth == 0 or not moves:
        stats.leaves += 1
        score , _ = evaluate(board,maximizer)
        return score
    

    maximizing = board.player_to_move == maximizer 
    best = -INF if maximizing else INF


    for col in moves:
        board.make_move(col)
        score = minimax(board,depth-1,maximizer,stats,order)
        board.undo(col)
        if maximizing:
            best = max(best,score)
        else:
            best = min(best,score)

    return best

def alpha_beta_benchmarks(board, depth, alpha, beta, maximizer, stats, order):
    stats.nodes += 1
    moves = board.valid_moves(order)

    if depth == 0 or not moves:
        stats.leaves += 1
        score, _ = evaluate(board, maximizer)
        return score

    maximizing = board.player_to_move == maximizer
    best = -INF if maximizing else INF

    for col in moves:
        board.make_move(col)

        score = alpha_beta_benchmarks(
            board, depth - 1, alpha, beta,
            maximizer, stats, order
        )

        board.undo(col)

        if maximizing:
            best = max(best, score)
            alpha = max(alpha, best)
        else:
            best = min(best, score)
            beta = min(beta, best)

        if alpha >= beta:
            stats.cutoffs += 1
            break

    return best



def run():

    board = Board();
    sequential = list(range(COLS))
    print("=" * 90)
    print("             MINIMAX AND ALPHA-BETA BENCHMARK")
    print("=" * 90)
    print(f"Board Size     : {ROWS} x {COLS}")
    print(f"Center Order   : {COLUMN_ORDER}")


    # 1. Minimax vs Alpha-Beta
    print("\n1. MINIMAX VS ALPHA-BETA (EMPTY BOARD)")
    print("-" * 90)

    print(
        f"{'Depth':<8} {'Minimax Nodes':<16} {'AB Nodes':<14} "
        f"{'Cutoffs':<12} {'Pruned %':<12} {'MM Time':<12} "
        f"{'AB Time':<12} {'Speedup'}"
    )


    for depth in range(1,8):
        mm_stats = Stats()

        start = time.perf_counter()
        minimax(board,depth,0,mm_stats,COLUMN_ORDER)
        mm_time = time.perf_counter() - start


        #Alpha-Beta
        ab_stats = Stats()
        start = time.perf_counter()
        alpha_beta_benchmarks(board,depth,-INF,INF,0,ab_stats,COLUMN_ORDER)
        ab_time = time.perf_counter() - start
        pruned = (mm_stats.nodes - ab_stats.nodes) / mm_stats.nodes * 100
        speedup = mm_time / ab_time if ab_time > 0 else 0
        print(
            f"{depth:<8} {mm_stats.nodes:<16,d} {ab_stats.nodes:<14,d} "
            f"{ab_stats.cutoffs:<12,d} {pruned:<11.2f}% "
            f"{mm_time * 1000:<11.2f}ms {ab_time * 1000:<11.2f}ms "
            f"{speedup:.2f}x"
        )
    
    print("\n2. Trying differnet moving orders")
    print("-" * 90)
    MOVE_ORDER = [[0,1,2,3,4,5,6],COLUMN_ORDER,[6,5,4,3,2,1,0],[0,6,1,5,2,4,3],[0,1,6,5,4,3,2],[1,2,3,6,5,4,0],[1,0,5,6,2,4,3],[3,2,4,5,6,1,0],[1,6,0,2,4,3,5]]
    print(
        f"{"Order":<20} {'Depth':<8} {'AB Nodes':<14} "
        f"{'Cutoffs':<12} "
        f"{'AB Time':<12}"
    )
    depth = 5
    for order in MOVE_ORDER:
        ab_stats = Stats()
        start = time.perf_counter()
        alpha_beta_benchmarks(board,depth,-INF,INF,0,ab_stats,order)
        ab_time = time.perf_counter() - start
        print(
            f"{order} {depth:<8} {ab_stats.nodes:<14,d} "
            f"{ab_stats.cutoffs:<12,d}"
            f"{ab_time * 1000:<11.2f}ms "
        )

    print("\n3. MIDGAME TACTICAL SEARCH PERFORMANCE && Stress testing with max_search_depth  = 12")

    print("-" * 90)
    print(
        f"{"Index":<10} {'Depth':<8} {'AB Nodes':<14} "
        f"{'Cutoffs':<12} "
        f"{'AB Time':<12}"
    )
    idx = 0
    for state in hard_states:
        nw_board = Board()
        for move in state:
            nw_board.make_move(move)
        # Stree testing with depth = 12
        depth = 12
        ab_stats = Stats()
        start = time.perf_counter()
        alpha_beta_benchmarks(nw_board,depth,-INF,INF,0,ab_stats,COLUMN_ORDER)
        ab_time = time.perf_counter() - start
        print(
            f"{idx:<10} {depth:<8} {ab_stats.nodes:<14} "
            f"{ab_stats.cutoffs:<12} "
            f"{ab_time:<12}"
        )
        idx+=1
        

        

    
run()