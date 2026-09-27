from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cdf.errors import CdfError

DEFAULT_IGNORE = ("node_modules", "__pycache__", ".venv")
_KNOWN_KEYS = {"path", "git", "hidden", "ignore"}


@dataclass(frozen=True)
class Config:
    path: Path
    git: bool = True
    hidden: bool = False
    ignore: tuple[str, ...] = field(default=DEFAULT_IGNORE)


def _home() -> Path | None:
    # Path.home() raises when $HOME is unset and the user has no passwd entry
    # (e.g. an arbitrary UID in a container); treat that as "no home".
    try:
        return Path.home()
    except RuntimeError:
        return None


def default_config_paths() -> tuple[Path, ...]:
    home = _home()
    paths: list[Path] = []
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    # The XDG spec says to ignore a relative XDG_CONFIG_HOME.
    if xdg_config_home and Path(xdg_config_home).is_absolute():
        paths.append(Path(xdg_config_home) / "cdf" / "cdf.conf")
    elif home is not None:
        paths.append(home / ".config" / "cdf" / "cdf.conf")
    if home is not None:
        paths.append(home / "cdf.conf")
    return tuple(paths)


def _first_existing_default(paths: tuple[Path, ...]) -> Path | None:
    # os.path.isfile, not Path.exists: on Python < 3.14 the latter raises
    # PermissionError when a parent (e.g. ~/.config) can't be searched, and a
    # file nobody can reach can't be the one the user meant.
    return next((path for path in paths if os.path.isfile(path)), None)


def _absolute(path: Path | None) -> Path:
    # Always hand an absolute root to the walker, so every printed result is
    # absolute and the shell's `cd` never consults CDPATH or sees a leading "-".
    # abspath (not resolve) keeps symlinked directories as the user wrote them.
    try:
        return Path(os.path.abspath(path)) if path is not None else Path.cwd()
    except FileNotFoundError as exc:
        raise CdfError(
            "the current directory no longer exists; cd somewhere else or pass -p/--path"
        ) from exc


def load_config_file(config_path: Path) -> dict[str, object]:
    try:
        with config_path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except FileNotFoundError as exc:
        # Default locations are only ever passed in when they exist, so a
        # missing file here is always one the user named (-c or $CDF_CONFIG_PATH).
        raise CdfError(f"config file not found: {config_path}") from exc
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
        # A relative path in the file means relative to the file, not to
        # wherever cdf happens to be run from.
        try:
            expanded = Path(raw_path).expanduser()
        except RuntimeError as exc:
            raise CdfError(f"{config_path}: cannot expand '~' in 'path': {exc}") from exc
        overrides["path"] = config_path.parent / expanded

    for key in ("git", "hidden"):
        if key in file_data:
            value = file_data[key]
            if not isinstance(value, bool):
                type_name = type(value).__name__
                raise CdfError(f"{config_path}: '{key}' must be a boolean, got {type_name}")
            overrides[key] = value

    if "ignore" in file_data:
        patterns = file_data["ignore"]
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise CdfError(f"{config_path}: 'ignore' must be a list of strings")
        # Patterns are matched against one directory name at a time, so one
        # with a "/" could never match; say so instead of silently ignoring it.
        with_slash = [pattern for pattern in patterns if "/" in pattern]
        if with_slash:
            raise CdfError(
                f"{config_path}: 'ignore' patterns match single directory names and "
                f"can't contain '/': {', '.join(with_slash)}"
            )
        overrides["ignore"] = tuple(patterns)

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
    resolved_config_path = config_path or _first_existing_default(default_config_paths())
    file_overrides: dict[str, Any] = {}
    if resolved_config_path is not None:
        file_data = load_config_file(resolved_config_path)
        file_overrides = _file_overrides(file_data, resolved_config_path)
    overrides = {**file_overrides, **_cli_overrides(cli_path, cli_git, cli_hidden)}
    root = _absolute(overrides.pop("path", None))
    config = Config(path=root, **overrides)

    if not config.path.is_dir():
        raise CdfError(f"search root does not exist or is not a directory: {config.path}")

    return config
