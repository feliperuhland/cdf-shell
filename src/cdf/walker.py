from __future__ import annotations

import os
from collections.abc import Collection, Iterator
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Protocol

from cdf.errors import CdfError

# Never worth listing or descending into, whatever the user's ignore patterns say.
_ALWAYS_PRUNED = ".git"


class DirectoryWalker(Protocol):
    def walk(
        self,
        root: Path,
        *,
        git_only: bool,
        include_hidden: bool,
        ignore: Collection[str],
    ) -> Iterator[Path]: ...


def _is_pruned(name: str, *, include_hidden: bool, ignore: Collection[str]) -> bool:
    if name == _ALWAYS_PRUNED:
        return True
    if not include_hidden and name.startswith("."):
        return True
    return any(fnmatchcase(name, pattern) for pattern in ignore)


class FilesystemWalker:
    def walk(
        self,
        root: Path,
        *,
        git_only: bool,
        include_hidden: bool,
        ignore: Collection[str],
    ) -> Iterator[Path]:
        def on_error(error: OSError) -> None:
            # Unreadable subdirectories are skipped, but an unreadable root
            # would otherwise masquerade as an empty tree.
            if error.filename is not None and Path(error.filename) == root:
                raise CdfError(f"cannot read search root {root}: {error.strerror}") from error

        for dirpath, dirnames, filenames in os.walk(
            root, topdown=True, onerror=on_error, followlinks=False
        ):
            current = Path(dirpath)
            is_repo = ".git" in dirnames or ".git" in filenames

            dirnames[:] = [
                name
                for name in dirnames
                if not _is_pruned(name, include_hidden=include_hidden, ignore=ignore)
            ]
            dirnames.sort()

            if current != root:
                if git_only and is_repo:
                    yield current
                    dirnames[:] = []
                    continue
                if not git_only:
                    yield current

            # os.walk never descends into symlinked directories (so no loops),
            # but they are still valid places to cd into: offer them as leaves.
            for name in dirnames:
                link = current / name
                if link.is_symlink() and (not git_only or (link / ".git").exists()):
                    yield link
