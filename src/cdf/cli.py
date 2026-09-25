from __future__ import annotations

import argparse
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from cdf.app import resolve
from cdf.config import DEFAULT_CONFIG_PATHS, resolve_config
from cdf.errors import CdfError
from cdf.picker import FzfPicker, Picker
from cdf.walker import DirectoryWalker, FilesystemWalker

_EXIT_SELECTED = 0
_EXIT_NO_SELECTION = 1
_EXIT_ERROR = 2


def create_walker() -> DirectoryWalker:
    return FilesystemWalker()


def create_picker() -> Picker:
    return FzfPicker()


def _package_version() -> str:
    try:
        return version("cdf-shell")
    except PackageNotFoundError:
        return "unknown"


def _resolve_config_path(cli_config: Path | None) -> Path | None:
    if cli_config is not None:
        return cli_config
    env_config = os.environ.get("CDF_CONFIG_PATH")
    return Path(env_config) if env_config else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdf",
        description="Interactively find a directory below a path and print it.",
        epilog=(
            "This binary only prints the resolved path; it never changes your shell's "
            "working directory itself. Source shell/cdf.sh in your shell rc — it defines "
            "a `cdf` shell function (which takes priority over this binary and calls it "
            "internally via `command cdf`) that actually cds into the result.\n\n"
            "Defaults shown below can also be set in the config file (-c/--config); "
            "CLI flags always win.\n\n"
            "Exit codes: 0 = a directory was selected, 1 = nothing was selected "
            "(cancelled or no matches), 2 = an error occurred (see stderr)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("term", nargs="?", default="", help="initial fuzzy filter text")
    parser.add_argument(
        "-p",
        "--path",
        type=Path,
        default=None,
        help="root to search from (default: cwd)",
    )
    parser.add_argument(
        "--git",
        dest="git",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="only match git repository roots (default: on)",
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="hidden",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="include hidden/dot directories (default: off)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help=(
            "config file path (default: $CDF_CONFIG_PATH, else first existing of "
            + ", ".join(str(path) for path in DEFAULT_CONFIG_PATHS)
            + ")"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = resolve_config(
            config_path=_resolve_config_path(args.config),
            cli_path=args.path,
            cli_git=args.git,
            cli_hidden=args.hidden,
        )
        target = resolve(
            args.term,
            config.path,
            git_only=config.git,
            include_hidden=config.hidden,
            walker=create_walker(),
            picker=create_picker(),
        )
    except CdfError as exc:
        print(str(exc), file=sys.stderr)
        return _EXIT_ERROR

    if target is None:
        return _EXIT_NO_SELECTION

    print(target)
    return _EXIT_SELECTED


if __name__ == "__main__":
    raise SystemExit(main())
