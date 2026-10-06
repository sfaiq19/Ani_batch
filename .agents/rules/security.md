# Security Rules

- FFmpeg and ffprobe invocations must pass arguments as an explicit argument vector (list/tuple) to `asyncio.create_subprocess_exec`. Never pass formatted strings or use `shell=True`.
- Media and directory names from external sources must pass through filename sanitization (`src/anibatch/naming/sanitizer.py`) to prevent path traversal and illegal filesystem characters on Windows and POSIX.
- No secrets, tokens, or credentials checked into source control.
- Atomic download commits: Always write to `.part` files in temporary locations before moving to destination.
