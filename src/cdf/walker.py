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
        max_depth: int | None = None,
        one_file_system: bool = False,
    ) -> Iterator[Path]: ...


def _is_pruned(name: str, *, include_hidden: bool, ignore: Collection[str]) -> bool:
    if not include_hidden and name.startswith("."):
        return True
    return any(fnmatchcase(name, pattern) for pattern in ignore)


def _device(entry: os.DirEntry[str]) -> int:
    return entry.stat(follow_symlinks=False).st_dev


class FilesystemWalker:
    """Depth-first, sorted walk built directly on os.scandir.

    scandir's DirEntry reports symlinks and directory-ness from the directory
    listing itself, so unlike os.walk plus a per-directory lstat, detecting
    symlinked directories costs no extra system calls.

    `max_depth` counts levels below the root (1 = only its direct children).
    With `one_file_system`, mount points below the root are listed but not
    entered, like `find -xdev`; that costs one stat per kept subdirectory.
    """

    def walk(
        self,
        root: Path,
        *,
        git_only: bool,
        include_hidden: bool,
        ignore: Collection[str],
        max_depth: int | None = None,
        one_file_system: bool = False,
    ) -> Iterator[Path]:
        root_device: int | None = None
        if one_file_system:
            try:
                root_device = os.stat(root).st_dev
            except OSError as exc:
                raise CdfError(f"cannot read search root {root}: {exc.strerror}") from exc
        stack = [(root, 0)]
        while stack:
            current, depth = stack.pop()
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
                            continue
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                subdirs.append(entry)
                            elif entry.is_symlink():
                                links.append(entry)
                        except OSError:
                            # Only this entry is unreadable (e.g. a file system
                            # without entry types, needing a stat that fails);
                            # keep its siblings.
                            continue
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

            if max_depth is not None and depth >= max_depth:
                continue

            kept = self._kept(subdirs, include_hidden=include_hidden, ignore=ignore)
            leaves = self._kept(links, include_hidden=include_hidden, ignore=ignore)
            if root_device is not None:
                kept, mounts = self._split_mounts(kept, root_device)
                leaves = sorted([*leaves, *mounts], key=lambda entry: entry.name)

            for entry in leaves:
                # Symlinks (so no loops) and, with one_file_system, mount points:
                # never descended into, but still valid places to cd into, so
                # offer them as leaves. is_dir() follows links, so broken links
                # and links to files drop out.
                path = Path(entry.path)
                try:
                    if entry.is_dir() and (not git_only or (path / ".git").exists()):
                        yield path
                except OSError:
                    continue

            # Reversed so the alphabetically first subdirectory is popped next.
            stack.extend((Path(entry.path), depth + 1) for entry in reversed(kept))

    @staticmethod
    def _split_mounts(
        entries: list[os.DirEntry[str]], root_device: int
    ) -> tuple[list[os.DirEntry[str]], list[os.DirEntry[str]]]:
        same: list[os.DirEntry[str]] = []
        mounts: list[os.DirEntry[str]] = []
        for entry in entries:
            try:
                (same if _device(entry) == root_device else mounts).append(entry)
            except OSError:
                continue
        return same, mounts

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
