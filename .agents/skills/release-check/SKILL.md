---
name: release-check
description: Comprehensive verification check before declaring any AniBatch milestone or release complete
---

# Release Check Skill

Execute the following checks sequentially:

1. **Formatting & Linting**:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   ```
2. **Type Checking**:
   ```bash
   uv run mypy src
   ```
3. **Automated Tests**:
   ```bash
   uv run pytest -v
   ```
4. **CLI Validation**:
   ```bash
   uv run anibatch --help
   uv run anibatch doctor
   ```
5. **Security & Secrets Check**:
   - Inspect `git status` and `git diff` for stray secrets, uncommitted temporary files, or hardcoded API keys.
