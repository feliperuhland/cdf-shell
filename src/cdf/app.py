from __future__ import annotations

from pathlib import Path

from cdf.picker import Picker
from cdf.walker import DirectoryWalker


def resolve(
    term: str,
    root: Path,
    *,
    git_only: bool,
    include_hidden: bool,
    walker: DirectoryWalker,
    picker: Picker,
) -> Path | None:
    candidates = list(walker.walk(root, git_only=git_only, include_hidden=include_hidden))
    if not candidates:
        return None
    return picker.pick(candidates, term)
