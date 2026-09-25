from __future__ import annotations

import argparse
import os
import sys
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from cdf.app import resolve
from cdf.config import default_config_paths, resolve_config
from cdf.errors import CdfError, NoCandidatesError
from cdf.picker import FzfPicker, Picker
from cdf.walker import DirectoryWalker, FilesystemWalker

_EXIT_SELECTED = 0
_EXIT_NO_SELECTION = 1
_EXIT_ERROR = 2
_EXIT_INTERRUPTED = 130
_INIT_SHELLS = ("bash", "zsh")


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


def shell_init_script(shell: str) -> str:
    # bash and zsh share one POSIX-style wrapper; `shell` is validated by argparse.
    return resources.files("cdf").joinpath("shell", "cdf.sh").read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdf",
        description="Interactively find a directory below a path and print it.",
        epilog=(
            "This binary only prints the resolved path; it never changes your shell's "
            'working directory itself. Add `eval "$(command cdf --init bash)"` (or zsh) '
            "to your shell rc: it defines a `cdf` shell function (which takes priority "
            "over this binary and calls it internally via `command cdf`) that actually "
            "cds into the result.\n\n"
            "Defaults shown below can also be set in the config file (-c/--config); "
            "CLI flags always win.\n\n"
            "Exit codes: 0 = a directory was selected, 1 = nothing was selected "
            "(cancelled or no matches), 2 = an error occurred (see stderr)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "term", nargs="*", default=[], help="initial fuzzy filter text (words are joined)"
    )
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
            + ", ".join(str(path) for path in default_config_paths())
            + ")"
        ),
    )
    parser.add_argument(
        "--init",
        choices=_INIT_SHELLS,
        default=None,
        metavar="SHELL",
        help=f"print the shell integration for SHELL ({', '.join(_INIT_SHELLS)}) and exit",
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

    if args.init is not None:
        sys.stdout.write(shell_init_script(args.init))
        return _EXIT_SELECTED

    try:
        config = resolve_config(
            config_path=_resolve_config_path(args.config),
            cli_path=args.path,
            cli_git=args.git,
            cli_hidden=args.hidden,
        )
        target = resolve(
            " ".join(args.term),
            config.path,
            git_only=config.git,
            include_hidden=config.hidden,
            ignore=config.ignore,
            walker=create_walker(),
            picker=create_picker(),
        )
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    except NoCandidatesError as exc:
        print(str(exc), file=sys.stderr)
        return _EXIT_NO_SELECTION
    except CdfError as exc:
        print(str(exc), file=sys.stderr)
        return _EXIT_ERROR

    if target is None:
        return _EXIT_NO_SELECTION

    print(target)
    return _EXIT_SELECTED


if __name__ == "__main__":
    raise SystemExit(main())
