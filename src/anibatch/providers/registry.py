from anibatch.providers.base import Provider


class ProviderRegistry:
    """Registry maintaining active media providers."""

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider instance."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> Provider | None:
        """Retrieve a provider by name."""
        return self._providers.get(name)

    def list_available(self) -> list[str]:
        """List registered provider names."""
        return list(self._providers.keys())

    async def health_check_all(self) -> dict[str, bool]:
        """Run health check against all registered providers."""
        results: dict[str, bool] = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:  # noqa: BLE001
                results[name] = False
        return results


# Default global registry singleton
registry = ProviderRegistry()


def init_default_providers() -> None:
    """Register standard built-in providers."""
    from anibatch.providers.archive.provider import ArchiveProvider
    from anibatch.providers.test_provider.provider import TestProvider

    if not registry.get("test"):
        registry.register(TestProvider())
    if not registry.get("archive"):
        registry.register(ArchiveProvider())
