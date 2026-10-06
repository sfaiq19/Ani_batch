from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, ProgressBar, Static


class AniBatchTUI(App[None]):
    """Terminal User Interface for AniBatch using Textual."""

    CSS = """
    Screen {
        background: $surface;
    }
    #sidebar {
        width: 24;
        background: $panel;
        padding: 1;
        border-right: vkey $accent;
    }
    #main-content {
        padding: 1;
    }
    .nav-btn {
        width: 100%;
        margin-bottom: 1;
    }
    .section-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Navigation", classes="section-title")
                yield Button("Downloads", id="btn-dl", classes="nav-btn", variant="primary")
                yield Button("Search", id="btn-search", classes="nav-btn")
                yield Button("History", id="btn-history", classes="nav-btn")
                yield Button("Providers", id="btn-providers", classes="nav-btn")
                yield Button("Settings", id="btn-settings", classes="nav-btn")

            with Container(id="main-content"):
                yield Label("Active Queue — Frieren: Beyond Journey's End", classes="section-title")
                yield Static("Episode 01")
                yield ProgressBar(total=100)
                yield Static("Episode 02")
                yield ProgressBar(total=100)
                yield Static("Episode 03")
                yield ProgressBar(total=100)
                yield Label(
                    "\nTransfer Speed: 14.6 MB/s | Concurrency: 3 active | Queue: 25 waiting"
                )

        yield Footer()


def run_tui() -> None:
    app = AniBatchTUI()
    app.run()
