import argparse
from pathlib import Path
import chess.pgn
import chess.engine
from chess.engine import PovScore
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
import os

# List of included Polyglot books (without .bin extension for argument choices)
INCLUDED_BOOKS = [
    "Human",
    "Titans",
    "baron30",
    "varied",
    "Performance",
    "Book",
    "DCbook_large",
    "Elo2400",
    "KomodoVariety",
    "codekiddy",
    "final-book",
    "gavibook-small",
    "gavibook",
    "gm2600",
    "komodo",
]

class Args(argparse.Namespace):
    pgn_file: Path

def parse_args(namespace: Args = None) -> Args:
    parser = argparse.ArgumentParser(
        description="Analyze a chess PGN file with Stockfish."
    )
    parser.add_argument(
        "pgn_file", type=Path, help="Path to the PGN file to analyze"
    )
    parser.add_argument(
        "--depth", type=int, default=15, help="Analysis depth for Stockfish (default: 15)"
    )
    parser.add_argument(
        "--book",
        type=str,
        default="Human",
        help=(
            "Polyglot opening book to use. "
            "You can also provide a custom path."
        ),
        choices=INCLUDED_BOOKS,
    )
    return parser.parse_args(namespace=namespace)

def resolve_book_path(book_arg):
    if book_arg is None:
        return None
    # If user selected a built-in book, add .bin extension and resolve path
    if book_arg in INCLUDED_BOOKS:
        book_filename = book_arg + ".bin"
        return Path(os.path.join(os.path.dirname(__file__), "..", "books", book_filename)).resolve()
    return Path(book_arg).expanduser().resolve()

def format_eval(pov_score):
    if pov_score.relative.is_mate():
        return f"Mate {pov_score.relative.mate()}", None
    else:
        score = pov_score.relative.score()
        return f"{score/100:+.2f}", score

def get_eval_diff(eval_cp, prev_score):
    if prev_score is not None and eval_cp is not None:
        return f"{(eval_cp - prev_score)/100:+.2f}"
    return "-"

def get_best_move_info(engine, board, move, eval_cp):
    best_move = None
    best_move_str = "-"
    best_score = None
    info = engine.analyse(board, chess.engine.Limit(depth=15))
    pov_score: PovScore = info['score']
    depth = info.get('depth', '-')
    best_move = info.get('pv', [None])[0]
    if best_move:
        best_move_str = board.san(best_move)
    return best_move, best_move_str, pov_score, depth

def get_accuracy(move_number, move, best_move, board, engine, eval_cp, prev_score=None, book_path=None):
    import chess
    import chess.polyglot
    # Use opening book to classify as 'Book' if in opening and book is provided
    if book_path is not None and book_path.exists():
        try:
            with chess.polyglot.open_reader(str(book_path)) as book:
                if any(True for entry in book.find(board)):
                    return "Book"
        except Exception:
            pass
    # If eval_cp is None and not in book, treat as "-" (unclassified)
    if eval_cp is None:
        return "-"
    # Don't penalize forced moves
    if board.legal_moves.count() == 1:
        return "Best"
    # If the position is already lost/won, be more forgiving
    if prev_score is not None and abs(prev_score / 100) > 5.0:
        return "-"
    elif best_move and move == best_move:
        return "Best"
    elif best_move:
        board.push(best_move)
        best_info = engine.analyse(board, chess.engine.Limit(depth=15))
        best_score = best_info['score'].relative.score(mate_score=100000)
        board.pop()
        # If either move or best move is mate, don't classify as blunder
        if (best_info['score'].relative.is_mate() or
            (isinstance(eval_cp, (int, float)) and abs(eval_cp) > 10000)):
            return "-"
        if eval_cp is not None and prev_score is not None:
            # Calculate centipawn loss from the perspective of the player making the move
            # If white to move, loss = prev_score - eval_cp; if black, loss = eval_cp - prev_score
            is_white = (move_number % 2 == 1)
            if is_white:
                loss = (prev_score - eval_cp) / 100
            else:
                loss = (eval_cp - prev_score) / 100
            # If the move improves the position, it's Excellent (but not in book)
            if loss <= 0.0:
                return "Excellent"
            # More forgiving: <0.35: Excellent, <2.0: Good, <2.5: Inaccuracy, <3.5: Mistake, <6.0: Miss, >=6.0: Blunder
            if loss < 0.35:
                return "Excellent"
            elif loss < 2.0:
                return "Good"
            elif loss < 2.5:
                return "Inaccuracy"
            elif loss < 3.5:
                return "Mistake"
            elif loss < 6.0:
                return "Miss"
            else:
                return "Blunder"
        else:
            return "-"
    else:
        return "-"

