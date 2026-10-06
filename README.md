# AniBatch

AniBatch is a production-quality, provider-agnostic batch media downloader and library management framework.

## Features

- **Decoupled Architecture**: Clean domain boundaries separating CLI, providers, downloader engine, and metadata services.
- **Pluggable Providers**: Standardized SPI (`Provider`) with strict type isolation.
- **Resilient Downloads**: HTTP streaming with resume support (`.part` chunks), exponential backoff retries, and concurrent job queues.
- **SQLite Persistence**: Complete state machine persisting jobs across application restarts.
- **Media Post-Processing**: FFmpeg validation and subtitle muxing without deleting intermediate source media until verified.
- **Local Web Dashboard**: Single-page modern browser dashboard with live progress polling, search, batch download, queue management, and system diagnostics.

## Quickstart

```bash
# Sync environment dependencies
uv sync

# Run the test suite
uv run pytest

# Launch AniBatch interactive Web Dashboard
uv run anibatch web

# Windows 1-click launcher
run_web.bat

# Execute AniBatch CLI
uv run anibatch --help
```

## Commands

### `anibatch web`

Launch the AniBatch interactive local Web Dashboard:

```bash
uv run anibatch web [OPTIONS]
```

**Options:**
- `-h, --host TEXT`: Host address to bind. [default: `127.0.0.1`]
- `-p, --port INTEGER`: Port to listen on. [default: `8000`]
- `--no-browser`: Do not automatically open the web browser.
- `--help`: Show this message and exit.

### 1-Click Windows Launcher (`run_web.bat`)

On Windows, double-click `run_web.bat` in the project root to start the Web Dashboard and open your default browser. If any error occurs, the window remains open to display diagnostic information.

