from __future__ import annotations

import itertools
from collections.abc import Collection
from pathlib import Path

from cdf.errors import NoCandidatesError
from cdf.picker import Picker
from cdf.walker import DirectoryWalker


def resolve(
    term: str,
    root: Path,
    *,
    git_only: bool,
    include_hidden: bool,
    ignore: Collection[str],
    walker: DirectoryWalker,
    picker: Picker,
) -> Path | None:
    candidates = walker.walk(root, git_only=git_only, include_hidden=include_hidden, ignore=ignore)
    # Peek at the first candidate so an empty tree gets a clear message instead
    # of an empty picker; the rest keeps streaming lazily into the picker.
    first = next(candidates, None)
    if first is None:
        if git_only:
            raise NoCandidatesError(f"no git repositories found under {root} (try --no-git)")
        raise NoCandidatesError(f"no directories found under {root}")
    return picker.pick(itertools.chain([first], candidates), term)