def get_progress_bar(eval_cp, bar_length=20):
    # Map eval_cp from [-300, 300] to [-100, 100]
    if eval_cp is not None:
        max_cp = 300
        norm_score = max(-max_cp, min(max_cp, eval_cp))
        completed = int((norm_score / max_cp) * 100)
        completed = max(-100, min(100, completed))
        # Use CustomBarColumn logic to generate the bar string
        half = bar_length // 2
        prog = max(-1, min(1, completed / 100))
        if prog >= 0:
            white_blocks = half + int(half * prog)
            black_blocks = bar_length - white_blocks
        else:
            black_blocks = half + int(half * -prog)
            white_blocks = bar_length - black_blocks
        bar = (
            "[white]" + "█" * white_blocks +
            "[black]" + "█" * black_blocks +
            "[/]"
        )
    else:
        bar = "[yellow]" + "█" * (bar_length // 2) + "[/]" + " " * (bar_length - (bar_length // 2))
    return bar

def get_game_type(time_control):
    """Classify game type based on initial time in seconds."""
    try:
        base = time_control.split('+')[0]
        seconds = int(base)
        if seconds < 180:
            return "Bullet"
        elif seconds < 600:
            return "Blitz"
        elif seconds < 1800:
            return "Rapid"
        else:
            return "Classical"
    except Exception:
        return "Unknown"

def print_header(pgn_file, game):
    white = game.headers.get("White", "Unknown")
    black = game.headers.get("Black", "Unknown")
    white_elo = game.headers.get("WhiteElo", "N/A")
    black_elo = game.headers.get("BlackElo", "N/A")
    termination = game.headers.get("Termination", "Unknown")
    time_control = game.headers.get("TimeControl", "Unknown")
    game_type = get_game_type(time_control) if time_control != "Unknown" else "Unknown"
    total_moves = int(sum(1 for _ in game.mainline_moves()) / 2)
    tc_str = get_time_control_str(time_control)
    console = Console()
    player_info = (
        f"[bold white]White:[/bold white] {white} [cyan](Elo: {white_elo})[/cyan]\n"
        f"[bold black]Black:[/bold black] {black} [cyan](Elo: {black_elo})[/cyan]\n"
        f"[yellow]Time Control:[/yellow] {tc_str} [green]({game_type})[/green]\n"
        f"[magenta]Termination:[/magenta] {termination}\n"
        f"[bold]Total Moves:[/bold] {total_moves}"
    )
    console.print(Panel(player_info, title=f"Analyzing: {pgn_file.name}", expand=False, border_style="blue"))

def get_time_control_str(time_control):
    try:
        base = time_control.split('+')[0]
        seconds = int(base)
        minutes = seconds // 60
        if minutes > 0:
            return f"{time_control} ({minutes} min)"
        else:
            return f"{time_control} ({seconds} sec)"
    except Exception:
        return time_control

def get_rich_header_table():
    table = Table(
        show_header=True,
        header_style="bold cyan",
        show_lines=False,
        box=None,
        expand=False,
        row_styles=["on grey23", "on grey15"]
    )
    table.add_column("Move #", justify="center", style="bold")
    table.add_column("Move", justify="left")
    table.add_column("Eval", justify="left")
    table.add_column("ΔEval", justify="left")
    table.add_column("Best Move", justify="center")
    table.add_column("Depth", justify="center")
    table.add_column("Accuracy", justify="left")
    table.add_column("Bar")
    return table

def analyze_game(game, engine, depth, book_path=None):
    board = game.board()
    move_number = 1
    prev_score = None
    # Initialize per-player summary
    white_summary = init_summary_dict()
    black_summary = init_summary_dict()
    console = Console()
    table = get_rich_header_table()
    panel = Panel(table, title="Game Analysis", border_style="green", expand=False)

    with Live(panel, console=console, refresh_per_second=2) as live:
        for move in game.mainline_moves():
            # Determine which player made the move
            is_white = (move_number % 2 == 1)
            summary = white_summary if is_white else black_summary
            process_move(
                board, move, move_number, engine, depth, table, summary, prev_score, book_path
            )
            prev_score = get_eval_cp(board, engine, depth)
            board.push(move)
            move_number += 1
            live.update(panel)

    print_summary_panels(game, white_summary, black_summary)

def init_summary_dict():
    return {
        "Brilliant": 0,
        "Great": 0,
        "Best": 0,
        "Excellent": 0,
        "Good": 0,
        "Book": 0,
        "Inaccuracy": 0,
        "Mistake": 0,
        "Miss": 0,
        "Blunder": 0,
        "-": 0
    }

def process_move(board, move, move_number, engine, depth, table, summary, prev_score, book_path=None):
    san = board.san(move)
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    pov_score: PovScore = info['score']
    depth_val = info.get('depth', '-')
    best_move = info.get('pv', [None])[0]
    best_move_str = board.san(best_move) if best_move else "-"
    eval_str, eval_cp = format_eval(pov_score)
    eval_diff = get_eval_diff(eval_cp, prev_score)
    accuracy = get_accuracy(move_number, move, best_move, board, engine, eval_cp, prev_score, book_path)
    bar = get_progress_bar(eval_cp)
    if accuracy in summary:
        summary[accuracy] += 1
    else:
        summary["-"] += 1
    move_num = f"{((move_number+1)//2):02d}"
    if move_number % 2 == 1:
        move_num_cell = f"[white]{move_num}[/white]"
    else:
        move_num_cell = f"[black on grey11]{move_num}[/black on grey11]"
    table.add_row(
        move_num_cell,
        san,
        eval_str,
        eval_diff,
        best_move_str,
        str(depth_val),
        accuracy,
        bar
    )

def get_eval_cp(board, engine, depth):
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    pov_score: PovScore = info['score']
    _, eval_cp = format_eval(pov_score)
    return eval_cp

def print_summary_panels(game, white_summary, black_summary):
    white = game.headers.get("White", "Unknown")
    black = game.headers.get("Black", "Unknown")
    summary_table = build_summary_table(white, black, white_summary, black_summary)
    console = Console()
    console.print(
        Panel(
            summary_table,
            title=f"Summary",
            border_style="blue",
            expand=False
        )
    )

def build_summary_table(white, black, white_summary, black_summary):
    summary_table = Table.grid(padding=(0, 2))
    summary_table.add_column(justify="right", style="bold")
    summary_table.add_column(justify="center", style="white")
    summary_table.add_column(justify="center", style="black")
    summary_table.add_row(
        "",
        f"[white]{white}[/white]",
        f"[black]{black}[/black]"
    )
    for key, label in [
        ("Brilliant", "[bold bright_magenta]Brilliant[/bold bright_magenta]"),
        ("Great", "[bold green]Great[/bold green]"),
        ("Best", "[bold green]Best[/bold green]"),
        ("Excellent", "[bold cyan]Excellent[/bold cyan]"),
        ("Good", "[bold blue]Good[/bold blue]"),
        ("Book", "[white]Book[/white]"),
        ("Inaccuracy", "[yellow]Inaccuracy[/yellow]"),
        ("Mistake", "[magenta]Mistake[/magenta]"),
        ("Miss", "[bold orange3]Miss[/bold orange3]"),
        ("Blunder", "[red]Blunder[/red]"),
    ]:
        color = {
            "Brilliant": "bright_magenta",
            "Great": "green",
            "Best": "green",
            "Excellent": "cyan",
            "Good": "blue",
            "Book": "white",
            "Inaccuracy": "yellow",
            "Mistake": "magenta",
            "Miss": "orange3",
            "Blunder": "red"
        }[key]
        summary_table.add_row(
            label,
            f"[{color}]{white_summary[key]}[/{color}]",
            f"[{color}]{black_summary[key]}[/{color}]"
        )
    return summary_table

def main():
    args = parse_args()
    book_path = resolve_book_path(args.book)
    try:
        with args.pgn_file.open() as pgn:
            game = chess.pgn.read_game(pgn)
            engine = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
            print_header(args.pgn_file, game)
            analyze_game(game, engine, args.depth, book_path)
            engine.quit()
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user.")

if __name__ == "__main__":
    main()
