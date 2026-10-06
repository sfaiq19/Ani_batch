# Local Web Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-dependency, local web dashboard for AniBatch (`anibatch web`) featuring an interactive browser interface for searching anime, selecting episodes, queuing downloads, monitoring real-time queue progress, and launching via a 1-click Windows `.bat` script.

**Architecture:** A lightweight REST API server built on Python standard library `http.server.ThreadingHTTPServer` bound to a dedicated `asyncio` event loop that interfaces cleanly with `DownloadService`. Serves a responsive, single-page web UI (HTML/CSS/JS) with live queue polling, search results cards, episode multi-selector, and queue control actions.

**Tech Stack:** Python 3.12 standard library (`http.server`, `threading`, `asyncio`, `json`, `webbrowser`, `urllib.parse`), Typer CLI, HTML5/CSS3/Vanilla JS (zero external frontend build tools needed).

**Spec:** Integrated architecture following AniBatch clean layered design (`d:/Anime2/AGENTS.md`).

## Global Constraints

- Web server code must not perform direct scraping, direct database access, direct FFmpeg execution, or direct HTTP downloads itself; all operations must go through `DownloadService`.
- Zero new external runtime dependencies: use Python 3.12 standard library for the server.
- Must run cleanly on Windows (UTF-8 console handling, port binding, and browser auto-launch).
- CLI command `anibatch web` requires help text, options (`--host`, `--port`, `--no-browser`), README documentation, and automated tests.
- Every bug fix or new feature requires tests; full test suite must pass.

---

### Task 1: Web Server REST Handler & Async Bridge

**Files:**
- Create: `src/anibatch/web/__init__.py`
- Create: `src/anibatch/web/server.py`
- Create: `tests/unit/test_web.py`

**Interfaces:**
- Consumes: `anibatch.services.download_service.DownloadService`
- Produces: `AniBatchWebServer` class with `start()`, `stop()`, and `handle_request()` methods supporting endpoints:
  - `GET /api/search?q=<query>&provider=<provider>`
  - `GET /api/info?id=<id>&provider=<provider>`
  - `POST /api/download` (payload: `{"series_id": str, "episodes": str, "provider": str}`)
  - `GET /api/queue`
  - `POST /api/queue/pause` (payload: `{"job_id": str}`)
  - `POST /api/queue/resume`
  - `POST /api/queue/cancel` (payload: `{"job_id": str}`)
  - `GET /api/providers`
  - `GET /` (serves dashboard HTML)

- [ ] **Step 1: Write failing tests for REST API endpoints**

```python
import json
import urllib.request
import pytest
from anibatch.services.download_service import DownloadService
from anibatch.web.server import AniBatchWebServer

@pytest.fixture
def web_server():
    service = DownloadService()
    server = AniBatchWebServer(service=service, host="127.0.0.1", port=0)
    server.start(open_browser=False)
    yield server
    server.stop()

def test_api_providers(web_server):
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/providers")
    assert req.status == 200
    data = json.loads(req.read().decode())
    assert any(p["name"] == "test" for p in data)

def test_api_search_and_queue(web_server):
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/search?q=Frieren")
    assert req.status == 200
    results = json.loads(req.read().decode())
    assert len(results) >= 1

    # Test download enqueue
    post_data = json.dumps({"series_id": "fake-frieren", "episodes": "1", "provider": "test"}).encode()
    post_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/download",
        data=post_data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(post_req)
    assert resp.status == 200
    post_res = json.loads(resp.read().decode())
    assert post_res["queued_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_web.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'anibatch.web'`

- [ ] **Step 3: Implement WebServer and Handler**

Create `src/anibatch/web/server.py` using `http.server.ThreadingHTTPServer`, with `asyncio.run_coroutine_threadsafe()` bridging HTTP thread requests to the service's async loop.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_web.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/anibatch/web tests/unit/test_web.py
git commit -m "feat: add AniBatchWebServer REST API backend and async bridge"
```

---

### Task 2: Responsive Frontend Single-Page Application (SPA)

**Files:**
- Create: `src/anibatch/web/static/index.html`
- Modify: `src/anibatch/web/server.py`
- Modify: `tests/unit/test_web.py`

**Interfaces:**
- Consumes: REST endpoints from Task 1
- Produces: Embedded single-page interface served on `GET /` featuring:
  - Header with AniBatch logo, provider status pill, and refresh button
  - Search input box with instant search and loading spinners
  - Grid of anime cards displaying title, year, episode count, and cover art
  - Interactive Episode Modal: allows selecting all episodes, a custom range (e.g. `1-4`), or single episode
  - Active Queue Drawer/Panel: live polling progress bar (updated every 1s), ETA, speed, status tags, Pause, Resume, and Cancel buttons

- [ ] **Step 1: Write test for static HTML delivery**

```python
def test_serve_dashboard_html(web_server):
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/")
    assert req.status == 200
    assert "text/html" in req.headers.get("Content-Type", "")
    content = req.read().decode()
    assert "AniBatch" in content
    assert "Download Queue" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_web.py -k test_serve_dashboard_html -v`
Expected: FAIL (or empty HTML response)

- [ ] **Step 3: Build HTML/CSS/JavaScript SPA**

Create `src/anibatch/web/static/index.html` with modern, self-contained CSS (dark glassmorphism, responsive grid, animated progress bars) and Vanilla JS interacting with `/api/search`, `/api/download`, `/api/queue`, and `/api/queue/pause/resume/cancel`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_web.py -k test_serve_dashboard_html -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/anibatch/web/static/index.html src/anibatch/web/server.py tests/unit/test_web.py
git commit -m "feat: implement responsive single-page web dashboard interface"
```

---

### Task 3: CLI Command Integration (`anibatch web`) & 1-Click Windows Launcher

**Files:**
- Modify: `src/anibatch/cli/app.py`
- Create: `run_web.bat`
- Modify: `README.md`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: `AniBatchWebServer`
- Produces: Typer CLI command `@app.command("web")`, Windows `run_web.bat`, and CLI tests

- [ ] **Step 1: Write test for `anibatch web --help` in `test_cli.py`**

```python
def test_cli_web_help():
    result = runner.invoke(app, ["web", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.stdout
    assert "--host" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli.py -k test_cli_web_help -v`
Expected: FAIL with "No such command 'web'"

- [ ] **Step 3: Implement `web` CLI command and `run_web.bat`**

Add `web` command in `src/anibatch/cli/app.py` accepting `--host` (default `127.0.0.1`), `--port` (default `8000`), and `--no-browser` flag.
Create `run_web.bat` in the project root:
```bat
@echo off
echo Starting AniBatch Web Dashboard...
uv run anibatch web
pause
```
Update `README.md` documentation.

- [ ] **Step 4: Run CLI tests**

Run: `uv run pytest tests/unit/test_cli.py -k test_cli_web -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/anibatch/cli/app.py run_web.bat README.md tests/unit/test_cli.py
git commit -m "feat: add anibatch web CLI command and 1-click Windows launcher"
```

---

### Task 4: Full Verification & Integration Testing

**Files:**
- Verification: Full test suite, lint, and type check

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest`
Expected: All tests pass (60+ tests).

- [ ] **Step 2: Run linters and type check**

Run: `uv run ruff check .`
Run: `uv run mypy src`
Expected: 0 errors across all source files.

- [ ] **Step 3: Live end-to-end verification**

Run `uv run anibatch web --no-browser --port 8765` in background, probe endpoints with HTTP GET/POST, verify queue lifecycle, and cleanly terminate.

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "chore: verify full web dashboard suite"
```
