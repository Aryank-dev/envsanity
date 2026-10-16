"""Load optional ``.envsanity.toml`` configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

CONFIG_FILENAME = ".envsanity.toml"


class ConfigError(Exception):
    """Raised when the config file exists but cannot be parsed."""


def load_config(root: Path) -> dict[str, Any]:
    """Load ``.envsanity.toml`` from *root*.

    Returns an empty dict when the file is absent. Raises :class:`ConfigError`
    when the file exists but is invalid TOML or has the wrong shape.
    """
    config_path = Path(root) / CONFIG_FILENAME
    if not config_path.exists():
        return {}

    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigError(f"invalid {CONFIG_FILENAME}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"invalid {CONFIG_FILENAME}: expected a table")

    return data
