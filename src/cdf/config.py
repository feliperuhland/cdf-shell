from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from cdf.errors import CdfError

DEFAULT_CONFIG_PATHS = (
    Path.home() / "cdf.conf",
    Path.home() / ".config" / "cdf" / "cdf.conf",
)
_KNOWN_KEYS = {"path", "git", "hidden"}


@dataclass(frozen=True)
class Config:
    path: Path
    git: bool = True
    hidden: bool = False


def default_config() -> Config:
    return Config(path=Path.cwd(), git=True, hidden=False)


def _first_existing_default(paths: tuple[Path, ...]) -> Path:
    return next((path for path in paths if path.exists()), paths[0])


def load_config_file(config_path: Path, *, explicit: bool = False) -> dict[str, object]:
    if not config_path.exists():
        if explicit:
            raise CdfError(f"config file not found: {config_path}")
        return {}
    try:
        with config_path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise CdfError(f"invalid config file {config_path}: {exc}") from exc
    except OSError as exc:
        raise CdfError(f"cannot read config file {config_path}: {exc}") from exc

    unknown = set(data) - _KNOWN_KEYS
    if unknown:
        raise CdfError(f"unknown key(s) in {config_path}: {', '.join(sorted(unknown))}")
    return data


def _file_overrides(file_data: dict[str, object], config_path: Path) -> dict[str, Any]:
    overrides: dict[str, Any] = {}

    if "path" in file_data:
        raw_path = file_data["path"]
        if not isinstance(raw_path, str):
            type_name = type(raw_path).__name__
            raise CdfError(f"{config_path}: 'path' must be a string, got {type_name}")
        overrides["path"] = Path(raw_path).expanduser()

    for key in ("git", "hidden"):
        if key in file_data:
            value = file_data[key]
            if not isinstance(value, bool):
                type_name = type(value).__name__
                raise CdfError(f"{config_path}: '{key}' must be a boolean, got {type_name}")
            overrides[key] = value

    return overrides


def _cli_overrides(
    cli_path: Path | None, cli_git: bool | None, cli_hidden: bool | None
) -> dict[str, Any]:
    candidates = {"path": cli_path, "git": cli_git, "hidden": cli_hidden}
    return {key: value for key, value in candidates.items() if value is not None}


def resolve_config(
    *,
    config_path: Path | None = None,
    cli_path: Path | None = None,
    cli_git: bool | None = None,
    cli_hidden: bool | None = None,
) -> Config:
    explicit = config_path is not None
    resolved_config_path = config_path or _first_existing_default(DEFAULT_CONFIG_PATHS)
    file_data = load_config_file(resolved_config_path, explicit=explicit)
    overrides = {
        **_file_overrides(file_data, resolved_config_path),
        **_cli_overrides(cli_path, cli_git, cli_hidden),
    }
    config = replace(default_config(), **overrides)

    if not config.path.is_dir():
        raise CdfError(f"search root does not exist or is not a directory: {config.path}")

    return config
