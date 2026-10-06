# AniBatch

AniBatch is a production-quality, provider-agnostic batch media downloader and library management framework.

## Features

- **Decoupled Architecture**: Clean domain boundaries separating CLI, providers, downloader engine, and metadata services.
- **Pluggable Providers**: Standardized SPI (`Provider`) with strict type isolation.
- **Resilient Downloads**: HTTP streaming with resume support (`.part` chunks), exponential backoff retries, and concurrent job queues.
- **SQLite Persistence**: Complete state machine persisting jobs across application restarts.
- **Media Post-Processing**: FFmpeg validation and subtitle muxing without deleting intermediate source media until verified.

## Quickstart

```bash
# Sync environment dependencies
uv sync

# Run the test suite
uv run pytest

# Execute AniBatch CLI
uv run anibatch --help
```
