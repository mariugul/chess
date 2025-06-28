# Chess Engine PGN Analyzer

A simple command-line chess PGN analyzer using Stockfish and Python. Provides move-by-move evaluation, accuracy classification, and a summary table for both players, with beautiful terminal output using [rich](https://github.com/Textualize/rich).

## Features
- Analyzes chess games from PGN files using Stockfish
- Evaluates each move and classifies accuracy (Brilliant, Best, Good, etc.)
- Displays a rich table with move details, evaluation bar, and best move suggestions
- Summarizes move quality for both White and Black
- Custom progress bar for evaluation swings

## Requirements
- Python 3.8+
- [Stockfish](https://stockfishchess.org/download/) chess engine installed (default path: `/usr/games/stockfish`)
- [rich](https://pypi.org/project/rich/)
- [python-chess](https://pypi.org/project/python-chess/)

## Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd chess
   ```
2. Install dependencies with pip:
   ```bash
   pip install -r requirements.txt
   ```
   Or install manually:
   ```bash
   pip install rich python-chess
   ```

## Usage

Analyze a PGN file:
```bash
python -m chess_engine.main path/to/game.pgn
```

Optional arguments:
- `--depth N` : Set Stockfish analysis depth (default: 15)

Example:
```bash
python -m chess_engine.main pgn/example_game.pgn --depth 18
```

## Project Structure
- `chess_engine/main.py` — Main analyzer script
- `chess_engine/rich_black_white_progress.py` — Custom progress bar for evaluation
- `pgn/` — Example PGN files

## License
MIT License

## Author
Your Name — <your.email@example.com>
