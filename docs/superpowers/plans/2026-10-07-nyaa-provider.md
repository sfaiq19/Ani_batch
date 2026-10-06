# Nyaa Anime Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a production-grade, pluggable `NyaaProvider` adapter in AniBatch to search, list, and batch-download anime releases directly from the Nyaa anime RSS feed using `aria2c`.

**Architecture:** Implement `NyaaProvider` conforming strictly to the AniBatch `Provider` SPI (`src/anibatch/providers/base.py`). Queries the public Nyaa XML RSS feed, cleans release group metadata into domain models (`ProviderSeries`, `ProviderEpisode`, `EpisodeMedia`), and dispatches downloads via `Aria2Backend` with torrent support (`--follow-torrent=mem`, `--seed-time=0`).

**Tech Stack:** Python 3.12 standard library (`xml.etree.ElementTree`, `re`, `shutil`), `httpx`, Pydantic, AniBatch Provider SPI, `aria2c`.

**Spec:** AniBatch clean layered architecture (`d:/Anime2/AGENTS.md`) and `.agents/skills/create-provider/SKILL.md`.

## Global Constraints

- Provider-specific logic must exist exclusively inside `src/anibatch/providers/nyaa/`.
- Zero provider-specific types may leak into downloader, metadata, storage, naming, or CLI layers.
- Network-based tests must not depend on public websites; all tests must use controlled XML fixtures or `respx` mocks.
- Every provider requires contract tests.
- Full test suite must pass before declaring completion.

---

### Task 1: Nyaa Provider Adapter Implementation

**Files:**
- Create: `src/anibatch/providers/nyaa/__init__.py`
- Create: `src/anibatch/providers/nyaa/provider.py`
- Modify: `src/anibatch/providers/registry.py`

**Interfaces:**
- Implements: `anibatch.providers.base.Provider`
- Methods:
  - `search(query: str) -> list[ProviderSeries]`
  - `get_series(series_id: str) -> ProviderSeries`
  - `get_episodes(series_id: str) -> list[ProviderEpisode]`
  - `get_media(episode: ProviderEpisode) -> EpisodeMedia`
  - `health_check() -> bool`

- [ ] **Step 1: Create `src/anibatch/providers/nyaa/__init__.py` and `provider.py`**
Implement XML parsing of Nyaa RSS feeds, episode extraction regex, series grouping, and media variant generation.

- [ ] **Step 2: Register in `src/anibatch/providers/registry.py`**
Add `NyaaProvider` to `init_default_providers()`.

---

### Task 2: Aria2 Torrent Download Options & Backend Enhancement

**Files:**
- Modify: `src/anibatch/downloader/backends/aria2.py`
- Modify: `tests/unit/test_aria2.py`

**Interfaces:**
- Adds `--follow-torrent=mem` and `--seed-time=0` to `Aria2Backend.download()` command invocation to support torrent links and direct media alike.

- [ ] **Step 1: Update `Aria2Backend` download args in `aria2.py`**
- [ ] **Step 2: Run aria2 unit tests to ensure no regressions**

---

### Task 3: Contract & Unit Tests for Nyaa Provider

**Files:**
- Create: `tests/unit/test_providers/test_nyaa_provider.py`

**Interfaces:**
- Tests `NyaaProvider` search, episode parsing, media variant extraction, and error handling against mock RSS XML responses using `respx`.

- [ ] **Step 1: Write contract tests with mocked XML responses**
- [ ] **Step 2: Run `uv run pytest tests/unit/test_providers/test_nyaa_provider.py`**

---

### Task 4: Full Verification & Integration Test

**Files:**
- Full test suite, ruff format/check, mypy check.

- [ ] **Step 1: Run `uv run pytest` across all tests**
- [ ] **Step 2: Run `uv run ruff check .` and `uv run mypy src`**
- [ ] **Step 3: Verify `anibatch doctor` and `anibatch providers` list `nyaa`**
