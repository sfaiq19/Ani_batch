# Architecture Rules

- Maintain clean separation between CLI, Domain, Providers, Downloader, Storage, and Media layers.
- CLI code must delegate all heavy lifting and business operations to Application Services.
- Pluggable provider code lives only inside `src/anibatch/providers/`.
- Domain models in `src/anibatch/core/models.py` are the single source of truth for entity representations across the system. Provider-specific response shapes or schemas must be mapped to normalized domain models before leaving the provider adapter.
- All network and I/O bound operations must be async (`asyncio`, `httpx.AsyncClient`, `aiosqlite`).
