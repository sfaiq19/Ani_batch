# Testing Rules

- Network-based tests must never hit live production services. Use `respx` or mock servers.
- Every provider requires contract tests verifying compliance with the `Provider` abstract interface.
- Unit tests and integration tests must run isolated and fast.
- Every bug fix requires an accompanying regression test.
- Full test suite (`pytest`) must pass cleanly before completing any task.
