from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from rich.style import Style

class CustomBarColumn(BarColumn):
    def render(self, task):
        total_width = self.bar_width or 40
        # Map completed from [-100, 100] to [-1, 1]
        prog = max(-1, min(1, task.completed / 100))
        half = total_width // 2
        if prog >= 0:
            white_blocks = half + int(half * prog)
            black_blocks = total_width - white_blocks
        else:
            black_blocks = half + int(half * -prog)
            white_blocks = total_width - black_blocks
        bar = (
            "[white]" + "█" * white_blocks +
            "[grey22]" + "█" * black_blocks +
            "[/]"
        )
        return bar

def show_progress(value):
    console = Console()
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        CustomBarColumn(bar_width=40),
        TextColumn("{task.completed:+.0f}"),
        console=console,
    ) as progress:
        task = progress.add_task("Progress", total=100, completed=value)
        progress.refresh()
        input("Press Enter to exit...")  # Keeps the bar visible until user input

if __name__ == "__main__":
    import sys
    value = -50
    if len(sys.argv) > 1:
        try:
            value = int(sys.argv[1])
            value = max(-100, min(100, value))
        except ValueError:
            pass
    show_progress(value)