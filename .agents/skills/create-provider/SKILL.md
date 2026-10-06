---
name: create-provider
description: Guidelines and procedure for creating a new pluggable AniBatch provider adapter
---

# Create Provider Skill

1. **Review Contract**: Inspect `src/anibatch/providers/base.py` for the required interface methods and return types.
2. **Create Package**: Place the provider in `src/anibatch/providers/<provider_name>/provider.py`.
3. **Inherit Base**: Subclass `anibatch.providers.base.Provider`.
4. **Implement Core Capabilities**:
   - `search(query: str) -> list[ProviderSeries]`
   - `get_episodes(series_id: str) -> list[ProviderEpisode]`
   - `get_media(episode_id: str) -> EpisodeMedia`
5. **No Domain Type Leakage**: Ensure raw HTML/JSON response structures are parsed into clean domain objects before returning.
6. **Register**: Register provider in `src/anibatch/providers/registry.py`.
7. **Add Fixtures and Contract Tests**: Create unit and contract tests in `tests/unit/test_providers/`.
