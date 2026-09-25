from __future__ import annotations

import os
from collections.abc import Collection, Iterator
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Protocol

from cdf.errors import CdfError


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
    if not include_hidden and name.startswith("."):
        return True
    return any(fnmatchcase(name, pattern) for pattern in ignore)


class FilesystemWalker:
    """Depth-first, sorted walk built directly on os.scandir.

    scandir's DirEntry reports symlinks and directory-ness from the directory
    listing itself, so unlike os.walk plus a per-directory lstat, detecting
    symlinked directories costs no extra system calls.
    """

    def walk(
        self,
        root: Path,
        *,
        git_only: bool,
        include_hidden: bool,
        ignore: Collection[str],
    ) -> Iterator[Path]:
        stack = [root]
        while stack:
            current = stack.pop()
            # One cheap pass over the listing: is_dir(follow_symlinks=False) and
            # is_symlink() come from the directory entry itself, so files (the
            # vast majority) are dismissed without a syscall, prune check or sort.
            is_repo = False
            subdirs: list[os.DirEntry[str]] = []
            links: list[os.DirEntry[str]] = []
            try:
                with os.scandir(current) as listing:
                    for entry in listing:
                        if entry.name == ".git":
                            # Marks a repo; never listed or descended into,
                            # whatever --all or the ignore patterns say.
                            is_repo = True
                        elif entry.is_dir(follow_symlinks=False):
                            subdirs.append(entry)
                        elif entry.is_symlink():
                            links.append(entry)
            except OSError as exc:
                # Unreadable subdirectories are skipped (they can't be cd'd
                # into anyway), but an unreadable root would otherwise
                # masquerade as an empty tree.
                if current == root:
                    raise CdfError(f"cannot read search root {root}: {exc.strerror}") from exc
                continue

            if current != root:
                if git_only and is_repo:
                    yield current
                    continue
                if not git_only:
                    yield current

            for entry in self._kept(links, include_hidden=include_hidden, ignore=ignore):
                # Never descended into (so no loops), but still a valid place to
                # cd into: offer it as a leaf. is_dir() follows the link, so
                # broken links and links to files drop out.
                path = Path(entry.path)
                try:
                    if entry.is_dir() and (not git_only or (path / ".git").exists()):
                        yield path
                except OSError:
                    continue

            kept = self._kept(subdirs, include_hidden=include_hidden, ignore=ignore)
            # Reversed so the alphabetically first subdirectory is popped next.
            stack.extend(Path(entry.path) for entry in reversed(kept))

    @staticmethod
    def _kept(
        entries: list[os.DirEntry[str]], *, include_hidden: bool, ignore: Collection[str]
    ) -> list[os.DirEntry[str]]:
        kept = [
            entry
            for entry in entries
            if not _is_pruned(entry.name, include_hidden=include_hidden, ignore=ignore)
        ]
        kept.sort(key=lambda entry: entry.name)
        return kept
