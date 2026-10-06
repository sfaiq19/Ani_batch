import typer
from rich.console import Console

app = typer.Typer(
    name="anibatch",
    help="AniBatch — Provider-agnostic batch media download and library manager.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def search(
    query: str = typer.Argument(..., help="Title or keyword to search for."),
) -> None:
    """Search for anime series across providers or metadata services."""
    console.print(f"[bold cyan]Searching for:[/bold cyan] {query}")


@app.command()
def info(
    series_id: str = typer.Argument(..., help="Metadata or series ID."),
) -> None:
    """Display detailed metadata and episode list for a series."""
    console.print(f"[bold cyan]Series ID:[/bold cyan] {series_id}")


@app.command()
def download(
    series_id: str = typer.Argument(..., help="Series identifier to download."),
    episodes: str = typer.Option(
        "all", "--episodes", "-e", help="Episode range (e.g. 1-12, 1,3,5 or all)."
    ),
    quality: str = typer.Option("1080p", "--quality", "-q", help="Preferred video quality."),
    sub_lang: str = typer.Option("en", "--sub-lang", "-s", help="Preferred subtitle language."),
) -> None:
    """Download episodes for a series."""
    console.print(
        f"[bold green]Queuing series {series_id} episodes {episodes} at {quality}...[/bold green]"
    )


@app.command()
def queue() -> None:
    """Show active and pending download jobs."""
    console.print("[bold yellow]Queue is empty.[/bold yellow]")


@app.command()
def resume() -> None:
    """Resume paused or interrupted downloads."""
    console.print("[bold cyan]Resuming downloads...[/bold cyan]")


@app.command()
def history() -> None:
    """View past completed or failed download jobs."""
    console.print("[bold cyan]No download history found.[/bold cyan]")


@app.command()
def doctor() -> None:
    """Check system environment, FFmpeg, and external tools."""
    import shutil

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    console.print("[bold]System Diagnostics:[/bold]")
    if ffmpeg_path:
        console.print(f"  [green]✓[/green] FFmpeg: {ffmpeg_path}")
    else:
        console.print("  [red]✗[/red] FFmpeg: Not found in PATH")
    if ffprobe_path:
        console.print(f"  [green]✓[/green] FFprobe: {ffprobe_path}")
    else:
        console.print("  [red]✗[/red] FFprobe: Not found in PATH")


if __name__ == "__main__":
    app()
