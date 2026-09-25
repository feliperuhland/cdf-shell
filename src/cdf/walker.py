from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol


class DirectoryWalker(Protocol):
    def walk(self, root: Path, *, git_only: bool, include_hidden: bool) -> Iterator[Path]: ...


class FilesystemWalker:
    def walk(self, root: Path, *, git_only: bool, include_hidden: bool) -> Iterator[Path]:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            current = Path(dirpath)
            is_repo = ".git" in dirnames or ".git" in filenames

            if not include_hidden:
                dirnames[:] = [name for name in dirnames if not name.startswith(".")]

            if current == root:
                continue

            if git_only:
                if is_repo:
                    yield current
                    dirnames[:] = []
            else:
                yield current
