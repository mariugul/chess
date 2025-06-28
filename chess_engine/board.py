import time
import os
import chess.pgn
import argparse


def print_board_progress(game, delay=1):
    board = game.board()
    print(board.unicode())
    for move in game.mainline_moves():
        move_san = board.san(move)
        board.push(move)
        os.system("clear")  # Clear the terminal (Linux/macOS)
        print(f"Move: {move_san}\n")
        print(board.unicode())
        time.sleep(delay)  # Or use input("Press Enter for next move...")

def print_large_board(board):
    piece_map = {
        "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚", "p": "♟",
        "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔", "P": "♙", ".": "·"
    }
    board_str = ""
    rows = str(board).split("\n")
    files = "  a  b  c  d  e  f  g  h"
    for i, row in enumerate(rows):
        board_str += f"{8-i} "
        for c in row.split(" "):
            board_str += piece_map.get(c, c) + "  "
        board_str += "\n"
    board_str += files
    print(board_str)

def print_board_progress(game, delay=1):
    board = game.board()
    print_large_board(board)
    for move in game.mainline_moves():
        move_san = board.san(move)
        board.push(move)
        os.system("clear")
        print(f"Move: {move_san}\n")
        print_large_board(board)
        time.sleep(delay)
# Usage in your main function:
# print_board_progress(game)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Show chess game progress from a PGN file.")
    parser.add_argument("pgn_file", type=str, help="Path to the PGN file")
    parser.add_argument("--delay", type=float, default=0, help="Delay between moves in seconds (default: 0)")
    args = parser.parse_args()
    with open(args.pgn_file) as f:
        game = chess.pgn.read_game(f)
    print_board_progress(game, delay=args.delay)
    print_large_board(game.board())