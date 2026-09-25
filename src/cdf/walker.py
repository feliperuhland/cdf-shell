from __future__ import annotations

import os
from collections.abc import Collection, Iterator
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Protocol

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
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            current = Path(dirpath)
            is_repo = ".git" in dirnames or ".git" in filenames

            dirnames[:] = [
                name
                for name in dirnames
                if not _is_pruned(name, include_hidden=include_hidden, ignore=ignore)
            ]
            dirnames.sort()

            if current == root:
                continue

            if git_only:
                if is_repo:
                    yield current
                    dirnames[:] = []
            else:
                yield current
