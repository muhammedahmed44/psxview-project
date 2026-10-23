from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE_ORDER = (
    "keywords.yaml",
    "thresholds.yaml",
    "source_quality.yaml",
    "sources.yaml",
)


def read_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return loaded if isinstance(loaded, dict) else {}


def deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def load_repository_config() -> dict[str, Any]:
    config = read_yaml_file(LEGACY_CONFIG_PATH)
    for filename in CONFIG_FILE_ORDER:
        config = deep_merge_dicts(config, read_yaml_file(CONFIG_DIR / filename))
    return config


def get_config_section(name: str, default: Any = None) -> Any:
    return load_repository_config().get(name, default)
