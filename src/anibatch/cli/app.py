import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from anibatch.core.config import AniBatchConfig, get_default_config_path
from anibatch.core.exceptions import AniBatchError
from anibatch.providers.registry import registry
from anibatch.services.download_service import DownloadService

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(
    name="anibatch",
    help="AniBatch — Provider-agnostic batch media download and library manager.",
    no_args_is_help=True,
)
console = Console(legacy_windows=False)


def get_service() -> DownloadService:
    config = AniBatchConfig.load()
    return DownloadService(config=config)


@app.command()
def search(
    query: str = typer.Argument(..., help="Title or keyword to search for."),
    provider: str = typer.Option("test", "--provider", "-p", help="Target provider."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Search for anime series across providers or metadata services."""
    import json

    service = get_service()
    results = asyncio.run(service.search(query))

    if json_output:
        print(json.dumps(results, indent=2))
        return

    if not results:
        console.print(f"[yellow]No results found for '{query}'.[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}'")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold white")
    table.add_column("Year", style="green")
    table.add_column("Episodes", style="magenta")
    table.add_column("Source", style="blue")

    for item in results:
        table.add_row(
            str(item.get("id")),
            str(item.get("title")),
            str(item.get("year") or "N/A"),
            str(item.get("episodes") or "N/A"),
            str(item.get("source")),
        )
    console.print(table)


@app.command()
def info(
    series_id: str = typer.Argument(..., help="Metadata or series ID."),
    provider: str = typer.Option("test", "--provider", "-p", help="Provider to query."),
) -> None:
    """Display detailed metadata and episode list for a series."""
    service = get_service()
    data = asyncio.run(service.get_series_info(series_id, provider_name=provider))

    if "error" in data:
        console.print(f"[red]{data['error']}[/red]")
        return

    console.print(f"[bold cyan]Series:[/bold cyan] {data['title']} ({data.get('year') or 'N/A'})")
    console.print(f"[bold cyan]Provider:[/bold cyan] {data['provider']}")

    episodes = data.get("episodes", [])
    console.print(f"\n[bold]Available Episodes ({len(episodes)}):[/bold]")
    for ep in episodes:
        console.print(f"  [green][OK][/green] Episode {int(ep['number']):02d}: {ep['title']}")


@app.command()
def download(
    series_id: str = typer.Argument(..., help="Series identifier to download."),
    episodes: str = typer.Option(
        "all", "--episodes", "-e", help="Episode range (e.g. 1-12, 1,3,5 or all)."
    ),
    quality: str = typer.Option("1080p", "--quality", "-q", help="Preferred video quality."),
    provider: str = typer.Option("test", "--provider", "-p", help="Provider to download from."),
) -> None:
    """Queue and download episodes for a series."""
    service = get_service()
    try:
        job_ids = asyncio.run(
            service.queue_episodes(
                series_id=series_id,
                episode_range=episodes,
                quality=quality,
                provider_name=provider,
            )
        )
        console.print(
            f"[bold green]Successfully queued {len(job_ids)} episode(s) to download queue.[/bold green]"
        )
        for jid in job_ids:
            console.print(f"  [cyan]*[/cyan] Queued: {jid}")
    except (AniBatchError, ValueError, OSError) as exc:
        console.print(f"[bold red]Failed to queue episodes:[/bold red] {exc}")


@app.command()
def queue(
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Show active and pending download jobs."""
    import json

    service = get_service()
    jobs = asyncio.run(service.list_jobs())

    if json_output:
        print(json.dumps([j.model_dump(mode="json") for j in jobs], indent=2))
        return

    if not jobs:
        console.print("[yellow]Download queue is empty.[/yellow]")
        return

    table = Table(title="Download Queue")
    table.add_column("Job ID", style="cyan")
    table.add_column("Series", style="white")
    table.add_column("Episode", style="magenta")
    table.add_column("Quality", style="green")
    table.add_column("State", style="bold yellow")
    table.add_column("Progress", style="blue")

    for j in jobs:
        progress = f"{j.bytes_downloaded} / {j.bytes_total} B" if j.bytes_total else "Pending"
        table.add_row(
            j.id,
            str(j.anime_id),
            str(j.episode_id),
            j.selected_quality,
            j.state.value.upper(),
            progress,
        )
    console.print(table)


@app.command()
def pause(
    job_id: str = typer.Argument(..., help="ID of job to pause."),
) -> None:
    """Pause an active or queued download job."""
    service = get_service()
    asyncio.run(service.pause_job(job_id))
    console.print(f"[bold yellow]Job {job_id} paused.[/bold yellow]")


@app.command()
def resume(
    job_id: str = typer.Option("all", "--job", "-j", help="Job ID or 'all' to resume."),
) -> None:
    """Resume paused download jobs."""
    service = get_service()
    count = asyncio.run(service.resume_all())
    console.print(f"[bold green]Resumed {count} paused job(s).[/bold green]")


@app.command()
def cancel(
    job_id: str = typer.Argument(..., help="ID of job to cancel."),
) -> None:
    """Cancel a download job."""
    service = get_service()
    asyncio.run(service.cancel_job(job_id))
    console.print(f"[bold red]Job {job_id} cancelled.[/bold red]")


@app.command()
def history() -> None:
    """View past completed download jobs."""
    service = get_service()
    records = asyncio.run(service.list_history())

    if not records:
        console.print("[yellow]No download history found.[/yellow]")
        return

    table = Table(title="Completed Downloads")
    table.add_column("ID", style="cyan")
    table.add_column("Episode", style="white")
    table.add_column("Destination", style="green")
    table.add_column("Size", style="blue")
    table.add_column("Completed At", style="magenta")

    for r in records:
        size_mb = f"{r.get('size', 0) / (1024 * 1024):.1f} MB"
        table.add_row(
            str(r.get("id")),
            str(r.get("episode_id")),
            str(r.get("destination")),
            size_mb,
            str(r.get("completed_at")),
        )
    console.print(table)


@app.command()
def providers() -> None:
    """List available media providers and their operational status."""
    # Ensure test provider is registered
    from anibatch.providers.test_provider.provider import TestProvider

    if not registry.get("test"):
        registry.register(TestProvider())

    health = asyncio.run(registry.health_check_all())

    table = Table(title="Media Providers")
    table.add_column("Provider", style="bold cyan")
    table.add_column("Status", style="green")

    for p_name, is_ok in health.items():
        status = "[green][OK] Online[/green]" if is_ok else "[red][X] Unreachable[/red]"
        table.add_row(p_name, status)

    console.print(table)


@app.command()
def config() -> None:
    """Show current AniBatch configuration."""
    cfg = AniBatchConfig.load()
    console.print(f"[bold cyan]Configuration File:[/bold cyan] {get_default_config_path()}")
    console.print(f"  [bold]Download Directory:[/bold] {cfg.general.download_directory}")
    console.print(f"  [bold]Data Directory:[/bold] {cfg.general.data_directory}")
    console.print(f"  [bold]Concurrency:[/bold] {cfg.downloads.concurrency}")
    console.print(f"  [bold]Preferred Quality:[/bold] {cfg.video.preferred_quality}")
    console.print(f"  [bold]Preferred Audio:[/bold] {cfg.audio.preferred_languages}")
    console.print(f"  [bold]Preferred Subtitles:[/bold] {cfg.subtitles.preferred_languages}")


@app.command()
def doctor() -> None:
    """Run comprehensive system diagnostics."""
    service = get_service()
    diag = asyncio.run(service.run_diagnostics())

    console.print("[bold]System Diagnostics:[/bold]")
    console.print(
        f"  {'[green][OK][/green]' if diag.get('config_loaded') else '[red][X][/red]'} Configuration: Loaded"
    )
    console.print(
        f"  {'[green][OK][/green]' if diag.get('database_writable') is True else '[red][X][/red]'} Database: Writable"
    )
    console.print(
        f"  {'[green][OK][/green]' if diag.get('destination_writable') is True else '[red][X][/red]'} Destination: Writable"
    )
    console.print(
        f"  {'[green][OK][/green]' if diag.get('ffmpeg') else '[red][X][/red]'} FFmpeg: {'Installed' if diag.get('ffmpeg') else 'Missing'}"
    )
    console.print(
        f"  {'[green][OK][/green]' if diag.get('ffprobe') else '[red][X][/red]'} FFprobe: {'Installed' if diag.get('ffprobe') else 'Missing'}"
    )
    console.print(
        f"  {'[green][OK][/green]' if diag.get('anilist_reachable') else '[yellow][!][/yellow]'} AniList: {'Reachable' if diag.get('anilist_reachable') else 'Offline / No internet'}"
    )

    prov_status = diag.get("providers", {})
    for p_name, ok in prov_status.items():
        console.print(
            f"  {'[green][OK][/green]' if ok else '[red][X][/red]'} Provider ({p_name}): {'Online' if ok else 'Offline'}"
        )


@app.command()
def tui() -> None:
    """Launch the interactive terminal user interface (TUI)."""
    from anibatch.cli.tui import run_tui

    run_tui()


@app.command(name="export-queue")
def export_queue(
    output_file: Path = typer.Argument(..., help="Destination JSON file path."),
) -> None:
    """Export current download queue to a JSON file."""
    import json

    service = get_service()
    jobs = asyncio.run(service.list_jobs())
    data = [j.model_dump(mode="json") for j in jobs]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(f"[bold green]Exported {len(data)} job(s) to {output_file}.[/bold green]")


@app.command(name="import-queue")
def import_queue(
    input_file: Path = typer.Argument(..., help="Source JSON file path."),
) -> None:
    """Import download jobs from a JSON file into the queue."""
    import json

    from anibatch.core.models import DownloadJob
    from anibatch.storage.repositories import SqliteJobRepository

    if not input_file.exists():
        console.print(f"[bold red]File not found: {input_file}[/bold red]")
        return
    data = json.loads(input_file.read_text(encoding="utf-8"))
    jobs = [DownloadJob.model_validate(item) for item in data]
    service = get_service()

    async def _import() -> None:
        await service.init_db()
        async with service.database.connect() as conn:
            repo = SqliteJobRepository(conn)
            for j in jobs:
                await repo.create_job(j)

    asyncio.run(_import())
    console.print(f"[bold green]Imported {len(jobs)} job(s) into queue.[/bold green]")


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address to bind."),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on."),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Do not automatically open the web browser."
    ),
) -> None:
    """Launch the AniBatch interactive local Web Dashboard."""
    import time

    from anibatch.web.server import AniBatchWebServer

    service = get_service()
    server = AniBatchWebServer(service=service, host=host, port=port)
    try:
        server.start(open_browser=not no_browser)
    except OSError as err:
        console.print(f"[bold red]Failed to start web server on {host}:{port}: {err}[/bold red]")
        raise typer.Exit(code=1) from err

    active_port = server.server_port
    if active_port != port:
        console.print(
            f"[yellow]Port {port} is in use by another application (e.g. Splunk).[/yellow]\n"
            f"[yellow]Automatically switched to port {active_port}.[/yellow]"
        )
    console.print(
        f"[bold green]AniBatch Web Dashboard is running at http://{host}:{active_port}/[/bold green]"
    )
    console.print("[dim]Press Ctrl+C to exit.[/dim]")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down AniBatch Web Dashboard...[/yellow]")
    finally:
        server.stop()


if __name__ == "__main__":
    app()
