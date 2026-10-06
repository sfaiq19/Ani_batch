# Provider Rules

- Every provider adapter must inherit from `anibatch.providers.base.Provider`.
- All methods (`search`, `get_series`, `get_episodes`, `get_media_variants`) must return canonical AniBatch domain entities.
- Never modify core downloader behavior or pipeline contracts to fit provider idiosyncrasies.
- No circumvention of access controls, DRM, CAPTCHAs, or paywalls. Providers only interface with authorized public feeds and endpoints.
