"""Configuration management for NextLog."""

import os
from pathlib import Path
from typing import Any

import yaml


class Config:
    """NextLog configuration."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or self._default_config_path()
        self._data: dict = {}
        if self.config_path.exists():
            self._load()

    def _default_config_path(self) -> Path:
        """Get default config path."""
        return Path.cwd() / "nextlog.json"

    def _load(self):
        """Load config from file."""
        if self.config_path.suffix in (".yaml", ".yml"):
            with open(self.config_path) as f:
                self._data = yaml.safe_load(f) or {}
        elif self.config_path.suffix == ".json":
            import json

            with open(self.config_path) as f:
                self._data = json.load(f)
        else:
            # Try JSON first, then YAML
            import json

            try:
                with open(self.config_path) as f:
                    self._data = json.load(f)
            except json.JSONDecodeError:
                with open(self.config_path) as f:
                    self._data = yaml.safe_load(f) or {}

    @property
    def vault_path(self) -> Path:
        """Get vault path."""
        return Path(self._data.get("vault", str(Path.cwd())))

    @property
    def inbox_raw(self) -> Path:
        """Get inbox raw folder."""
        return self.vault_path / "inbox" / "raw"

    @property
    def inbox_processed(self) -> Path:
        """Get inbox processed folder."""
        return self.vault_path / "inbox" / "processed"

    @property
    def synthesis(self) -> Path:
        """Get synthesis folder."""
        return self.vault_path / "synthesis"

    @property
    def ref(self) -> Path:
        """Get ref folder."""
        return self.vault_path / "ref"

    @property
    def twitter(self) -> dict[str, Any]:
        """Get Twitter credentials."""
        return self._data.get("twitter", {})  # type: ignore[no-any-return]

    @property
    def llm(self) -> dict[str, Any]:
        """Get LLM configuration."""
        return self._data.get("llm", {})  # type: ignore[no-any-return]

    @property
    def llm_provider(self) -> str:
        """Get LLM provider."""
        return self.llm.get("provider", "openrouter")  # type: ignore[no-any-return]

    @property
    def llm_api_key(self) -> str:
        """Get LLM API key."""
        return self.llm.get("api_key", os.environ.get("OPENROUTER_API_KEY", ""))  # type: ignore[no-any-return]

    @property
    def llm_model(self) -> str:
        """Get LLM model."""
        return self.llm.get("model", "anthropic/claude-3.5-sonnet")  # type: ignore[no-any-return]

    @property
    def timezone(self) -> str:
        """Get timezone."""
        return self._data.get("timezone", "America/New_York")  # type: ignore[no-any-return]

    @property
    def bird_path(self) -> str:
        """Get bird CLI path."""
        return self._data.get("bird_path", "bird")  # type: ignore[no-any-return]

    def get(self, key: str, default=None):
        """Get config value."""
        return self._data.get(key, default)


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration."""
    return Config(config_path)
